package blenderassets

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

// BridgeCaller is the subset of *client.Client this package needs, kept as
// an interface so it doesn't import internal/client (which would create an
// import cycle: internal/cli imports both this package and internal/client).
type BridgeCaller interface {
	CallBridge(ctx context.Context, method string, params any, timeout time.Duration) (json.RawMessage, error)
}

const heavyTimeout = 600 * time.Second

// ImportParams mirrors ImportOnlineAssetParams in asset_source_ops.py.
type ImportParams struct {
	AssetID          string
	Provider         string
	TargetPolyBudget int
	ReductionMethod  string // simplify (default) | decimate | remesh | "" (none)
	CollectionPath   string
	Location         [3]float64
	HasLocation      bool
	ScaleToSize      float64
	HasScale         bool
	ForwardAxis      string
	UpAxis           string
	AutoOrient       bool
}

// ImportOnlineAsset mirrors import_online_asset: resolve a downloadable file
// for (provider, asset_id), fetch it locally, hand it to the bridge's
// import_file, then optionally reduce to a vertex budget and file it into a
// collection. This is a narrower port than the Python original: it does not
// reproduce axis-orientation heuristics (suspect_upside_down/lying_down
// verdicts) or ambientCG/HDRI world-environment setup -- see
// .printing-press-patches/0002-vlm-and-asset-pipeline.md for what's covered.
func ImportOnlineAsset(ctx context.Context, bridge BridgeCaller, p ImportParams) (map[string]any, error) {
	provider := strings.ToLower(strings.TrimSpace(p.Provider))
	if provider == "" {
		provider = "sketchfab"
	}

	workDir, err := os.MkdirTemp("", "mcp-blender-asset-*")
	if err != nil {
		return nil, fmt.Errorf("creating temp download dir: %w", err)
	}

	var filePath string
	switch provider {
	case "polyhaven":
		filePath, err = downloadPolyhavenModel(ctx, p.AssetID, workDir)
	case "sketchfab":
		filePath, err = downloadSketchfabModel(ctx, p.AssetID, workDir)
	case "ambientcg":
		return nil, fmt.Errorf(
			"ambientCG import is texture/material-only in this CLI port (no 3D-model import path); " +
				"use --provider polyhaven or --provider sketchfab for models")
	default:
		return nil, fmt.Errorf("unknown provider %q: expected polyhaven, sketchfab, or ambientcg", p.Provider)
	}
	if err != nil {
		return nil, err
	}

	fileFormat := strings.ToUpper(strings.TrimLeft(filepath.Ext(filePath), "."))
	importParams := map[string]any{
		"filepath":    filePath,
		"file_format": fileFormat,
	}
	if p.ForwardAxis != "" {
		importParams["forward_axis"] = p.ForwardAxis
	}
	if p.UpAxis != "" {
		importParams["up_axis"] = p.UpAxis
	}
	if p.AutoOrient {
		importParams["auto_orient"] = true
	}

	raw, err := bridge.CallBridge(ctx, "import_file", importParams, heavyTimeout)
	if err != nil {
		return nil, fmt.Errorf("importing downloaded file into Blender: %w", err)
	}
	var importResult map[string]any
	if err := json.Unmarshal(raw, &importResult); err != nil {
		return nil, fmt.Errorf("parsing import_file result: %w", err)
	}
	if ok, _ := importResult["success"].(bool); !ok {
		msg, _ := importResult["message"].(string)
		if msg == "" {
			msg = "import_file failed"
		}
		return nil, fmt.Errorf("%s", msg)
	}

	newObjectNames := stringSlice(importResult["imported_objects"])

	result := map[string]any{
		"success":          true,
		"asset_id":         p.AssetID,
		"provider":         provider,
		"downloaded_file":  filePath,
		"imported_objects": newObjectNames,
		"orientation":      importResult["orientation"],
		"import_message":   importResult["message"],
	}

	// Optional: place and/or uniform-scale the imported roots before reducing
	// geometry, so a poly-budget pass (if any) measures the final placement.
	if (p.HasLocation || p.HasScale) && len(newObjectNames) > 0 {
		if err := applyPlacement(ctx, bridge, newObjectNames, p); err != nil {
			result["placement_error"] = err.Error()
		}
	}

	// Optional: reduce the largest imported mesh(es) toward a total vertex
	// budget, mirroring the Python pipeline's per-asset simplify pass.
	if p.TargetPolyBudget > 0 && len(newObjectNames) > 0 {
		simplifyReport, err := simplifyToPolyBudget(ctx, bridge, newObjectNames, p.TargetPolyBudget, p.ReductionMethod)
		if err != nil {
			result["simplify_error"] = err.Error()
		} else {
			result["simplify"] = simplifyReport
		}
	}

	// Optional: file the import into a named collection hierarchy.
	if p.CollectionPath != "" {
		groupName := p.AssetID
		if idx := strings.LastIndex(p.CollectionPath, "/"); idx >= 0 && idx+1 < len(p.CollectionPath) {
			groupName = p.CollectionPath[idx+1:]
		}
		organizeRaw, err := bridge.CallBridge(ctx, "organize_scene_hierarchy", map[string]any{
			"groups": []map[string]any{
				{
					"name":            groupName,
					"objects":         newObjectNames,
					"collection_path": p.CollectionPath,
				},
			},
		}, heavyTimeout)
		if err != nil {
			result["organize_error"] = err.Error()
		} else {
			var organizeResult map[string]any
			if json.Unmarshal(organizeRaw, &organizeResult) == nil {
				result["organize"] = organizeResult
			}
		}
	}

	return result, nil
}

// applyPlacement sets absolute location and/or a uniform scale-to-size on
// every newly imported object. This is a narrower port than the Python
// pipeline: it applies location/scale to every new object independently
// rather than computing one combined bounding box across the whole import
// and moving/scaling only the roots -- fine for a single-root import (the
// common case), imprecise for a multi-root import where objects should move
// together as a rigid group.
func applyPlacement(ctx context.Context, bridge BridgeCaller, objectNames []string, p ImportParams) error {
	var scaleFactor float64
	if p.HasScale && len(objectNames) > 0 {
		raw, err := bridge.CallBridge(ctx, "get_object_info", map[string]any{"name": objectNames[0]}, heavyTimeout)
		if err != nil {
			return fmt.Errorf("reading dimensions for scale-to-size: %w", err)
		}
		var info map[string]any
		if err := json.Unmarshal(raw, &info); err != nil {
			return err
		}
		dims, _ := info["dimensions"].([]any)
		maxDim := 0.0
		for _, d := range dims {
			if f := asFloat(d); f > maxDim {
				maxDim = f
			}
		}
		if maxDim <= 0 {
			return fmt.Errorf("could not determine current size of %q to compute scale-to-size", objectNames[0])
		}
		scaleFactor = p.ScaleToSize / maxDim
	}

	for _, name := range objectNames {
		params := map[string]any{"name": name}
		if p.HasLocation {
			params["location"] = []float64{p.Location[0], p.Location[1], p.Location[2]}
		}
		if p.HasScale {
			params["delta_scale"] = []float64{scaleFactor, scaleFactor, scaleFactor}
		}
		if len(params) == 1 {
			continue
		}
		if _, err := bridge.CallBridge(ctx, "set_object_transform", params, heavyTimeout); err != nil {
			return err
		}
	}
	return nil
}

// simplifyToPolyBudget calls simplify_geometry on each new mesh object,
// scaling each object's target proportionally to its share of the combined
// vertex count so the total lands near targetTotal. Objects the quality gate
// rejects are left at their original vertex count and reported, not silently
// dropped -- matching this CLI's simplify-geometry command's own behavior.
func simplifyToPolyBudget(ctx context.Context, bridge BridgeCaller, objectNames []string, targetTotal int, method string) (map[string]any, error) {
	if method == "" {
		method = "simplify"
	}
	if method != "simplify" {
		return map[string]any{
			"skipped": fmt.Sprintf("reduction_method %q not implemented in this CLI port; only 'simplify' is wired", method),
		}, nil
	}

	type objCount struct {
		name  string
		verts int
	}
	var objects []objCount
	total := 0
	for _, name := range objectNames {
		raw, err := bridge.CallBridge(ctx, "get_object_info", map[string]any{"name": name}, heavyTimeout)
		if err != nil {
			continue
		}
		var info map[string]any
		if json.Unmarshal(raw, &info) != nil {
			continue
		}
		meshData, _ := info["mesh_data"].(map[string]any)
		verts := int(asFloat(meshData["vertices_count"]))
		if verts <= 0 {
			continue
		}
		objects = append(objects, objCount{name: name, verts: verts})
		total += verts
	}
	if total == 0 || total <= targetTotal {
		return map[string]any{"skipped": "already at or under target_poly_budget"}, nil
	}

	factor := float64(targetTotal) / float64(total)
	results := make([]map[string]any, 0, len(objects))
	for _, o := range objects {
		target := int(float64(o.verts) * factor)
		if target < 50 {
			target = 50
		}
		raw, err := bridge.CallBridge(ctx, "simplify_geometry", map[string]any{
			"object_name": o.name,
			"target":      target,
			"target_unit": "VERTICES",
		}, heavyTimeout)
		entry := map[string]any{"object_name": o.name, "original_vertices": o.verts, "target": target}
		if err != nil {
			entry["error"] = err.Error()
		} else {
			var simplifyResult map[string]any
			if json.Unmarshal(raw, &simplifyResult) == nil {
				entry["result"] = simplifyResult
			}
		}
		results = append(results, entry)
	}
	return map[string]any{"objects": results, "original_total": total, "target_total": targetTotal}, nil
}

func downloadFile(ctx context.Context, rawURL, destDir, filename string) (string, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, rawURL, nil)
	if err != nil {
		return "", err
	}
	req.Header.Set("User-Agent", userAgent)

	client := &http.Client{Timeout: 120 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("downloading %s: %w", rawURL, err)
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return "", fmt.Errorf("downloading %s returned HTTP %d", rawURL, resp.StatusCode)
	}

	destPath := filepath.Join(destDir, filename)
	if err := os.MkdirAll(filepath.Dir(destPath), 0o755); err != nil {
		return "", err
	}
	out, err := os.Create(destPath)
	if err != nil {
		return "", err
	}
	defer out.Close()

	if _, err := io.Copy(out, resp.Body); err != nil {
		return "", fmt.Errorf("writing %s: %w", destPath, err)
	}
	return destPath, nil
}

// downloadPolyhavenModel picks the lowest-resolution glTF variant (geometry
// fidelity is unaffected by texture resolution; the 1k texture set is enough
// to see the model, and this CLI doesn't need to reproduce Poly Haven's full
// resolution-selection UI) and downloads the .gltf + its .bin + textures.
func downloadPolyhavenModel(ctx context.Context, assetID, workDir string) (string, error) {
	var files map[string]any
	if err := httpGetJSON(ctx, fmt.Sprintf("https://api.polyhaven.com/files/%s", assetID), &files); err != nil {
		return "", fmt.Errorf("fetching Poly Haven file manifest for %q: %w", assetID, err)
	}

	gltfByRes, ok := files["gltf"].(map[string]any)
	if !ok || len(gltfByRes) == 0 {
		return "", fmt.Errorf("Poly Haven asset %q has no gltf variant available", assetID)
	}

	resolutions := make([]string, 0, len(gltfByRes))
	for res := range gltfByRes {
		resolutions = append(resolutions, res)
	}
	sort.Strings(resolutions) // "1k" < "2k" < "4k" < "8k" lexically for this naming scheme
	chosenRes := resolutions[0]

	variant, ok := gltfByRes[chosenRes].(map[string]any)
	if !ok {
		return "", fmt.Errorf("unexpected Poly Haven manifest shape for %q at resolution %q", assetID, chosenRes)
	}
	gltfInfo, ok := variant["gltf"].(map[string]any)
	if !ok {
		return "", fmt.Errorf("Poly Haven asset %q resolution %q has no gltf entry", assetID, chosenRes)
	}

	mainURL, _ := gltfInfo["url"].(string)
	if mainURL == "" {
		return "", fmt.Errorf("Poly Haven asset %q has no gltf download URL", assetID)
	}
	mainPath, err := downloadFile(ctx, mainURL, workDir, filepath.Base(mainURL))
	if err != nil {
		return "", err
	}

	include, _ := gltfInfo["include"].(map[string]any)
	for relPath, meta := range include {
		metaMap, ok := meta.(map[string]any)
		if !ok {
			continue
		}
		fileURL, _ := metaMap["url"].(string)
		if fileURL == "" {
			continue
		}
		if _, err := downloadFile(ctx, fileURL, workDir, relPath); err != nil {
			// A missing texture shouldn't block geometry import; the model
			// will just render untextured. A missing .bin would break the
			// gltf load, but that failure surfaces clearly at import_file time.
			continue
		}
	}

	return mainPath, nil
}

// downloadSketchfabModel resolves a signed, short-lived (~5 minute) download
// URL via the authenticated download endpoint and fetches the glb variant.
// Requires SKETCHFAB_API_TOKEN.
func downloadSketchfabModel(ctx context.Context, uid, workDir string) (string, error) {
	token := strings.TrimSpace(os.Getenv("SKETCHFAB_API_TOKEN"))
	if token == "" {
		return "", fmt.Errorf("SKETCHFAB_API_TOKEN is not set; Sketchfab requires a token to download (search does not)")
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet,
		fmt.Sprintf("https://api.sketchfab.com/v3/models/%s/download", uid), nil)
	if err != nil {
		return "", err
	}
	req.Header.Set("Authorization", "Token "+token)
	req.Header.Set("User-Agent", userAgent)

	client := &http.Client{Timeout: httpTimeout}
	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("requesting Sketchfab download URL: %w", err)
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}
	if resp.StatusCode >= 400 {
		return "", fmt.Errorf("Sketchfab download request for %q returned HTTP %d: %s", uid, resp.StatusCode, string(body))
	}

	var data map[string]struct {
		URL string `json:"url"`
	}
	if err := json.Unmarshal(body, &data); err != nil {
		return "", fmt.Errorf("parsing Sketchfab download response: %w", err)
	}
	glb, ok := data["glb"]
	if !ok || glb.URL == "" {
		return "", fmt.Errorf("Sketchfab model %q has no glb download variant", uid)
	}

	// The signed URL expires in ~300s; download immediately.
	return downloadFile(ctx, glb.URL, workDir, uid+".glb")
}

func stringSlice(v any) []string {
	arr, ok := v.([]any)
	if !ok {
		return nil
	}
	out := make([]string, 0, len(arr))
	for _, item := range arr {
		if s, ok := item.(string); ok {
			out = append(out, s)
		}
	}
	return out
}

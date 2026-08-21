// Package blenderassets is a Go port of the online-asset search + import
// pipeline in mcp_server/src/mcp_blender/tools/asset_source_ops.py and
// extension/tools/super_import_ops.py. It exists because that pipeline's HTTP
// fetching (Poly Haven / Sketchfab / ambientCG APIs) runs inside the Python
// mcp_server process, not over the Blender WebSocket bridge -- the bridge
// only has an import_file method for a local path already on disk. This
// package does the fetching in Go and hands the resulting local file to the
// bridge.
package blenderassets

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"net/http"
	"net/url"
	"sort"
	"strconv"
	"strings"
	"time"
)

const (
	userAgent          = "mcp-blender-pp-cli/1.0"
	polyhavenAssetsURL = "https://api.polyhaven.com/assets?t=models"
	sketchfabSearchURL = "https://api.sketchfab.com/v3/search"
	ambientcgSearchURL = "https://ambientcg.com/api/v2/full_json"
	httpTimeout        = 15 * time.Second
)

// Hit mirrors the unified hit shape search_online_assets returns on the
// Python side (id, provider, name, polycount, downloads, license, credits,
// thumbnail_url, asset_type).
type Hit struct {
	ID           string `json:"id"`
	Provider     string `json:"provider"`
	Name         string `json:"name"`
	Polycount    int    `json:"polycount"`
	Downloads    int    `json:"downloads"`
	License      string `json:"license"`
	Credits      string `json:"credits"`
	ThumbnailURL string `json:"thumbnail_url,omitempty"`
	AssetType    string `json:"asset_type"`
}

func httpGetJSON(ctx context.Context, rawURL string, out any) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, rawURL, nil)
	if err != nil {
		return err
	}
	req.Header.Set("User-Agent", userAgent)

	client := &http.Client{Timeout: httpTimeout}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return err
	}
	if resp.StatusCode >= 400 {
		return fmt.Errorf("GET %s returned HTTP %d", rawURL, resp.StatusCode)
	}
	return json.Unmarshal(body, out)
}

var polyhavenCache map[string]map[string]any

func polyhavenModelsIndex(ctx context.Context) (map[string]map[string]any, error) {
	if polyhavenCache != nil {
		return polyhavenCache, nil
	}
	var data map[string]map[string]any
	if err := httpGetJSON(ctx, polyhavenAssetsURL, &data); err != nil {
		return nil, err
	}
	polyhavenCache = data
	return data, nil
}

// SearchPolyhaven mirrors search_polyhaven_models: relevance+popularity
// ranked search over the CC0 model catalog. No API key required.
func SearchPolyhaven(ctx context.Context, query string, limit, offset int) ([]Hit, error) {
	assets, err := polyhavenModelsIndex(ctx)
	if err != nil {
		return nil, err
	}
	if len(assets) == 0 {
		return nil, nil
	}

	needle := strings.ToLower(strings.TrimSpace(query))
	words := strings.Fields(needle)

	type scored struct {
		score float64
		id    string
		info  map[string]any
	}
	var candidates []scored

	if len(words) == 0 {
		for id, info := range assets {
			candidates = append(candidates, scored{score: asFloat(info["download_count"]), id: id, info: info})
		}
		sort.Slice(candidates, func(i, j int) bool { return candidates[i].score > candidates[j].score })
	} else {
		for id, info := range assets {
			name := strings.ToLower(asString(info["name"], id))
			tags := toLowerStrings(info["tags"])
			cats := toLowerStrings(info["categories"])
			desc := strings.ToLower(asString(info["description"], ""))

			score := 0.0
			matched := false
			for _, w := range words {
				switch {
				case w == name || w == strings.ToLower(id):
					score += 1000
					matched = true
				case strings.Contains(name, w):
					score += 300
					matched = true
				case containsAny(tags, w):
					score += 100
					matched = true
				case containsAny(cats, w):
					score += 50
					matched = true
				case strings.Contains(desc, w):
					score += 10
					matched = true
				}
			}
			if matched {
				dl := asFloat(info["download_count"])
				if dl < 1 {
					dl = 1
				}
				finalScore := score * (1 + math.Log10(dl))
				candidates = append(candidates, scored{score: finalScore, id: id, info: info})
			}
		}
		sort.Slice(candidates, func(i, j int) bool { return candidates[i].score > candidates[j].score })
	}

	start, end := paginate(len(candidates), offset, limit)
	hits := make([]Hit, 0, end-start)
	for _, c := range candidates[start:end] {
		authors := ""
		if a, ok := c.info["authors"].(map[string]any); ok {
			names := make([]string, 0, len(a))
			for k := range a {
				names = append(names, k)
			}
			sort.Strings(names)
			authors = strings.Join(names, ", ")
		}
		if authors == "" {
			authors = "Unknown"
		}
		thumb := asString(c.info["thumbnail_url"], "")
		if thumb == "" {
			thumb = fmt.Sprintf("https://cdn.polyhaven.com/asset_img/thumbs/%s.png?width=256&height=256", c.id)
		}
		hits = append(hits, Hit{
			ID:           c.id,
			Provider:     "polyhaven",
			Name:         asString(c.info["name"], c.id),
			Polycount:    int(asFloat(c.info["polycount"])),
			Downloads:    int(asFloat(c.info["download_count"])),
			License:      "CC0",
			Credits:      fmt.Sprintf("Poly Haven CC0 by %s", authors),
			ThumbnailURL: thumb,
			AssetType:    "MODEL",
		})
	}
	return hits, nil
}

// SearchSketchfab mirrors search_sketchfab_models: keyless public search
// (a token is only needed to download).
func SearchSketchfab(ctx context.Context, query string, limit, offset int) ([]Hit, error) {
	if strings.TrimSpace(query) == "" {
		return nil, nil
	}
	values := url.Values{}
	values.Set("type", "models")
	values.Set("q", query)
	values.Set("downloadable", "true")
	values.Set("count", strconv.Itoa(limit))
	values.Set("offset", strconv.Itoa(offset))

	var data struct {
		Results []struct {
			UID     string `json:"uid"`
			Name    string `json:"name"`
			Vertex  int    `json:"vertexCount"`
			Face    int    `json:"faceCount"`
			Like    int    `json:"likeCount"`
			License struct {
				Label string `json:"label"`
			} `json:"license"`
			User struct {
				DisplayName string `json:"displayName"`
				Username    string `json:"username"`
			} `json:"user"`
			Thumbnails struct {
				Images []struct {
					URL string `json:"url"`
				} `json:"images"`
			} `json:"thumbnails"`
		} `json:"results"`
	}
	if err := httpGetJSON(ctx, sketchfabSearchURL+"?"+values.Encode(), &data); err != nil {
		return nil, err
	}

	hits := make([]Hit, 0, len(data.Results))
	for _, r := range data.Results {
		if r.UID == "" {
			continue
		}
		lic := r.License.Label
		if lic == "" {
			lic = "CC Attribution"
		}
		user := r.User.DisplayName
		if user == "" {
			user = r.User.Username
		}
		if user == "" {
			user = "Sketchfab Creator"
		}
		polycount := r.Vertex
		if polycount == 0 {
			polycount = r.Face
		}
		thumb := ""
		if len(r.Thumbnails.Images) > 0 {
			thumb = r.Thumbnails.Images[0].URL
		}
		hits = append(hits, Hit{
			ID:           r.UID,
			Provider:     "sketchfab",
			Name:         orDefault(r.Name, r.UID),
			Polycount:    polycount,
			Downloads:    r.Like * 10,
			License:      lic,
			Credits:      fmt.Sprintf("Sketchfab (%s) by %s", lic, user),
			ThumbnailURL: thumb,
			AssetType:    "MODEL",
		})
	}
	return hits, nil
}

// SearchAmbientCG mirrors search_ambientcg_assets: CC0 materials/textures,
// occasionally 3D models.
func SearchAmbientCG(ctx context.Context, query string, limit, offset int) ([]Hit, error) {
	q := strings.TrimSpace(query)
	if q == "" {
		q = "Material"
	}
	values := url.Values{}
	values.Set("q", q)
	values.Set("limit", strconv.Itoa(limit))
	values.Set("sort", "Popular")
	values.Set("offset", strconv.Itoa(offset))

	var data struct {
		FoundAssets []struct {
			AssetID       string            `json:"assetId"`
			DisplayName   string            `json:"displayName"`
			DownloadCount int               `json:"downloadCount"`
			DataType      string            `json:"dataType"`
			PreviewImage  map[string]string `json:"previewImage"`
		} `json:"foundAssets"`
	}
	if err := httpGetJSON(ctx, ambientcgSearchURL+"?"+values.Encode(), &data); err != nil {
		return nil, err
	}

	hits := make([]Hit, 0, len(data.FoundAssets))
	for _, a := range data.FoundAssets {
		if a.AssetID == "" {
			continue
		}
		downloads := a.DownloadCount
		if downloads == 0 {
			downloads = 5000
		}
		assetType := "TEXTURE"
		if a.DataType == "3DModel" {
			assetType = "MODEL"
		}
		hits = append(hits, Hit{
			ID:           a.AssetID,
			Provider:     "ambientcg",
			Name:         orDefault(a.DisplayName, a.AssetID),
			Downloads:    downloads,
			License:      "CC0",
			Credits:      fmt.Sprintf("ambientCG CC0 (%s)", a.AssetID),
			ThumbnailURL: a.PreviewImage["256-PNG"],
			AssetType:    assetType,
		})
	}
	return hits, nil
}

// SearchAll mirrors search_all_online_models: fan out to the requested
// provider(s), merge, and re-rank by downloads.
func SearchAll(ctx context.Context, query, provider string, limit, offset int) ([]Hit, error) {
	provider = strings.ToUpper(strings.TrimSpace(provider))
	if provider == "" {
		provider = "ALL"
	}
	if limit <= 0 {
		limit = 20
	}

	var all []Hit
	var firstErr error
	tryAdd := func(hits []Hit, err error) {
		if err != nil {
			if firstErr == nil {
				firstErr = err
			}
			return
		}
		all = append(all, hits...)
	}

	if provider == "ALL" || provider == "POLYHAVEN" {
		tryAdd(SearchPolyhaven(ctx, query, limit, offset))
	}
	if provider == "ALL" || provider == "SKETCHFAB" {
		tryAdd(SearchSketchfab(ctx, query, limit, offset))
	}
	if provider == "ALL" || provider == "AMBIENTCG" {
		tryAdd(SearchAmbientCG(ctx, query, limit, offset))
	}

	if len(all) == 0 && firstErr != nil {
		return nil, firstErr
	}

	sort.Slice(all, func(i, j int) bool { return all[i].Downloads > all[j].Downloads })
	if len(all) > limit {
		all = all[:limit]
	}
	return all, nil
}

func paginate(total, offset, limit int) (int, int) {
	if offset < 0 {
		offset = 0
	}
	if offset > total {
		offset = total
	}
	end := offset + limit
	if end > total {
		end = total
	}
	return offset, end
}

func asFloat(v any) float64 {
	switch n := v.(type) {
	case float64:
		return n
	case int:
		return float64(n)
	case json.Number:
		f, _ := n.Float64()
		return f
	default:
		return 0
	}
}

func asString(v any, fallback string) string {
	if s, ok := v.(string); ok && s != "" {
		return s
	}
	return fallback
}

func orDefault(s, fallback string) string {
	if s == "" {
		return fallback
	}
	return s
}

func toLowerStrings(v any) []string {
	arr, ok := v.([]any)
	if !ok {
		return nil
	}
	out := make([]string, 0, len(arr))
	for _, item := range arr {
		if s, ok := item.(string); ok {
			out = append(out, strings.ToLower(s))
		}
	}
	return out
}

func containsAny(haystack []string, needle string) bool {
	for _, h := range haystack {
		if strings.Contains(h, needle) {
			return true
		}
	}
	return false
}

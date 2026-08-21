// Copyright 2026 pakkio and contributors. Licensed under Apache-2.0.
//
// Hand-patched (see .printing-press-patches/0002-vlm-and-asset-pipeline.md):
// the generated version posted to a synthetic /blender_scene/regen path that
// has no bridge equivalent. The real regen_names tool
// (mcp_server/src/mcp_blender/tools/localization_ops.py) is mostly a single
// bridge call (regen_element_names, pure structural rename via a keyword
// vocabulary) plus an OPTIONAL per-object vision-assisted pass on top for
// mesh leaves the vocabulary can't cover. This version reimplements both
// steps directly against the bridge + OpenRouter, instead of requiring the
// Python mcp_server process.

package cli

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"mcp-blender-pp-cli/internal/vlm"

	"github.com/spf13/cobra"
)

var langDisplayNames = map[string]string{"it": "Italian"}

const defaultMaxVisionRenames = 15

func newSceneRegenCmd(flags *rootFlags) *cobra.Command {
	var lang string
	var element string
	var useVision bool
	var maxVisionRenames int
	var visionModel string

	cmd := &cobra.Command{
		Use:   "regen",
		Short: "Regenerate scene element names in a target language, optionally vision-assisted",
		Long: "Renames category collections/Empties via a keyword vocabulary (e.g. 'Furniture' -> 'Arredamento'). " +
			"Pass --element to scope this to one collection or root-Empty instead of the whole scene. Pass " +
			"--use-vision to also name mesh leaves the vocabulary can't cover, by looking at each one and asking " +
			"a vision model for its semantic role. Requires OPENROUTER_API_KEY for --use-vision; without it, " +
			"vision naming is silently skipped and only the structural pass runs.",
		Example: "  mcp-blender-pp-cli scene regen --lang it\n  mcp-blender-pp-cli scene regen --lang it --use-vision",
		RunE: func(cmd *cobra.Command, args []string) error {
			result, err := sceneRegen(cmd.Context(), flags, lang, element, useVision, maxVisionRenames, visionModel)
			if err != nil {
				return classifyAPIError(cmd.OutOrStdout(), err, flags)
			}
			data, err := json.Marshal(result)
			if err != nil {
				return err
			}
			return printOutputWithFlagsMeta(cmd.OutOrStdout(), data, flags, map[string]any{"source": "live"}, nil)
		},
	}
	cmd.Flags().StringVar(&lang, "lang", "it", "target language, e.g. it")
	cmd.Flags().StringVar(&element, "element", "", "optional single element (collection/root-empty) to rename")
	cmd.Flags().BoolVar(&useVision, "use-vision", false, "use a vision model to name mesh leaves the keyword vocabulary can't cover")
	cmd.Flags().IntVar(&maxVisionRenames, "max-vision-renames", defaultMaxVisionRenames, "cap on vision-assisted renames per call")
	cmd.Flags().StringVar(&visionModel, "vision-model", "", "OpenRouter model override for the vision pass")

	return cmd
}

func sceneRegen(ctx context.Context, flags *rootFlags, lang, element string, useVision bool, maxVisionRenames int, visionModel string) (map[string]any, error) {
	c, err := flags.newClient()
	if err != nil {
		return nil, err
	}

	structuralParams := map[string]any{"lang": lang}
	if element != "" {
		structuralParams["element"] = element
	}
	raw, err := c.CallBridge(ctx, "regen_element_names", structuralParams, heavyBridgeTimeout)
	if err != nil {
		return nil, err
	}
	var structural map[string]any
	if err := json.Unmarshal(raw, &structural); err != nil {
		return nil, fmt.Errorf("parsing regen_element_names result: %w", err)
	}
	if ok, _ := structural["success"].(bool); !ok {
		msg, _ := structural["message"].(string)
		if msg == "" {
			msg = "regen_element_names failed"
		}
		return nil, fmt.Errorf("%s", msg)
	}

	root, _ := structural["root"].(map[string]any)
	visionRenames := []map[string]any{}
	var visionNote string

	if useVision {
		if !vlm.IsConfigured() {
			visionNote = "use_vision requested but OPENROUTER_API_KEY is not set -- structural pass only."
		} else {
			langName := langDisplayNames[lang]
			if langName == "" {
				langName = lang
			}
			candidates := collectMeshObjects(root, maxVisionRenames)
			for _, candidate := range candidates {
				objName, _ := candidate["name"].(string)
				category, _ := candidate["category"].(string)

				captureRaw, err := c.CallBridge(ctx, "inspect_focus_shot", map[string]any{
					"target_object": objName, "include_base64": true,
				}, heavyBridgeTimeout)
				if err != nil {
					continue
				}
				var capture map[string]any
				if json.Unmarshal(captureRaw, &capture) != nil {
					continue
				}
				if ok, _ := capture["success"].(bool); !ok {
					continue
				}
				pngBytes, err := vlm.ExtractPNGBytes(capture, "image_base64")
				if err != nil {
					continue
				}

				context := ""
				if category != "" {
					context = fmt.Sprintf(" It belongs to the '%s' group.", category)
				}
				question := fmt.Sprintf(
					"This 3D model part is currently named '%s'.%s In one or two words, name it by its SEMANTIC "+
						"ROLE or FUNCTION within the whole object (e.g. 'leg', 'seat', 'wheel', 'handle', 'blade') "+
						"-- NOT its geometric shape (never answer 'cube', 'cylinder', 'sphere', 'cone', or similar). "+
						"Reply in %s with ONLY that name, capitalized, no punctuation.",
					objName, context, langName,
				)
				verdict, err := vlm.CritiqueImage(ctx, question, pngBytes, visionModel)
				if err != nil {
					continue
				}
				newName := sanitizeVisionName(verdict.Critique)
				if newName == "" {
					continue
				}

				renameRaw, err := c.CallBridge(ctx, "set_object_properties", map[string]any{
					"name": objName, "new_name": newName,
				}, 0)
				if err != nil {
					continue
				}
				var renameResult map[string]any
				if json.Unmarshal(renameRaw, &renameResult) != nil {
					continue
				}
				if ok, _ := renameResult["success"].(bool); ok {
					visionRenames = append(visionRenames, map[string]any{
						"old_name": objName,
						"new_name": renameResult["name"],
					})
				}
			}
		}
	}

	result := map[string]any{
		"success":        true,
		"message":        structural["message"],
		"lang":           lang,
		"structural":     root,
		"vision_used":    useVision && vlm.IsConfigured(),
		"vision_renames": visionRenames,
	}
	if visionNote != "" {
		result["vision_note"] = visionNote
	}
	return result, nil
}

// collectMeshObjects flattens the regen_element_names report tree into every
// MESH leaf, each carrying its category (immediate parent collection's
// new_name) for vision-prompt context. Mirrors localization_ops.py's
// _collect_mesh_objects.
func collectMeshObjects(node map[string]any, limit int) []map[string]any {
	var found []map[string]any
	var walk func(n map[string]any)
	walk = func(n map[string]any) {
		if n == nil || (limit > 0 && len(found) >= limit) {
			return
		}
		if objects, ok := n["objects"].([]any); ok {
			for _, o := range objects {
				obj, ok := o.(map[string]any)
				if !ok {
					continue
				}
				if t, _ := obj["type"].(string); t == "MESH" {
					name, _ := obj["name"].(string)
					found = append(found, map[string]any{"name": name, "category": n["new_name"]})
					if limit > 0 && len(found) >= limit {
						return
					}
				}
			}
		}
		if children, ok := n["children"].([]any); ok {
			for _, c := range children {
				if child, ok := c.(map[string]any); ok {
					walk(child)
				}
			}
		}
	}
	walk(node)
	return found
}

// sanitizeVisionName mirrors localization_ops.py's _sanitize_vision_name:
// vision models sometimes wrap the answer in a sentence or quotes despite
// instructions -- take the first line, strip quoting/trailing punctuation,
// and cap length so a rambling answer can't produce an unusable name.
func sanitizeVisionName(text string) string {
	trimmed := strings.TrimSpace(text)
	if trimmed == "" {
		return ""
	}
	firstLine := strings.SplitN(trimmed, "\n", 2)[0]
	firstLine = strings.Trim(strings.TrimSpace(firstLine), " .\"'“”")
	if len(firstLine) > 40 {
		firstLine = firstLine[:40]
	}
	return firstLine
}

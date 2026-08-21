// Copyright 2026 pakkio and contributors. Licensed under Apache-2.0.
//
// Hand-patched (see .printing-press-patches/0002-vlm-and-asset-pipeline.md):
// the generated version of this file sent the wrong param names (this
// spec.yaml declared camera_name/prompt/resolution; the real MCP tool takes
// question/target_object/view/model) and posted them over the WebSocket
// bridge, which has no evaluate_scene_visually method -- that logic lives in
// mcp_server's Python process (bridge screenshot + OpenRouter VLM call). This
// version reimplements it directly: capture a screenshot via the real bridge
// methods (inspect_focus_shot / capture_multiview_audit), then send it to
// OpenRouter for critique, mirroring
// mcp_server/src/mcp_blender/tools/vision_eval_ops.py.

package cli

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"mcp-blender-pp-cli/internal/vlm"

	"github.com/spf13/cobra"
)

const heavyBridgeTimeout = 600 * time.Second

func newEvaluateSceneVisuallyPromotedCmd(flags *rootFlags) *cobra.Command {
	var question string
	var targetObject string
	var view string
	var model string

	cmd := &cobra.Command{
		Use:   "evaluate-scene-visually",
		Short: "Get a text critique of the rendered scene from a vision model via OpenRouter",
		Long: "When you cannot see rendered images yourself, use this to get a text critique of the scene from a " +
			"cheap vision-capable model via OpenRouter. Captures a multiview audit (or a focused close-up on " +
			"--target-object) and asks --question about it. Requires OPENROUTER_API_KEY in the environment.",
		Example:     "  mcp-blender-pp-cli evaluate-scene-visually --question \"Is the lighting even?\"",
		Annotations: map[string]string{"pp:endpoint": "evaluate_scene_visually.evaluate", "mcp:read-only": "true"},
		RunE: func(cmd *cobra.Command, args []string) error {
			if strings.TrimSpace(question) == "" && !flags.dryRun {
				return cmd.Help()
			}

			result, err := evaluateSceneVisually(cmd.Context(), flags, question, targetObject, view, model)
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
	cmd.Flags().StringVar(&question, "question", "", "What to ask the vision model about the captured scene (required)")
	cmd.Flags().StringVar(&targetObject, "target-object", "", "Object to focus on (required when --view=FOCUS)")
	cmd.Flags().StringVar(&view, "view", "MULTIVIEW", "MULTIVIEW (default) or FOCUS")
	cmd.Flags().StringVar(&model, "model", "", "OpenRouter model override (default: OPENROUTER_VISION_MODEL env or google/gemini-2.5-flash)")

	return cmd
}

func evaluateSceneVisually(ctx context.Context, flags *rootFlags, question, targetObject, view, model string) (map[string]any, error) {
	if !vlm.IsConfigured() {
		return map[string]any{
			"success": false,
			"message": "OPENROUTER_API_KEY is not set, so evaluate-scene-visually cannot run. " +
				"Set it in your environment, or capture a screenshot yourself via " +
				"'camera-lighting screenshot' and look at it directly.",
		}, nil
	}

	c, err := flags.newClient()
	if err != nil {
		return nil, err
	}

	view = strings.ToUpper(strings.TrimSpace(view))
	if view == "" {
		view = "MULTIVIEW"
	}

	var captureResult map[string]any
	var imageKey string

	switch view {
	case "FOCUS":
		if strings.TrimSpace(targetObject) == "" {
			return nil, fmt.Errorf("--target-object is required when --view=FOCUS")
		}
		raw, err := c.CallBridge(ctx, "inspect_focus_shot", map[string]any{
			"target_object": targetObject, "include_base64": true,
		}, heavyBridgeTimeout)
		if err != nil {
			return nil, err
		}
		if err := json.Unmarshal(raw, &captureResult); err != nil {
			return nil, fmt.Errorf("parsing inspect_focus_shot result: %w", err)
		}
		imageKey = "image_base64"
	case "MULTIVIEW":
		params := map[string]any{"include_base64": true}
		if targetObject != "" {
			params["target_object"] = targetObject
		}
		raw, err := c.CallBridge(ctx, "capture_multiview_audit", params, heavyBridgeTimeout)
		if err != nil {
			return nil, err
		}
		if err := json.Unmarshal(raw, &captureResult); err != nil {
			return nil, fmt.Errorf("parsing capture_multiview_audit result: %w", err)
		}
		imageKey = "base64_data_uri"
	default:
		return nil, fmt.Errorf("invalid --view %q: expected MULTIVIEW or FOCUS", view)
	}

	if ok, _ := captureResult["success"].(bool); !ok {
		msg, _ := captureResult["message"].(string)
		if msg == "" {
			msg = "scene capture failed"
		}
		return nil, fmt.Errorf("%s", msg)
	}

	pngBytes, err := vlm.ExtractPNGBytes(captureResult, imageKey)
	if err != nil {
		return nil, fmt.Errorf("scene capture did not return usable image data: %w", err)
	}

	verdict, err := vlm.CritiqueImage(ctx, question, pngBytes, model)
	if err != nil {
		return map[string]any{"success": false, "message": err.Error()}, nil
	}

	return map[string]any{
		"success":           true,
		"question":          question,
		"critique":          verdict.Critique,
		"model":             verdict.Model,
		"prompt_tokens":     verdict.PromptTokens,
		"completion_tokens": verdict.CompletionTokens,
	}, nil
}

// Package vlm is a Go port of mcp_server/src/mcp_blender/vlm.py: a thin
// OpenRouter chat-completions client used to critique Blender viewport
// captures when the calling agent cannot itself see image content blocks.
package vlm

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

const (
	openRouterURL      = "https://openrouter.ai/api/v1/chat/completions"
	defaultVisionModel = "google/gemini-2.5-flash"
	requestTimeout     = 60 * time.Second
)

// IsConfigured mirrors vlm.py's is_configured(): true only when an
// OpenRouter API key is present in the environment.
func IsConfigured() bool {
	return strings.TrimSpace(os.Getenv("OPENROUTER_API_KEY")) != ""
}

// ResolveModel mirrors vlm.py's resolve_model(): explicit override, then
// OPENROUTER_VISION_MODEL, then the default.
func ResolveModel(override string) string {
	if override != "" {
		return override
	}
	if m := os.Getenv("OPENROUTER_VISION_MODEL"); m != "" {
		return m
	}
	return defaultVisionModel
}

// Verdict is the subset of an OpenRouter chat-completion response this CLI
// surfaces, matching the fields evaluate_scene_visually / regen_names return
// on the Python side.
type Verdict struct {
	Critique         string `json:"critique"`
	Model            string `json:"model"`
	PromptTokens     int    `json:"prompt_tokens"`
	CompletionTokens int    `json:"completion_tokens"`
}

// CritiqueImage sends a question plus a PNG image to OpenRouter and returns
// the model's text critique. Mirrors vlm.py's critique_image, minus the
// vision-incompatible-model retry loop (that logic exists in the Python
// client to auto-fallback across a candidate model list; this port surfaces
// the error instead so the caller can decide whether to retry with a
// different --model).
func CritiqueImage(ctx context.Context, question string, pngBytes []byte, model string) (*Verdict, error) {
	apiKey := strings.TrimSpace(os.Getenv("OPENROUTER_API_KEY"))
	if apiKey == "" {
		return nil, fmt.Errorf(
			"OPENROUTER_API_KEY is not set. Add it to your environment (or .env) to enable this command",
		)
	}

	resolvedModel := ResolveModel(model)
	dataURI := "data:image/png;base64," + base64.StdEncoding.EncodeToString(pngBytes)

	payload := map[string]any{
		"model": resolvedModel,
		"messages": []map[string]any{
			{
				"role": "user",
				"content": []map[string]any{
					{"type": "text", "text": question},
					{"type": "image_url", "image_url": map[string]string{"url": dataURI}},
				},
			},
		},
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("encoding OpenRouter request: %w", err)
	}

	reqCtx, cancel := context.WithTimeout(ctx, requestTimeout)
	defer cancel()
	req, err := http.NewRequestWithContext(reqCtx, http.MethodPost, openRouterURL, bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("building OpenRouter request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("OpenRouter request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("reading OpenRouter response: %w", err)
	}
	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("OpenRouter returned HTTP %d: %s", resp.StatusCode, strings.TrimSpace(string(respBody)))
	}

	var parsed struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
		Usage struct {
			PromptTokens     int `json:"prompt_tokens"`
			CompletionTokens int `json:"completion_tokens"`
		} `json:"usage"`
	}
	if err := json.Unmarshal(respBody, &parsed); err != nil {
		return nil, fmt.Errorf("parsing OpenRouter response: %w", err)
	}
	if len(parsed.Choices) == 0 {
		return nil, fmt.Errorf("OpenRouter response had no choices (model %q may not support vision)", resolvedModel)
	}

	return &Verdict{
		Critique:         parsed.Choices[0].Message.Content,
		Model:            resolvedModel,
		PromptTokens:     parsed.Usage.PromptTokens,
		CompletionTokens: parsed.Usage.CompletionTokens,
	}, nil
}

// ExtractPNGBytes mirrors vlm.py's extract_png_bytes: pulls a base64 (or
// data: URI) image out of a bridge JSON result by key and decodes it.
func ExtractPNGBytes(result map[string]any, key string) ([]byte, error) {
	raw, _ := result[key].(string)
	if raw == "" {
		return nil, fmt.Errorf("bridge result has no %q field", key)
	}
	if strings.HasPrefix(raw, "data:") {
		if idx := strings.Index(raw, ","); idx >= 0 {
			raw = raw[idx+1:]
		}
	}
	return base64.StdEncoding.DecodeString(raw)
}

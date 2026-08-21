package vlm

import (
	"os"
	"testing"
)

func TestIsConfigured(t *testing.T) {
	old := os.Getenv("OPENROUTER_API_KEY")
	defer os.Setenv("OPENROUTER_API_KEY", old)

	os.Unsetenv("OPENROUTER_API_KEY")
	if IsConfigured() {
		t.Error("IsConfigured() = true with no key set, want false")
	}

	os.Setenv("OPENROUTER_API_KEY", "sk-or-test")
	if !IsConfigured() {
		t.Error("IsConfigured() = false with key set, want true")
	}
}

func TestResolveModel(t *testing.T) {
	oldModel := os.Getenv("OPENROUTER_VISION_MODEL")
	defer os.Setenv("OPENROUTER_VISION_MODEL", oldModel)

	os.Unsetenv("OPENROUTER_VISION_MODEL")
	if got := ResolveModel(""); got != defaultVisionModel {
		t.Errorf("ResolveModel(\"\") = %q, want default %q", got, defaultVisionModel)
	}

	os.Setenv("OPENROUTER_VISION_MODEL", "env/model")
	if got := ResolveModel(""); got != "env/model" {
		t.Errorf("ResolveModel(\"\") with env set = %q, want env/model", got)
	}

	if got := ResolveModel("explicit/override"); got != "explicit/override" {
		t.Errorf("ResolveModel(explicit) = %q, want explicit/override", got)
	}
}

func TestExtractPNGBytes(t *testing.T) {
	raw := "aGVsbG8=" // base64("hello")
	result := map[string]any{"image_base64": raw}
	got, err := ExtractPNGBytes(result, "image_base64")
	if err != nil {
		t.Fatalf("ExtractPNGBytes returned error: %v", err)
	}
	if string(got) != "hello" {
		t.Errorf("ExtractPNGBytes = %q, want %q", got, "hello")
	}

	dataURI := map[string]any{"base64_data_uri": "data:image/png;base64," + raw}
	got, err = ExtractPNGBytes(dataURI, "base64_data_uri")
	if err != nil {
		t.Fatalf("ExtractPNGBytes (data URI) returned error: %v", err)
	}
	if string(got) != "hello" {
		t.Errorf("ExtractPNGBytes (data URI) = %q, want %q", got, "hello")
	}

	if _, err := ExtractPNGBytes(map[string]any{}, "missing"); err == nil {
		t.Error("ExtractPNGBytes with missing key should return an error")
	}
}

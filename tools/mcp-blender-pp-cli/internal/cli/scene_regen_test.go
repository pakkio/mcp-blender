package cli

import (
	"strings"
	"testing"
)

func TestSanitizeVisionName(t *testing.T) {
	longInput := strings.Repeat("A", 50)
	cases := map[string]string{
		"Leg":             "Leg",
		"  \"Leg.\"  ":    "Leg",
		"Leg\nExtra line": "Leg",
		"":                "",
		"   ":             "",
		longInput:         strings.Repeat("A", 40),
	}
	for in, want := range cases {
		if got := sanitizeVisionName(in); got != want {
			t.Errorf("sanitizeVisionName(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestCollectMeshObjects(t *testing.T) {
	tree := map[string]any{
		"new_name": "Furniture",
		"objects": []any{
			map[string]any{"name": "Chair_Mesh", "type": "MESH"},
			map[string]any{"name": "Light", "type": "LIGHT"},
		},
		"children": []any{
			map[string]any{
				"new_name": "Kitchen",
				"objects": []any{
					map[string]any{"name": "Table_Mesh", "type": "MESH"},
				},
				"children": []any{},
			},
		},
	}

	got := collectMeshObjects(tree, 0)
	if len(got) != 2 {
		t.Fatalf("collectMeshObjects returned %d entries, want 2: %+v", len(got), got)
	}
	if got[0]["name"] != "Chair_Mesh" || got[0]["category"] != "Furniture" {
		t.Errorf("first entry = %+v, want name=Chair_Mesh category=Furniture", got[0])
	}
	if got[1]["name"] != "Table_Mesh" || got[1]["category"] != "Kitchen" {
		t.Errorf("second entry = %+v, want name=Table_Mesh category=Kitchen", got[1])
	}
}

func TestCollectMeshObjectsLimit(t *testing.T) {
	tree := map[string]any{
		"new_name": "Root",
		"objects": []any{
			map[string]any{"name": "A", "type": "MESH"},
			map[string]any{"name": "B", "type": "MESH"},
			map[string]any{"name": "C", "type": "MESH"},
		},
	}
	got := collectMeshObjects(tree, 2)
	if len(got) != 2 {
		t.Fatalf("collectMeshObjects with limit=2 returned %d entries, want 2", len(got))
	}
}

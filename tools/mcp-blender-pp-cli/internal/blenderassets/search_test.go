package blenderassets

import "testing"

func TestPaginate(t *testing.T) {
	cases := []struct {
		name                 string
		total, offset, limit int
		wantStart, wantEnd   int
	}{
		{"basic", 10, 0, 5, 0, 5},
		{"offset within range", 10, 3, 5, 3, 8},
		{"limit exceeds remaining", 10, 8, 5, 8, 10},
		{"offset beyond total", 10, 20, 5, 10, 10},
		{"negative offset clamped", 10, -3, 5, 0, 5},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			start, end := paginate(c.total, c.offset, c.limit)
			if start != c.wantStart || end != c.wantEnd {
				t.Errorf("paginate(%d,%d,%d) = (%d,%d), want (%d,%d)",
					c.total, c.offset, c.limit, start, end, c.wantStart, c.wantEnd)
			}
		})
	}
}

func TestAsFloat(t *testing.T) {
	cases := []struct {
		name string
		in   any
		want float64
	}{
		{"float64", float64(3.5), 3.5},
		{"int", 7, 7.0},
		{"nil", nil, 0},
		{"string ignored", "abc", 0},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			if got := asFloat(c.in); got != c.want {
				t.Errorf("asFloat(%v) = %v, want %v", c.in, got, c.want)
			}
		})
	}
}

func TestAsString(t *testing.T) {
	if got := asString("hello", "fallback"); got != "hello" {
		t.Errorf("asString with value = %q, want %q", got, "hello")
	}
	if got := asString(nil, "fallback"); got != "fallback" {
		t.Errorf("asString with nil = %q, want %q", got, "fallback")
	}
	if got := asString("", "fallback"); got != "fallback" {
		t.Errorf("asString with empty string = %q, want %q", got, "fallback")
	}
}

func TestOrDefault(t *testing.T) {
	if got := orDefault("x", "y"); got != "x" {
		t.Errorf("orDefault(x,y) = %q, want x", got)
	}
	if got := orDefault("", "y"); got != "y" {
		t.Errorf("orDefault(empty,y) = %q, want y", got)
	}
}

func TestToLowerStrings(t *testing.T) {
	in := []any{"Foo", "BAR", 5}
	got := toLowerStrings(in)
	want := []string{"foo", "bar"}
	if len(got) != len(want) {
		t.Fatalf("toLowerStrings length = %d, want %d", len(got), len(want))
	}
	for i := range want {
		if got[i] != want[i] {
			t.Errorf("toLowerStrings[%d] = %q, want %q", i, got[i], want[i])
		}
	}
}

func TestContainsAny(t *testing.T) {
	haystack := []string{"medieval", "fortress"}
	if !containsAny(haystack, "fort") {
		t.Error("expected containsAny to find substring match")
	}
	if containsAny(haystack, "castle") {
		t.Error("expected containsAny to not match unrelated substring")
	}
}

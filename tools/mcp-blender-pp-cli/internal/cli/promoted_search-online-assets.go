// Copyright 2026 pakkio and contributors. Licensed under Apache-2.0.
//
// Hand-patched (see .printing-press-patches/0002-vlm-and-asset-pipeline.md):
// the generated version posted to a synthetic /search_online_assets path
// that has no bridge equivalent -- the real search_online_assets tool
// (mcp_server/src/mcp_blender/tools/asset_source_ops.py) does its HTTP
// fetching (Poly Haven / Sketchfab / ambientCG) entirely inside the Python
// process, never touching the Blender bridge. This version calls the Go
// port of that search logic directly (internal/blenderassets).

package cli

import (
	"encoding/json"
	"fmt"
	"os"

	"mcp-blender-pp-cli/internal/blenderassets"

	"github.com/spf13/cobra"
)

func newSearchOnlineAssetsPromotedCmd(flags *rootFlags) *cobra.Command {
	var query string
	var assetType string
	var providers string
	var limit int
	var freeOnly bool

	cmd := &cobra.Command{
		Use:   "search-online-assets",
		Short: "Search free/CC0 online asset libraries (Poly Haven, ambientCG, Sketchfab)",
		Long: "Search free/CC0 online asset libraries (Poly Haven, ambientCG for textures, Sketchfab for a much " +
			"larger catalog with mixed licenses) for a downloadable 3D model, texture, or HDRI. Call this BEFORE " +
			"hand-modelling any recognisable real-world object -- furniture, props, vehicles, plants. Returns " +
			"ranked hits with license and whether download needs a token you don't have configured.",
		Example:     "  mcp-blender-pp-cli search-online-assets --query \"wooden chair\"",
		Annotations: map[string]string{"pp:endpoint": "search_online_assets.search", "mcp:read-only": "true"},
		RunE: func(cmd *cobra.Command, args []string) error {
			if query == "" && !flags.dryRun {
				return cmd.Help()
			}

			providerArg := "ALL"
			if providers != "" {
				providerArg = providers
			}
			hits, err := blenderassets.SearchAll(cmd.Context(), query, providerArg, limit, 0)
			if err != nil {
				return classifyAPIError(cmd.OutOrStdout(), err, flags)
			}
			if assetType != "" {
				filtered := hits[:0]
				for _, h := range hits {
					if h.AssetType == assetType {
						filtered = append(filtered, h)
					}
				}
				hits = filtered
			}
			if freeOnly {
				filtered := hits[:0]
				for _, h := range hits {
					if h.License == "CC0" {
						filtered = append(filtered, h)
					}
				}
				hits = filtered
			}

			data, err := json.Marshal(hits)
			if err != nil {
				return err
			}
			if wantsHumanTable(cmd.OutOrStdout(), flags) {
				var items []map[string]any
				if json.Unmarshal(data, &items) == nil && len(items) > 0 {
					if err := printAutoTable(cmd.OutOrStdout(), items); err != nil {
						return err
					}
					if len(items) >= 25 {
						fmt.Fprintf(os.Stderr, "\nShowing %d results. To narrow: add --limit or filter flags.\n", len(items))
					}
					return nil
				}
			}
			return printOutputWithFlagsMeta(cmd.OutOrStdout(), data, flags, map[string]any{"source": "live"}, nil)
		},
	}
	cmd.Flags().StringVar(&query, "query", "", "search text (required)")
	cmd.Flags().StringVar(&assetType, "asset-type", "", "filter to MODEL, TEXTURE, or HDRI")
	cmd.Flags().StringVar(&providers, "providers", "", "comma-free provider filter: POLYHAVEN, SKETCHFAB, AMBIENTCG, or ALL (default)")
	cmd.Flags().IntVar(&limit, "limit", 10, "max results")
	cmd.Flags().BoolVar(&freeOnly, "free-only", true, "restrict to CC0/free assets")

	return cmd
}

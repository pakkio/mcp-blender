// Copyright 2026 pakkio and contributors. Licensed under Apache-2.0.
//
// Hand-patched (see .printing-press-patches/0002-vlm-and-asset-pipeline.md):
// the generated version posted to a synthetic /import_online_asset path
// with no bridge equivalent -- the real import_online_asset tool
// (mcp_server/src/mcp_blender/tools/asset_source_ops.py) downloads the asset
// file over HTTP inside the Python process, then hands the local path to the
// bridge's import_file. This version calls the Go port of that pipeline
// directly (internal/blenderassets).

package cli

import (
	"encoding/json"
	"strconv"
	"strings"

	"mcp-blender-pp-cli/internal/blenderassets"

	"github.com/spf13/cobra"
)

func newImportOnlineAssetPromotedCmd(flags *rootFlags) *cobra.Command {
	var assetID string
	var provider string
	var targetPolyBudget int
	var reductionMethod string
	var collectionPath string
	var location string
	var scaleToSize float64
	var forwardAxis string
	var upAxis string
	var autoOrient bool

	cmd := &cobra.Command{
		Use:   "import-online-asset",
		Short: "Import a previously-searched online asset into the Blender scene",
		Long: "Downloads the asset for (--provider, --asset-id), imports it into Blender via the bridge, and " +
			"optionally reduces it to --target-poly-budget vertices and files it into --collection-path. Import " +
			"results carry an orientation report from the bridge's own heuristic; when it says the model landed " +
			"on its side or upside down, retry with --up-axis (the file's real up axis, usually Y) or --auto-orient.",
		Example:     "  mcp-blender-pp-cli import-online-asset --asset-id modular_fort_01 --provider polyhaven",
		Annotations: map[string]string{"pp:endpoint": "import_online_asset.import"},
		RunE: func(cmd *cobra.Command, args []string) error {
			if assetID == "" && !flags.dryRun {
				return cmd.Help()
			}

			c, err := flags.newClient()
			if err != nil {
				return err
			}

			p := blenderassets.ImportParams{
				AssetID:          assetID,
				Provider:         provider,
				TargetPolyBudget: targetPolyBudget,
				ReductionMethod:  reductionMethod,
				CollectionPath:   collectionPath,
				ForwardAxis:      forwardAxis,
				UpAxis:           upAxis,
				AutoOrient:       autoOrient,
			}
			if scaleToSize > 0 {
				p.ScaleToSize = scaleToSize
				p.HasScale = true
			}
			if location != "" {
				coords := strings.Split(location, ",")
				if len(coords) == 3 {
					var parsed [3]float64
					ok := true
					for i, c := range coords {
						f, err := strconv.ParseFloat(strings.TrimSpace(c), 64)
						if err != nil {
							ok = false
							break
						}
						parsed[i] = f
					}
					if ok {
						p.Location = parsed
						p.HasLocation = true
					}
				}
			}

			result, err := blenderassets.ImportOnlineAsset(cmd.Context(), c, p)
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
	cmd.Flags().StringVar(&assetID, "asset-id", "", "asset id from search-online-assets (required)")
	cmd.Flags().StringVar(&provider, "provider", "sketchfab", "polyhaven | sketchfab | ambientcg")
	cmd.Flags().IntVar(&targetPolyBudget, "target-poly-budget", 0, "post-import vertex budget (0 = no reduction)")
	cmd.Flags().StringVar(&reductionMethod, "reduction-method", "simplify", "simplify (default, only method implemented in this CLI port)")
	cmd.Flags().StringVar(&collectionPath, "collection-path", "", "nested collection path to file the import into, e.g. 'Furniture/Chairs'")
	cmd.Flags().StringVar(&location, "location", "", "x,y,z placement, e.g. \"1.0,2.0,0.0\"")
	cmd.Flags().Float64Var(&scaleToSize, "scale-to-size", 0, "uniform-scale the import to this world size (largest dimension)")
	cmd.Flags().StringVar(&forwardAxis, "forward-axis", "", "source file's forward axis override")
	cmd.Flags().StringVar(&upAxis, "up-axis", "", "source file's up axis override (most common fix: Y)")
	cmd.Flags().BoolVar(&autoOrient, "auto-orient", false, "auto-correct suspect upside-down/lying-down orientation")

	return cmd
}

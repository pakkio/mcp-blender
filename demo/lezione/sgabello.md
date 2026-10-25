---
name: sgabello
description: "Crea uno sgabello con cuscino in Blender tramite l'MCP mcp-blender, in due modi: generato con Meshy (importa, semplifica, texturizza) oppure modellato a mano (cubo, inset, extrude, bevel, subdivision), con texture PBR ambientCG e export GLB compatibile con PBR di Second Life e OpenSim. Usare per richieste su sgabelli, sedie o mobili per mondi virtuali."
---

# Sgabello per mondi virtuali (Meshy o a mano)

Prerequisiti: MCP Bridge 2.3.6 o successivo (`get_bridge_status` risponde), `MESHY_API_KEY` per la via Meshy
(`get_env_info` la mostra mascherata), texture PBR in una cartella locale (qui `demo/lezione/Wood049`, `Fabric030`,
`Leather024`, `Metal032`, da ambientCG, 1K JPG).

**Regola di lavoro.** Prima di ogni passo spiega cosa farai e perché, poi esegui e mostra un render. Se l'utente
vuole la modalità lenta, chiedi conferma prima di ogni passo. Registra i passi in italiano in un `.md` della cartella.

## 0. Sempre

1. `blender_scene checkpoint_create` (nome `pre_sgabello`): permette di tornare indietro.
2. Se la scena ha il cubo di default e l'utente lo vuole fuori, cancellalo; in dubbio, nascondilo.
3. Crea la collezione `Sgabello_Manuale` o `Generated/Meshy` e rendila attiva.

## A. Via Meshy

1. `blender_assets action=ai_generate`, `params`: `provider: meshy`, `prompt` (inglese, es. "ornate wooden bar stool with
   padded leather cushion, carved legs and metal footrest"), `target_vertices: 5000`, `reduction_method: simplify`.
   Dura circa 2 minuti; il tool passa in background. Con `none` non c'è riduzione.
2. **`target_size` viene ignorato da `ai_generate`**: il modello esce enorme (1,9 m invece di 0,75). Ridimensiona a mano
   con Python: scala, `transform_apply` della scala, base a Z = 0, centro in X/Y.
3. La risposta contiene un'anteprima base64 da circa 2 MB: viene salvata su file, non è un errore. Leggi solo le chiavi
   utili (`vertices_count`, `tri_count_before`, `decimation_applied`).
4. Le UV di Meshy sono un atlante, inutili per texture ripetibili. Per texturizzare con PBR separate:
   - separa il cuscino dal legno per altezza (es. facce con Z > 0,665 m);
   - due slot materiale e `cube_project` con `cube_size=0.5`, `scale_to_bounds=False`.
5. `screenshot` della viewport mostra solo la finestra dell'utente (spesso minuscola): per vedere il risultato usa
   `render_image` (EEVEE, 800 x 800) e leggi il PNG.

## B. A mano (valori usati, unità metri)

| Passo | Operazione | Valori |
|---|---|---|
| 1 | Cubo `Seduta`, scala applicata | 0,40 x 0,40 x 0,05, Z = 0,70 |
| 2 | Subdivide su tutti gli spigoli | 2 tagli: 56 vertici, faccia inferiore 3 x 3 |
| 3 | Inset individuale sui 4 angoli sotto, poi Extrude | inset 0,04; extrude 0,675 in giù |
| 3b | Gambe diagonali: sposta ogni piede verso l'esterno | 0,07 su X e Y (circa 6 gradi) |
| 4 | Modificatore Bevel | 0,008, 2 segmenti, limite angolo 30 gradi |
| 5 | Cubo `Cuscino` quadrato, scala applicata | 0,38 x 0,38 x 0,06, Z = 0,755 |
| 5b | Inset e Extrude della faccia superiore | 0,03 e 0,02 (cima a 0,805) |
| 6 | Bevel e Subdivision Surface, Shade Smooth | 0,012, 2 segmenti, livelli 2 |

Con script: usa `bmesh` (`subdivide_edges` con `use_grid_fill=True`, `inset_individual`, `extrude_discrete_faces`).
Per mostrare i tagli in un render serve un modificatore **Wireframe temporaneo**: la modalità wireframe del render esce vuota.

## C. UV e materiali (stessi per A e B)

1. UV: `cube_project`, cubo 0,5 m, senza scalare ai bordi.
2. **Venatura verticale sulle gambe**: scambia U e V sulle facce laterali sotto la tavola (Z < 0,67). La tavola resta orizzontale.
3. Materiali: l'add-on ha `auto_load_pbr_texture_set(folder_path, material_name)`; se non è esposto come tool MCP, chiamalo
   da `execute_blender_python` con `AutoLoadPBRTextureSetTool().execute(...)` (modulo `...tools.advanced_material_slot_ops`).
   Carica Color, Roughness e **NormalGL** (preferita alla DX, 2.3.6 e successive; Displacement ignorata).
4. Per Second Life / OpenSim: rimuovi i nodi `Texture Coordinate` e `Mapping` (creerebbero `KHR_texture_transform`),
   attiva il **backface culling** (`doubleSided` falso), un solo set UV, 2 o 3 materiali al massimo.
5. Texture a **512 px**: `image.scale(512, 512)` e `image.pack()` per ognuna delle 6 immagini. Il GLB passa da 9,4 a 0,95 MB.
   Il ridimensionamento sta solo in memoria: senza `pack()` e senza salvare, si perde alla riapertura.

## D. Export e verifica

1. Seleziona solo gli oggetti dello sgabello (nascondere un oggetto non basta con `selected_only` falso).
2. `ExportSceneTool` / `export_scene`: `file_format: GLB`, `selected_only: true`, `apply_modifiers: true`,
   `export_animations: false`, `draco_compression: false`.
3. Rileggi il GLB: JSON chunk dopo l'header di 20 byte. Controlla `extensionsUsed` (assente), una `normalTexture` per
   materiale, `metallicRoughnessTexture`, un solo `TEXCOORD_0`, numero di triangoli, peso.
4. Per salvare la scena: pack delle immagini poi `wm.save_as_mainfile(copy=True, compress=True)`.

## Cose da non dimenticare

- `studio_lighting` crea un secondo set di luci a ogni chiamata: cancella quello vecchio.
- `blender_material pbr_setup` richiede `material_name`.
- Non ho mai provato il GLB in Second Life o in OpenSim: dichiaralo nel riepilogo finale.
- Budget indicativo: Meshy 5.000 vertici; a mano 104 vertici (3.552 nel file con modificatori).
- Riferimenti: `PROCEDURA_SGABELLO_MESHY.md`, `PROCEDURA_MANUALE_GUI.md`, `REGISTRO_ESECUZIONE.md`,
  `REGISTRO_MANUALE.md`.

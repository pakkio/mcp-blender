# Sgabello complesso da Meshy: importa, semplifica, texturizza, salva GLB

Procedura con l'MCP Blender di questo repository. Le texture sono già in questa cartella
(`Wood049`, `Fabric030`, `Leather024`, `Metal032`).

## 0. Preparazione (una volta sola)

1. Aggiorna il repo: `git pull` nella root `mcp-blender`. A oggi `main` è allineato con `origin/main`
   (versione 2.3.5), quindi non c'è niente da scaricare. Se il pull porta novità, riavvia il server MCP
   e ricarica l'add-on in Blender (Edit → Preferences → Add-ons, disattiva e riattiva).
2. Chiave Meshy: variabile d'ambiente `MESHY_API_KEY` oppure il tool `set_api_keys`. Senza chiave
   `ai_generate` con `provider=meshy` fallisce.
3. Abilita **Node Wrangler** (Edit → Preferences → Add-ons) se vuoi collegare le texture a mano.
4. Verifica la connessione: `get_bridge_status`. Deve risultare connesso a Blender.
5. Cartella di lavoro: crea una scena vuota e salva un checkpoint
   (`blender_scene`, action `checkpoint_create`).

## 1. Genera e importa da Meshy (con semplificazione integrata)

`blender_assets`, action `ai_generate`:

```json
{
  "action": "ai_generate",
  "params": {
    "provider": "meshy",
    "prompt": "ornate wooden bar stool with padded leather cushion, carved legs and metal footrest",
    "target_vertices": 5000,
    "reduction_method": "simplify",
    "target_size": 0.75,
    "collection_path": "Generated/Meshy"
  }
}
```

- Da immagine: sostituisci `prompt` con `"image_path": "C:\\percorso\\sgabello.png"`.
- `target_vertices` è il budget di vertici per mesh. 5000 va bene per OpenSim e Second Life; usa 2000 per un
  oggetto molto leggero, 10000 per un oggetto di pregio.
- `reduction_method`: `simplify` (consigliato, usa `simplify_geometry`), `remesh` (rifà la topologia, può
  smussare gli spigoli) oppure `none` (nessuna riduzione).
- Meshy da testo esegue una fase di refine e produce un modello già texturizzato. Aspetta il completamento:
  può richiedere minuti.
- In alternativa, dal pannello: tasto `N` → scheda MCP Bridge → AI Generate.

Controlla il risultato: `blender_scene` (ispezione) e verifica che i vertici siano sotto il budget.

## 2. Semplifica ancora se serve

Se dopo l'import hai ancora troppi vertici, oppure hai usato `reduction_method: none`:

```json
simplify_geometry { "object_name": "<nome>", "target": 5000, "target_unit": "VERTICES" }
```

Se la riduzione deforma la forma, il tool fa rollback e suggerisce un nuovo `suggested_retry_target`: riprova con
quel valore. Per sgabelli con gambe sottili non scendere troppo.

Per un oggetto fatto di molte parti (seduta, gambe, pedana): `separate_logical_areas`, poi
`confirm_separated_parts`, così puoi dare un materiale diverso a ogni parte.

## 3. Texturizza con le texture di questa cartella

Il materiale di Meshy ha una sola texture dipinta. Per sostituirla con materiali PBR separati:

1. Per ogni parte crea un materiale dalla cartella giusta, con `auto_load_pbr_texture_set`:

   | Parte | folder_path | material_name |
   |---|---|---|
   | Seduta (cuscino) | `...\demo\lezione\Leather024` oppure `Fabric030` | `M_Cuscino` |
   | Gambe e struttura | `...\demo\lezione\Wood049` | `M_Legno` |
   | Poggiapiedi o rinforzi | `...\demo\lezione\Metal032` | `M_Metallo` |

   Usa il percorso assoluto, per esempio
   `C:\Users\claudio.pacchiega\w\mcp-blender\demo\lezione\Wood049`.
2. Assegna il materiale alla parte con `blender_material`, action `assign` (oppure `manage_material_slots`
   per assegnarlo a gruppi di facce).
3. **UV**: se la parte non ha UV valide, lancia `uv_unwrap` (`blender_mesh`) prima di assegnare. Senza UV le
   texture risultano stirate.
4. **Normal map**: i file `_NormalGL.jpg` sono quelli giusti per Blender. Se l'add-on collega per sbaglio la
   `_NormalDX.jpg`, i rilievi appaiono invertiti: togli quel file dalla cartella o ricollega la GL a mano
   (Node Wrangler: `Ctrl+Shift+T` sul Principled BSDF e scegli le mappe a mano).
5. **Verifica**: `evaluate_scene_visually`, oppure uno screenshot dal viewport con `blender_camera_lighting`.

Regola per OpenSim e Second Life: pochi materiali (uno per parte, al massimo 3 o 4 in totale), solo Color,
Normal e Roughness. Non servono Displacement, AO e NormalDX.

## 4. Pulizia prima dell'export

- Applica trasformazioni e modificatori; `export_apply` lo fa già a livello di export.
- Posiziona l'origine alla base dell'oggetto, a Z=0 (`target_size` all'import già appoggia il modello a terra).
- Elimina camera, luci e oggetti di servizio: l'export salva solo l'oggetto se usi `selected_only`.

## 5. Salva il GLB

`export_scene`:

```json
{
  "filepath": "C:\\Users\\claudio.pacchiega\\w\\mcp-blender\\demo\\lezione\\sgabello.glb",
  "file_format": "GLB",
  "selected_only": true,
  "apply_modifiers": true,
  "export_animations": false,
  "export_materials": true,
  "draco_compression": false
}
```

Prima dell'export seleziona lo sgabello. Lascia `draco_compression` a `false` se il GLB deve andare in
OpenSim, Second Life o in un viewer che non supporta Draco.

Controllo finale: reimporta `sgabello.glb` in una scena vuota (`import_file`) e verifica vertici, scala e
materiali.

## 6. Problemi frequenti

| Sintomo | Causa e rimedio |
|---|---|
| `ai_generate` fallisce subito | Manca `MESHY_API_KEY`. |
| Timeout durante la generazione | Meshy è lento; l'add-on ha una ripresa del timeout (v2.3.5), rilancia lo stesso prompt. |
| Modello troppo grande o piccolo | Imposta `target_size` (metri). |
| Modello ruotato di 90° | Passa `forward_axis` e `up_axis`, oppure `auto_orient: true`. |
| Texture non collegate | I nomi dei file non sono riconosciuti: vedi sotto. |
| Rilievi invertiti | Hai collegato NormalDX invece di NormalGL. |
| In-world solo una parte ha le texture | Troppi materiali: unisci le parti con lo stesso materiale. |

## Versione dell'add-on

Questa procedura vale per **MCP Bridge 2.3.6** (`dist/mcp_bridge-2.3.6.zip`). La 2.3.6 corregge
`auto_load_pbr_texture_set`: riconosce i nomi di Poly Haven (`_diff_`, `_nor_gl_`) e, se in una cartella ci sono
sia NormalGL sia NormalDX, usa sempre la GL.

Per aggiornare: Edit → Preferences → Get Extensions → Install from Disk → `mcp_bridge-2.3.6.zip`, poi riavvia
Blender e il server MCP.

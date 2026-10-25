# Registro di esecuzione: sgabello da Meshy

Data: 2026-10-25. Add-on: MCP Bridge 2.3.6. Blender 5.2 LTS.

## Passo 0 - Verifiche iniziali

- `get_bridge_status`: bridge connesso, nessun lavoro in coda.
- `get_env_info`: `MESHY_API_KEY` presente (letta da `.env`).
- Controllo della versione in Blender: `bl_ext.user_default.mcp_bridge` = 2.3.6.
- Prova della correzione PBR su `Wood049`: caricati Color, Roughness e **NormalGL**; NormalDX scartata.
  Materiale di prova cancellato.
- Scena di partenza: 3 oggetti.

## Passo 1 - Checkpoint e generazione con Meshy

- `blender_scene checkpoint_create` -> `pre_sgabello` salvato (ripristinabile).
- `blender_assets ai_generate`:
  - provider `meshy`, testo: "ornate wooden bar stool with padded leather cushion, carved legs and metal footrest, highly detailed"
  - `target_vertices` 5000, `reduction_method` simplify, `target_size` 0.75 m, collezione `Generated/Meshy`
- Avvio: la chiamata passa in background. Dopo 90 s lo stato è "Downloading ... from meshy".
- Esito: generazione completata. Importato `Mesh_0` (padre vuoto `Meshy`), 10.382 triangoli prima della riduzione,
  **4.999 vertici** dopo `simplify_geometry`. Licenza Meshy "User Generated".
- Nota: `target_size` non è stato applicato dalla action `ai_generate` (il modello era 1,03 x 1,03 x 1,90 m).
  Va ridimensionato a mano (passo 2).
- Nota: la risposta del tool contiene un'anteprima base64 da quasi 2 MB; Claude Code la salva su file e
  non la mostra. Non è un errore.

## Passo 2 - Pulizia della scena e dimensioni

- Il cubo di default nascondeva lo sgabello: su richiesta è stato **cancellato** (resta il checkpoint `pre_sgabello`).
- Ridimensionato lo sgabello ad altezza **0,75 m** (fattore di scala applicato con `transform_apply`),
  base appoggiata a Z=0 e centrato in X/Y. Dimensioni finali: 0,407 x 0,407 x 0,75 m.
- Render di controllo con la texture originale di Meshy: `render_01_meshy.png` (legno scuro, cuscino bordeaux).

## Passo 3 - Texture PBR

- Il tool `auto_load_pbr_texture_set` non è esposto come tool MCP in questa sessione: l'ho eseguito
  direttamente dall'add-on 2.3.6 tramite `execute_blender_python`. Stessa funzione, stesso risultato.
- Creati due materiali: `M_Cuscino` (cartella `Leather024`) e `M_Legno` (cartella `Wood049`).
  Per entrambi sono state caricate 3 mappe: Color, Roughness e **NormalGL** (la DX è stata ignorata, come da correzione 2.3.6).
- Assegnazione per altezza: facce con Z > 0,665 m (1.432) -> cuscino; le altre (7.659) -> legno.
  La soglia è stata scelta guardando il colore dell'albedo originale di Meshy (il cuscino sta tra 0,67 e 0,75 m).
- UV: le UV di Meshy sono un atlante e non vanno bene per texture ripetibili. Ho rifatto le UV con
  `cube_project` (cubo da 0,5 m, senza scalare ai bordi), così la scala delle texture è reale.
- Luci: `studio_lighting` (tre punti). Render: `render_02_texturizzato.png` (legno chiaro, cuscino in pelle rossa).
- Non ho usato `Fabric030` e `Metal032`: lo sgabello ha solo due materiali, in linea con il consiglio per OpenSim.

## Passo 4 - Export GLB

- `export_scene` (dall'add-on): `sgabello.glb`, solo l'oggetto selezionato, modificatori applicati, senza animazioni, senza Draco.
- Dimensione: 7.771.592 byte (7,4 MB).
- Verifica leggendo il GLB: 1 mesh, 2 primitive (`M_Legno` 8.416 triangoli, `M_Cuscino` 1.592 triangoli),
  6 immagini (colore, roughness/metallic e normal per ciascun materiale), `normalTexture` presente in entrambi.
  I vertici nel file sono circa 14.400 contro i 4.999 in Blender: è normale, i vertici si sdoppiano sulle cuciture UV.

## Cosa non ho verificato

- Non ho reimportato il GLB in una scena vuota né l'ho caricato in OpenSim/Second Life.
- Le texture sono 1K (1024 x 1024), ma il GLB pesa 7,4 MB: per un caricamento in-world valuta di
  comprimere le immagini o di scendere a 512 px.

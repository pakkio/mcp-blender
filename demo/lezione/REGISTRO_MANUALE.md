# Sgabello grezzo a mano, passo per passo

Modellazione manuale in stile lezione di Eva, con conferma prima di ogni passo.

## Passo 1 - Preparazione (fatto)

- Nascosti `Mesh_0` e `Meshy` (lo sgabello di Meshy), non cancellati.
- Creata la collezione `Sgabello_Manuale` e resa attiva: ogni nuovo oggetto nasce lì.
- Cursore 3D azzerato in (0, 0, 0).

## Passo 2 - Seduta (fatto)

- Aggiunto un cubo e rinominato `Seduta`: 0,40 x 0,40 x 0,05 m, centro a Z = 0,70 m, scala applicata.
- 8 vertici, nella collezione `Sgabello_Manuale`.
- Render: `manuale_02_seduta.png` (la tavola è sospesa, le gambe arrivano dopo).

## Passo 3 - Tagli di divisione (fatto)

- Suddivisi tutti gli spigoli della `Seduta` con 2 tagli: da 8 a **56 vertici**, 54 facce.
- La faccia inferiore ora è una griglia 3 x 3 (9 facce); anche le facce laterali hanno tagli, per non creare poligoni irregolari.
- Render: `manuale_03_tagli.png`, con un modificatore Wireframe temporaneo (rimosso subito dopo) per far vedere i tagli.
- Camera spostata sotto la seduta per mostrare la faccia inferiore.
- Nota: il primo tentativo di render in modalità wireframe usciva vuoto; il modificatore temporaneo ha risolto.

## Passo 4 - Gambe diagonali (fatto)

- Su richiesta: inset sul lato inferiore e gambe leggermente diagonali (divaricate verso l'esterno).
- Inset di 0,04 m sui 4 quadrati d'angolo della faccia inferiore (sezione gamba circa 5 x 5 cm).
- Estrusione di 0,675 m verso il basso, con ogni piede spostato di 7 cm verso l'esterno su X e Y (circa 6 gradi).
- Risultato: 88 vertici, piedi a Z = 0. Nel render ne sono visibili tre; la quarta è dietro.
- Render: `manuale_04_gambe.png` (Workbench, solido).

## Passo 5 - Bevel (fatto)

- Su richiesta: smusso più marcato. Modificatore `Bevel` sulla `Seduta`: larghezza 8 mm, 2 segmenti,
  limite d'angolo 30 gradi (smussa solo gli spigoli netti, non i tagli piatti della griglia).
- Vertici: 88 nella mesh, **376** dopo il modificatore (il modificatore non è applicato, si può ancora cambiare).
- Render: `manuale_05_bevel.png` (EEVEE, ancora senza materiali).

## Passo 6 - Cuscino: cilindro, inset ed estrusione (fatto)

- Cilindro a 24 lati, raggio 0,19 m, altezza 0,06 m, centro a Z = 0,755 m: appoggiato sulla seduta (che arriva a 0,725 m).
- Inset di 0,03 m e estrusione di 0,02 m della faccia superiore: cima rialzata a forma di cappello. Nome `Cuscino`.
- 96 vertici, punto più alto Z = 0,805 m. Nella collezione `Sgabello_Manuale`.
- Render: `manuale_06_cuscino.png`. Il cuscino è ancora spigoloso, con un gradino visibile: lo ammorbidisce il passo 7.

### Passo 6 (rifatto) - Cuscino quadrato

- Su richiesta il cilindro è stato cancellato e sostituito da un cuscino quadrato.
- Cubo 0,38 x 0,38 x 0,06 m, centro a Z = 0,755 m, scala applicata. Inset 0,03 m ed estrusione 0,02 m della faccia superiore.
- Solo **16 vertici** (il cilindro ne aveva 96). Punto più alto Z = 0,805 m. Nome `Cuscino`.
- Render: `manuale_06_cuscino_quadrato.png`. Il bordo è ancora a spigoli vivi e con un gradino: lo ammorbidisce il passo 7.

## Passo 7 - Cuscino morbido (fatto)

- Modificatori sul `Cuscino`, in quest'ordine: `Bevel` (12 mm, 2 segmenti, limite 30 gradi) e `Subdivision` (livello 2 in vista e in render).
- Ombreggiatura liscia attivata su tutte le facce.
- Vertici: 16 nella mesh, **1.762** con i modificatori. Altezza invariata, 0,805 m.
- Render: `manuale_07_cuscino_morbido.png`. Il gradino è diventato una curva morbida; il bordo resta ben definito.

## Passo 8 - UV e materiali PBR (fatto)

- `Cube Projection` (cubo da 0,5 m, senza scalare ai bordi) su `Seduta` e `Cuscino`: UV in scala reale.
- Materiali creati con l'add-on 2.3.6 (stessa funzione di Node Wrangler `Ctrl+Shift+T`):
  - `M_Legno_Manuale` da `Wood049` sulla `Seduta` (gambe incluse)
  - `M_Cuscino_Manuale` da `Fabric030` sul `Cuscino` (tessuto grigio)
  - Per entrambi caricate 3 mappe: Color, Roughness, NormalGL. NormalDX ignorata.
- `studio_lighting` ha creato un secondo set di luci; ho cancellato il set vecchio (`Key_Light`, `Fill_Light`, `Rim_Light`,
  puntato sullo sgabello Meshy) e tenuto quello nuovo (`.001`).
- Render: `manuale_08_materiali.png`. Le gambe sono 4, ma una è nascosta dietro quella centrale.

## Passo 8b - Venatura verticale e compatibilità PBR Second Life (fatto)

Su richiesta: legno con linee verticali sulle gambe e shading compatibile con il PBR di Second Life.

- **Venatura:** ruotate di 90 gradi le UV delle 16 facce laterali delle gambe (quelle sotto la tavola, Z < 0,67 m). La tavola
  della seduta mantiene la venatura orizzontale. Render: `manuale_08b_venatura_verticale.png`.
- **Nodi del materiale:** rimossi `Texture Coordinate` e `Mapping` da entrambi i materiali. Restano solo Principled BSDF,
  Normal Map, Output e 3 immagini: così l'export non genera estensioni glTF.
- **Backface culling attivo** sui due materiali: nel GLB `doubleSided` passa a falso (le mesh sono chiuse).
- **Verifica su un GLB di prova** (cartella temporanea, non in `demo`):
  - `extensionsUsed` assente: nessuna estensione glTF, quindi niente `KHR_texture_transform`.
  - Per ogni materiale: baseColor, metallicRoughness (roughness nel canale verde, metallic 0) e normalTexture.
  - Immagini 1024 x 1024 (limite SL 2048), normal map in formato GL, un solo set UV (`TEXCOORD_0`).
  - 2 mesh, 3.553 vertici e 4.268 triangoli dopo i modificatori; 9,4 MB.
- **Non verificato:** non l'ho caricato in Second Life né in OpenSim. Il controllo è solo sulla struttura del file.
- Occlusion map assente (non serve a SL). Per il peso del file valuta di scendere a 512 px.

## Passo 8c - Texture ridotte a 512 px (fatto)

- Le 6 immagini dei due materiali (Color, Roughness, NormalGL di `Wood049` e `Fabric030`) sono state ridimensionate da
  1024 a **512 x 512** dentro Blender. I file originali nelle cartelle `Wood049` e `Fabric030` non sono stati toccati.
- GLB di prova (cartella temporanea): da 9,4 MB a **0,95 MB** (953.764 byte).
- Render: `manuale_08c_texture_512.png`. A questa distanza la differenza con il 1K non si nota.
- Il ridimensionamento vale solo per la scena aperta: se riapri il .blend senza salvarlo, le immagini tornano a 1K.

## Passo 9 - Export GLB (fatto)

- `export_scene` dall'add-on: `sgabello_manuale.glb`, solo `Seduta` e `Cuscino`, modificatori applicati,
  senza animazioni, senza Draco, materiali inclusi.
- Controllo del file riletto: vedi il riepilogo in chat (vertici, triangoli, materiali, peso).
- Non provato in Second Life né in OpenSim.

## Passo 10 - Salvataggio della scena (fatto)

- Le 6 immagini a 512 px sono state impacchettate nel file, così la riduzione non si perde alla riapertura.
- Salvato `sgabello_manuale.blend` (circa 3 MB, compresso) come **copia**: la sessione di Blender in corso non cambia nome.
- Il file contiene anche lo sgabello Meshy (nascosto), le luci e la camera.

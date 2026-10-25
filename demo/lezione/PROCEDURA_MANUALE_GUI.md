# Sgabello a mano in Blender: passi con mouse e tastiera

Riproduce `sgabello_manuale.glb`. I valori sono quelli usati davvero. Unità: metri.
I passaggi sono scritti per Blender 4.2 o successivo (testato con 5.2 LTS solo via script: le scorciatoie qui sotto
non le ho eseguite io a mano, quindi se un menu ha un nome diverso nella tua versione, dimmelo).

Prerequisito: Edit > Preferences > Add-ons > attiva **Node Wrangler**. Texture in `Wood049` e `Fabric030`.

## 0. Scena pulita

1. File > New > General.
2. Seleziona il cubo, `X`, Delete. Lascia camera e luce.
3. Nell'Outliner: clic destro su Scene Collection > New Collection, rinomina in `Sgabello_Manuale` (`F2`).
   Clicca sulla collezione per renderla attiva.

## 1. Seduta (tavola di legno)

1. `Shift+A` > Mesh > Cube.
2. Tasto `N` > scheda Item. Dimensions: X 0.4, Y 0.4, Z 0.05. Location: Z 0.70.
3. `Ctrl+A` > Scale (applica la scala: serve a inset e UV).
4. `F2`, nome `Seduta`.

## 2. Tagli per le gambe

1. `Tab` (Edit Mode), `A` (seleziona tutto).
2. Clic destro > Subdivide. Nel pannello in basso a sinistra imposta **Number of Cuts = 2**.
   Risultato: 56 vertici, e la faccia inferiore è una griglia 3 x 3.

## 3. Gambe con Inset ed Extrude

1. Premi `3` (modalità facce). `Ctrl+Numpad7` per guardare da sotto. `Alt+Z` per vedere in trasparenza.
2. Clic sul quadrato d'angolo, poi `Shift`+clic sugli altri tre: **solo i 4 angoli** della faccia inferiore.
3. Premi `I` (Inset), poi di nuovo `I` per attivare **Individual**, scrivi `0.04`, `Enter`.
4. Premi `E` (Extrude), scrivi `0.675`, `Enter`. Le gambe scendono fino a Z = 0.
   Se vanno verso l'alto, scrivi `-0.675`.
5. Gambe in diagonale: con `Ctrl+Numpad7` guarda da sotto. Seleziona **una** faccia in fondo a una gamba e premi
   `G` `X` `0.07` `Enter`, poi `G` `Y` `0.07` `Enter`. Il segno va verso l'esterno: per le gambe con X negativo usa `-0.07`,
   con Y negativo `-0.07`. Ripeti per le 4 gambe.
   Ogni gamba si apre di circa 6 gradi.

## 4. Smusso del legno

1. `Tab` per uscire da Edit Mode.
2. Properties > Modifiers (chiave inglese) > Add Modifier > Generate > **Bevel**.
3. Width 0.008 m, Segments 2, Limit Method **Angle**, Angle 30 gradi.

## 5. Cuscino quadrato

1. `Shift+A` > Mesh > Cube. `N`: Dimensions X 0.38, Y 0.38, Z 0.06. Location Z 0.755.
2. `Ctrl+A` > Scale. `F2`, nome `Cuscino`.
3. `Tab`, modalità facce (`3`), clic sulla faccia superiore.
4. `I`, `0.03`, `Enter` (senza Individual, è una sola faccia).
5. `E`, `0.02`, `Enter`. La cima si alza a 0,805 m. `Tab`.

## 6. Cuscino morbido

1. Modifiers > Add > Generate > **Bevel**: Width 0.012, Segments 2, Limit Method Angle, 30 gradi.
2. Add > Generate > **Subdivision Surface**: Levels Viewport 2, Render 2. Il Bevel deve stare sopra.
3. Menu Object > **Shade Smooth**.

## 7. UV

1. Seleziona `Seduta`, `Tab`, `A`. Premi `U` > **Cube Projection**.
2. Nel pannello in basso a sinistra: **Cube Size 0.5**, togli la spunta a **Scale to Bounds**.
3. `Tab`. Ripeti per `Cuscino`.
4. Venatura verticale sulle gambe:
   - Seleziona `Seduta`, `Tab`, modalità facce, `Alt+Z`.
   - `Numpad1` (vista frontale). Con il box select, `B` o trascina, seleziona **tutto quello che sta sotto la tavola**
     (da Z = 0 a poco sotto 0,675 m). Non toccare la tavola.
   - Apri un'area UV Editor (workspace UV Editing), attiva **UV Sync Selection** (due frecce in alto a sinistra).
   - Nell'UV Editor premi `R`, scrivi `90`, `Enter`.

## 8. Materiali PBR

1. Workspace **Shading**. Seleziona `Seduta`, nel Shader Editor premi **New** per un materiale. Nome `M_Legno_Manuale`.
2. Seleziona il nodo Principled BSDF e premi **`Ctrl+Shift+T`**. Nella finestra scegli la cartella `Wood049` e seleziona
   **solo** `..._Color.jpg`, `..._Roughness.jpg` e `..._NormalGL.jpg`. **Non** NormalDX e non Displacement. Clic su Principled Setup.
3. Node Wrangler aggiunge anche `Texture Coordinate` e `Mapping`: selezionali con `Shift`+clic e premi `X`.
   Vanno tolti perché nel GLB creerebbero `KHR_texture_transform`, che Second Life non gestisce.
4. Material Properties > Settings > spunta **Backface Culling**.
5. Ripeti per `Cuscino` con la cartella `Fabric030` e nome `M_Cuscino_Manuale`.

## 9. Texture a 512 px

Per **ognuna** delle 6 immagini:
1. Workspace Texture Paint o Image Editor, scegli l'immagine dal menu a tendina.
2. Image > **Resize** (`Alt+R`): 512 x 512 > OK.
3. Image > **Pack** (altrimenti la riduzione si perde alla riapertura).
La roughness e la normal restano Non-Color (Node Wrangler lo imposta da solo).

## 10. Export GLB

1. Seleziona `Seduta` e `Cuscino` (clic e `Ctrl`+clic nell'Outliner).
2. File > Export > **glTF 2.0 (.glb/.gltf)**.
3. Format: **glTF Binary (.glb)**. Include: spunta **Limit to > Selected Objects**.
4. Data > Mesh: spunta **Apply Modifiers**. Data > Compression: **spento**.
5. Animation: spegni **Animation**.
6. Nome `sgabello_manuale.glb`, Export.

## Controlli finali

- Peso del GLB circa 0,95 MB, 4.268 triangoli e 3.552 vertici circa nel file (da 104 vertici in Blender).
- Reimporta il GLB in una scena vuota: 2 mesh e 2 materiali, texture visibili in Material Preview.
- Ricorda: non l'ho provato in Second Life né in OpenSim.

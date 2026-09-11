"""Offline vocabulary and Blender language choices for structural naming."""

LANG_DISPLAY_NAMES = {'it': 'Italian', 'en': 'English', 'hu': 'Hungarian',
                      'fr': 'French', 'de': 'German', 'es': 'Spanish'}
LANGUAGE_ITEMS = (
    ('it', 'Italian (Italiano)', 'Translate names into Italian'),
    ('en', 'English', 'Clean up names in English'),
    ('hu', 'Hungarian (Magyar)', 'Translate names into Hungarian'),
    ('fr', 'French (Français)', 'Translate names into French'),
    ('de', 'German (Deutsch)', 'Translate names into German'),
    ('es', 'Spanish (Español)', 'Translate names into Spanish'),
)

# English source | Hungarian | French | German | Spanish.
# Keep accented characters: Blender object names support Unicode.
_WORDS = '''
furniture|Bútorok|Mobilier|Möbel|Mobiliario
characters|Karakterek|Personnages|Figuren|Personajes
props|Kellékek|Accessoires|Requisiten|Accesorios
architecture|Építészet|Architecture|Architektur|Arquitectura
vehicles|Járművek|Véhicules|Fahrzeuge|Vehículos
environment|Környezet|Environnement|Umgebung|Entorno
lights|Fények|Lumières|Lichter|Luces
cameras|Kamerák|Caméras|Kameras|Cámaras
imports|Importálások|Importations|Importe|Importaciones
generated|Generált|Générés|Generiert|Generados
scene|Jelenet|Scène|Szene|Escena
collection|Gyűjtemény|Collection|Sammlung|Colección
master|Fő|Principal|Haupt|Principal
assets|Erőforrások|Ressources|Ressourcen|Recursos
materials|Anyagok|Matériaux|Materialien|Materiales
textures|Textúrák|Textures|Texturen|Texturas
chair|Szék|Chaise|Stuhl|Silla
chairs|Székek|Chaises|Stühle|Sillas
armchair|Fotel|Fauteuil|Sessel|Sillón
armchairs|Fotelek|Fauteuils|Sessel|Sillones
stool|Zsámoly|Tabouret|Hocker|Taburete
sofa|Kanapé|Canapé|Sofa|Sofá
table|Asztal|Table|Tisch|Mesa
tables|Asztalok|Tables|Tische|Mesas
desk|Íróasztal|Bureau|Schreibtisch|Escritorio
shelf|Polc|Étagère|Regal|Estante
cabinet|Szekrény|Meuble|Schrank|Mueble
closet|Ruhásszekrény|Armoire|Kleiderschrank|Armario
bed|Ágy|Lit|Bett|Cama
lamp|Lámpa|Lampe|Lampe|Lámpara
lamps|Lámpák|Lampes|Lampen|Lámparas
light|Fény|Lumière|Licht|Luz
bulb|Izzó|Ampoule|Glühbirne|Bombilla
spotlight|Reflektor|Projecteur|Strahler|Foco
camera|Kamera|Caméra|Kamera|Cámara
car|Autó|Voiture|Auto|Coche
cars|Autók|Voitures|Autos|Coches
vehicle|Jármű|Véhicule|Fahrzeug|Vehículo
truck|Teherautó|Camion|Lastwagen|Camión
boat|Hajó|Bateau|Boot|Barco
tree|Fa|Arbre|Baum|Árbol
trees|Fák|Arbres|Bäume|Árboles
plant|Növény|Plante|Pflanze|Planta
plants|Növények|Plantes|Pflanzen|Plantas
flower|Virág|Fleur|Blume|Flor
grass|Fű|Herbe|Gras|Hierba
bush|Bokor|Buisson|Busch|Arbusto
rock|Szikla|Rocher|Felsen|Roca
rocks|Sziklák|Rochers|Felsen|Rocas
box|Doboz|Boîte|Kasten|Caja
boxes|Dobozok|Boîtes|Kästen|Cajas
crate|Láda|Caisse|Kiste|Cajón
barrel|Hordó|Tonneau|Fass|Barril
bottle|Palack|Bouteille|Flasche|Botella
cup|Csésze|Tasse|Tasse|Taza
plate|Tányér|Assiette|Teller|Plato
door|Ajtó|Porte|Tür|Puerta
doors|Ajtók|Portes|Türen|Puertas
window|Ablak|Fenêtre|Fenster|Ventana
windows|Ablakok|Fenêtres|Fenster|Ventanas
wall|Fal|Mur|Wand|Pared
walls|Falak|Murs|Wände|Paredes
floor|Padló|Sol|Boden|Suelo
roof|Tető|Toit|Dach|Tejado
ceiling|Mennyezet|Plafond|Decke|Techo
pillar|Pillér|Pilier|Pfeiler|Pilar
column|Oszlop|Colonne|Säule|Columna
stairs|Lépcső|Escalier|Treppe|Escaleras
sword|Kard|Épée|Schwert|Espada
shield|Pajzs|Bouclier|Schild|Escudo
gun|Pisztoly|Pistolet|Pistole|Pistola
wheel|Kerék|Roue|Rad|Rueda
wheels|Kerekek|Roues|Räder|Ruedas
tire|Gumiabroncs|Pneu|Reifen|Neumático
tires|Gumiabroncsok|Pneus|Reifen|Neumáticos
rim|Felni|Jante|Felge|Llanta
rims|Felnik|Jantes|Felgen|Llantas
hood|Motorháztető|Capot|Motorhaube|Capó
trunk_car|Csomagtartó|Coffre|Kofferraum|Maletero
windshield|Szélvédő|Pare-brise|Windschutzscheibe|Parabrisas
bumper|Lökhárító|Pare-chocs|Stoßstange|Parachoques
exhaust|Kipufogó|Échappement|Auspuff|Escape
mirror|Tükör|Rétroviseur|Spiegel|Retrovisor
seat|Ülés|Siège|Sitz|Asiento
seats|Ülések|Sièges|Sitze|Asientos
backrest|Háttámla|Dossier|Rückenlehne|Respaldo
arm|Kar|Bras|Arm|Brazo
armrest|Kartámasz|Accoudoir|Armlehne|Reposabrazos
armrests|Kartámaszok|Accoudoirs|Armlehnen|Reposabrazos
leg|Láb|Pied|Bein|Pata
legs|Lábak|Pieds|Beine|Patas
base|Alap|Base|Basis|Base
frame|Keret|Cadre|Rahmen|Marco
handle|Fogantyú|Poignée|Griff|Tirador
handles|Fogantyúk|Poignées|Griffe|Tiradores
cover|Burkolat|Couvercle|Abdeckung|Cubierta
cushion|Párna|Coussin|Kissen|Cojín
cushions|Párnák|Coussins|Kissen|Cojines
screw|Csavar|Vis|Schraube|Tornillo
screws|Csavarok|Vis|Schrauben|Tornillos
bolt|Csavar|Boulon|Bolzen|Perno
bolts|Csavarok|Boulons|Bolzen|Pernos
pedal|Pedál|Pédale|Pedal|Pedal
chain|Lánc|Chaîne|Kette|Cadena
mesh|Háló|Maillage|Netz|Malla
root|Gyökér|Racine|Wurzel|Raíz
body|Test|Corps|Körper|Cuerpo
head|Fej|Tête|Kopf|Cabeza
left|bal|gauche|links|izquierdo
right|jobb|droite|rechts|derecho
front|elülső|avant|vorne|delantero
back|hátsó|arrière|hinten|trasero
top|felső|supérieur|oben|superior
bottom|alsó|inférieur|unten|inferior
inside|belső|intérieur|innen|interior
outside|külső|extérieur|außen|exterior
wood|Fa|Bois|Holz|Madera
metal|Fém|Métal|Metall|Metal
plastic|Műanyag|Plastique|Kunststoff|Plástico
glass|Üveg|Verre|Glas|Vidrio
leather|Bőr|Cuir|Leder|Cuero
fabric|Szövet|Tissu|Stoff|Tela
gold|Arany|Or|Gold|Oro
silver|Ezüst|Argent|Silber|Plata
bronze|Bronz|Bronze|Bronze|Bronce
chrome|Króm|Chrome|Chrom|Cromo
brass|Sárgaréz|Laiton|Messing|Latón
steel|Acél|Acier|Stahl|Acero
copper|Réz|Cuivre|Kupfer|Cobre
iron|Vas|Fer|Eisen|Hierro
rubber|Gumi|Caoutchouc|Gummi|Caucho
stone|Kő|Pierre|Stein|Piedra
concrete|Beton|Béton|Beton|Hormigón
marble|Márvány|Marbre|Marmor|Mármol
ring|Gyűrű|Anneau|Ring|Anillo
crossbar|Keresztrúd|Traverse|Querstrebe|Travesaño
crossbars|Keresztrudak|Traverses|Querstreben|Travesaños
fixator|Rögzítő|Fixation|Befestigung|Fijación
car_body|Karosszéria|Carrosserie|Karosserie|Carrocería
headlight|Fényszóró|Phare|Scheinwerfer|Faro
headlights|Fényszórók|Phares|Scheinwerfer|Faros
steering_wheel|Kormánykerék|Volant|Lenkrad|Volante
cube|Kocka|Cube|Würfel|Cubo
cylinder|Henger|Cylindre|Zylinder|Cilindro
sphere|Gömb|Sphère|Kugel|Esfera
icosphere|Ikoz gömb|Icosphère|Ikosphäre|Icoesfera
plane|Sík|Plan|Ebene|Plano
cone|Kúp|Cône|Kegel|Cono
torus|Tórusz|Tore|Torus|Toro
monkey|Majom|Singe|Affe|Mono
empty|Üres|Vide|Leer|Vacío
organized|Rendezett|Organisé|Organisiert|Organizado
misc|Vegyes|Divers|Sonstiges|Varios
part|Alkatrész|Pièce|Teil|Pieza
area|Terület|Zone|Bereich|Área
model|Modell|Modèle|Modell|Modelo
'''

EXTRA_VOCABULARIES = {lang: {} for lang in ('hu', 'fr', 'de', 'es')}
for row in _WORDS.strip().splitlines():
    key, *values = row.split('|')
    for lang, value in zip(EXTRA_VOCABULARIES, values):
        EXTRA_VOCABULARIES[lang][key] = value

_ALIASES = {'couch': 'sofa', 'rear': 'back', 'suzanne': 'monkey', 'nogi': 'legs',
            'noga': 'leg', 'spinka': 'backrest', 'sidenie': 'seat', 'obod': 'rim',
            'obruch': 'ring', 'perekladina': 'crossbar', 'perekladini': 'crossbars',
            'setka': 'mesh', 'bolti': 'bolts', 'koleso': 'wheel', 'kolesa': 'wheels',
            'kuzov': 'car_body', 'fara': 'headlight', 'fary': 'headlights',
            'rul': 'steering_wheel', 'ruchka': 'handle', 'dver': 'door'}
for vocab in EXTRA_VOCABULARIES.values():
    vocab.update({alias: vocab[key] for alias, key in _ALIASES.items()})

# =====================================================================================
#  PLANET · APROVECHAR LOS TILES DEL MES (NO gastan km² de descarga)
#     %run -i /content/drive/MyDrive/Purdue_TarSpot_Project/PlanetScope_inventory/scripts/planet_tiles_aprovechar.py
#
#  A) SCENE TILES  → vista rápida (color natural) de CADA fecha despejada en temporada, recortada al sitio,
#                    + estimación de nubes SOBRE EL SITIO (no sobre toda la escena) → sirve para elegir
#                    qué escenas pedir en diciembre sin desperdiciar cuota.
#  B) BASEMAP TILES → mosaicos mensuales sin nubes de cada sitio (contexto 10 × 10 km), incluido el Ariari.
#
#  Son imágenes de visualización (PNG 8 bits): sirven para revisar y elegir, NO para calcular índices.
#  Todo queda en Drive y no se vuelve a pedir lo que ya existe (no gasta tiles dos veces).
# =====================================================================================
import os, io, json, math, glob, time, getpass, requests
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
try:
    display
except NameError:
    display = print

HACER_SCENE_TILES   = True
HACER_BASEMAPS      = True
TOPE_SCENE_TILES    = 90000     # te quedan ~99.594 este mes; deja margen
TOPE_BASEMAP_TILES  = 90000
ZOOM_ESCENA         = 15        # ≈ 3–4 m/píxel en pantalla
BUFFER_ESCENA_M     = 1500      # vista de 3 × 3 km alrededor del sitio
ZOOM_BASEMAP        = 14
BUFFER_BASEMAP_M    = 5000      # vista de 10 × 10 km alrededor del sitio
ANIOS               = [2020, 2021, 2022, 2023, 2024, 2025]

COORD = {'PPAC': (41.4432, -86.9301), 'RICE': (41.3269, -86.8028), 'SEPAC': (39.0357, -85.5291),
         'SWPAC': (38.7372, -87.4845), 'ARIARI': (3.650321, -73.782597)}

def _tiles():
    try:
        from google.colab import drive
        if not os.path.isdir('/content/drive/MyDrive'):
            drive.mount('/content/drive')
    except ImportError:
        pass
    base = '/content/drive/MyDrive/Purdue_TarSpot_Project' if os.path.isdir('/content/drive/MyDrive') \
        else globals().get('RUTA_BASE', './Purdue_TarSpot_Project')
    out = os.path.join(base, '09_Planet_Tiles'); os.makedirs(out, exist_ok=True)
    ruta_uso = os.path.join(out, 'uso_tiles.json')
    uso = json.load(open(ruta_uso)) if os.path.exists(ruta_uso) else {}
    mes = time.strftime('%Y-%m')
    uso.setdefault(mes, {'scene': 0, 'basemap': 0})
    key = os.environ.get('PL_API_KEY') or getpass.getpass('API key de Planet: ').strip()
    os.environ['PL_API_KEY'] = key
    ses = requests.Session(); ses.auth = (key, '')

    def xy(lat, lon, z):
        n = 2 ** z
        return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n

    def recorte(url_tpl, lat, lon, buf, z, tipo, tope):
        dy = buf / 111320; dx = buf / (111320 * math.cos(math.radians(lat)))
        x0, y0 = xy(lat + dy, lon - dx, z); x1, y1 = xy(lat - dy, lon + dx, z)
        tx, ty = range(int(x0), int(x1) + 1), range(int(y0), int(y1) + 1)
        if uso[mes][tipo] + len(tx) * len(ty) > tope:
            return None
        lienzo = Image.new('RGBA', (256 * len(tx), 256 * len(ty)))
        for i, x in enumerate(tx):
            for j, y in enumerate(ty):
                r = ses.get(url_tpl.format(z=z, x=x, y=y), timeout=60)
                uso[mes][tipo] += 1
                if r.status_code == 200:
                    lienzo.paste(Image.open(io.BytesIO(r.content)).convert('RGBA'), (256 * i, 256 * j))
        return lienzo.crop((int((x0 - tx[0]) * 256), int((y0 - ty[0]) * 256), int((x1 - tx[0]) * 256), int((y1 - ty[0]) * 256)))

    def nubes_sitio(img):
        a = np.asarray(img).astype(float)
        valido = a[..., 3] > 0
        if not valido.any():
            return np.nan, 0.0
        rgb = a[..., :3][valido]
        brillo = rgb.mean(axis=1); sat = rgb.max(axis=1) - rgb.min(axis=1)
        return round(100 * float(((brillo > 185) & (sat < 35)).mean()), 1), round(100 * float(valido.mean()), 1)

    def guardar_uso():
        json.dump(uso, open(ruta_uso, 'w'), indent=1)

    # ------------------------------ A) SCENE TILES ------------------------------
    if HACER_SCENE_TILES:
        inv = globals().get('PL_INV')
        if inv is None:
            c = sorted(glob.glob(os.path.join(base, '**', 'INVENTARIO_PLANET_COMPLETO.csv'), recursive=True) +
                       glob.glob(os.path.join(base, '**', 'INVENTARIO_PLANET*.csv'), recursive=True))
            inv = pd.read_csv(c[0], low_memory=False) if c else None
        if inv is None:
            print('⚠️ Sin inventario: se omiten los scene tiles (corre antes el gestor o el inventario).')
        else:
            d = inv.copy()
            d['despejada'] = d['despejada'].astype(str).eq('True')
            d['clear_pct'] = pd.to_numeric(d.get('clear_pct', d.get('p_clear_percent')), errors='coerce')
            d['n_bandas'] = pd.to_numeric(d['n_bandas'], errors='coerce')
            d = d[d.despejada & (pd.to_numeric(d.cobertura_aoi_pct, errors='coerce') >= 99) & d.sitio.isin(COORD)]
            d = d.sort_values(['n_bandas', 'clear_pct'], ascending=False).drop_duplicates(['sitio', 'fecha'])
            d = d.sort_values(['sitio', 'fecha'])
            print(f'A) SCENE TILES: {len(d)} fechas despejadas (una por sitio y día)')
            filas = []
            for _, r in d.iterrows():
                carpeta = os.path.join(out, 'escenas', r.sitio, str(r.anio)); os.makedirs(carpeta, exist_ok=True)
                png = os.path.join(carpeta, f'{r.fecha}_{r.etapa}_{r.item_id}.png')
                if os.path.exists(png):
                    img = Image.open(png)
                else:
                    lat, lon = COORD[r.sitio]
                    img = recorte(f'https://tiles.planet.com/data/v1/PSScene/{r.item_id}/{{z}}/{{x}}/{{y}}.png',
                                  lat, lon, BUFFER_ESCENA_M, ZOOM_ESCENA, 'scene', TOPE_SCENE_TILES)
                    if img is None:
                        print(f'   ⛔ Tope de scene tiles alcanzado ({uso[mes]["scene"]}). Lo demás queda para el próximo mes.'); break
                    img.save(png)
                nub, cob = nubes_sitio(img)
                filas.append({'sitio': r.sitio, 'campana': r.campana, 'anio': r.anio, 'etapa': r.etapa, 'fecha': r.fecha,
                              'item_id': r.item_id, 'n_bandas': r.n_bandas, 'clear_pct_escena': r.clear_pct,
                              'nubes_sobre_sitio_%': nub, 'cobertura_vista_%': cob, 'png': os.path.relpath(png, base)})
                if len(filas) % 50 == 0:
                    guardar_uso(); print(f'   … {len(filas)} vistas · {uso[mes]["scene"]} scene tiles usados')
            guardar_uso()
            qa = pd.DataFrame(filas)
            if len(qa):
                qa['apta_para_pedir'] = (qa['nubes_sobre_sitio_%'] < 5) & (qa['cobertura_vista_%'] > 95)
                qa.to_csv(os.path.join(out, 'QA_VISUAL_ESCENAS.csv'), index=False, encoding='utf-8-sig')
                print(f"   ✅ {len(qa)} vistas · {int(qa.apta_para_pedir.sum())} realmente despejadas sobre el sitio")
                display(qa.groupby(['sitio', 'anio']).agg(fechas=('fecha', 'size'), aptas=('apta_para_pedir', 'sum')))
                # Hoja de contacto por sitio y año (máx. 60 miniaturas por hoja)
                for (s, a), g in qa.groupby(['sitio', 'anio']):
                    g = g.head(60); n = len(g); cols = 10; filas_f = math.ceil(n / cols)
                    fig, axes = plt.subplots(filas_f, cols, figsize=(2.0 * cols, 2.7 * filas_f), squeeze=False,
                                             gridspec_kw={'hspace': 0.45})
                    for ax in axes.ravel():
                        ax.axis('off')
                    for ax, (_, q) in zip(axes.ravel(), g.iterrows()):
                        ax.imshow(Image.open(os.path.join(base, q.png)))
                        ax.set_title(f"{q.fecha[5:]} {q.etapa[:5]}\nnube sitio {q['nubes_sobre_sitio_%']:.0f}%",
                                     fontsize=7, color='#0b0b0b' if q.apta_para_pedir else '#b3261e')
                    fig.suptitle(f'{s} {a}: vistas de cada fecha despejada (rojo = nube sobre el sitio)', fontsize=11, fontweight='bold', x=0.01, ha='left')
                    plt.tight_layout(); fig.savefig(os.path.join(out, f'HOJA_{s}_{a}.png'), dpi=120, bbox_inches='tight'); plt.close(fig)
                print('   Hojas de contacto en', out)

    # ------------------------------ B) BASEMAPS ------------------------------
    if HACER_BASEMAPS:
        print('\nB) BASEMAPS (mosaicos mensuales)')
        mos, url = [], 'https://api.planet.com/basemaps/v1/mosaics?name__contains=global_monthly&_page_size=250'
        while url:
            r = ses.get(url, timeout=120)
            if r.status_code != 200:
                print(f'   ⚠️ No se pudo listar mosaicos ({r.status_code}): {r.text[:200]}'); break
            j = r.json(); mos += j.get('mosaics', [])
            url = (j.get('_links') or {}).get('_next')
        mos = [m for m in mos if str(m.get('first_acquired', ''))[:4].isdigit() and int(m['first_acquired'][:4]) in ANIOS]
        print(f'   {len(mos)} mosaicos mensuales disponibles para tu cuenta en {ANIOS[0]}–{ANIOS[-1]}')
        filas = []
        for m in sorted(mos, key=lambda m: m['first_acquired']):
            mes_m = m['first_acquired'][:7]
            for s, (lat, lon) in COORD.items():
                carpeta = os.path.join(out, 'basemaps', s); os.makedirs(carpeta, exist_ok=True)
                png = os.path.join(carpeta, f'{mes_m}_{m["name"]}.png')
                if not os.path.exists(png):
                    tpl = f"https://tiles.planet.com/basemaps/v1/planet-tiles/{m['name']}/gmap/{{z}}/{{x}}/{{y}}.png?api_key={key}"
                    img = recorte(tpl, lat, lon, BUFFER_BASEMAP_M, ZOOM_BASEMAP, 'basemap', TOPE_BASEMAP_TILES)
                    if img is None:
                        print(f'   ⛔ Tope de basemap tiles alcanzado ({uso[mes]["basemap"]}).'); break
                    img.save(png)
                filas.append({'sitio': s, 'mes': mes_m, 'mosaico': m['name'], 'png': os.path.relpath(png, base)})
            else:
                guardar_uso(); continue
            break
        guardar_uso()
        bm = pd.DataFrame(filas)
        if len(bm):
            bm.to_csv(os.path.join(out, 'LISTA_BASEMAPS.csv'), index=False, encoding='utf-8-sig')
            for s, g in bm.groupby('sitio'):
                g = g.sort_values('mes'); anios = sorted({x[:4] for x in g.mes})
                fig, axes = plt.subplots(len(anios), 12, figsize=(24, 2.2 * len(anios)), squeeze=False)
                for ax in axes.ravel():
                    ax.axis('off')
                for _, q in g.iterrows():
                    ax = axes[anios.index(q.mes[:4]), int(q.mes[5:7]) - 1]
                    ax.imshow(Image.open(os.path.join(base, q.png))); ax.set_title(q.mes, fontsize=8)
                fig.suptitle(f'{s}: mosaico mensual Planet (10 × 10 km)', fontsize=12, fontweight='bold', x=0.01, ha='left')
                plt.tight_layout(); fig.savefig(os.path.join(out, f'BASEMAPS_{s}.png'), dpi=110, bbox_inches='tight'); plt.close(fig)
            print(f'   ✅ {len(bm)} vistas mensuales · hojas BASEMAPS_<sitio>.png en {out}')

    print(f"\nTiles usados este mes según este script → scene: {uso[mes]['scene']} · basemap: {uso[mes]['basemap']}")
    print('Compáralo con tu cuenta en planet.com (Plans). Registro:', ruta_uso)

_tiles()

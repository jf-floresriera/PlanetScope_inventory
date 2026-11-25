# =====================================================================================
#  PLANET · GRÁFICAS DEL INVENTARIO + IMÁGENES E ÍNDICES POR ETAPA DEL CULTIVO
#  Ejecutar al final del cuaderno, después del inventario (necesita PL_INV en memoria):
#     %run -i /content/drive/MyDrive/Purdue_TarSpot_Project/PlanetScope_inventory/scripts/planet_graficas_e_indices.py
# =====================================================================================
import os, io, json, time, math, glob, getpass, requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
try:
    display
except NameError:
    display = print

# ------------------------------- CONFIGURACIÓN -------------------------------------
HACER_GRAFICAS   = True
HACER_IMAGENES   = True       # pide a Planet los recortes y calcula índices
CONFIRMAR_PEDIDO = False      # ⚠️ NO usar True: los pedidos se hacen SOLO con planet_gestor_descargas.py
ANIO_INDIANA     = 2024       # año de las imágenes para los 4 sitios de Indiana
ANIO_ARIARI      = None       # None = el año del Ariari con más fechas despejadas
CAMPANA_ARIARI   = 'Semestre A'
BUFFER_IMG       = 500        # recorte de 1 × 1 km (= 1 km² de cuota por imagen). 1500 = 3 × 3 km (9 km²)

try:                                                   # las imágenes SIEMPRE van a Google Drive (no al disco temporal de Colab)
    from google.colab import drive
    if not os.path.isdir('/content/drive/MyDrive'):
        drive.mount('/content/drive')
except ImportError:
    pass
BASE = globals().get('RUTA_BASE', '/content/drive/MyDrive/Purdue_TarSpot_Project')
OUT_FIG = os.path.join(BASE, '07_Figuras', 'Planet'); os.makedirs(OUT_FIG, exist_ok=True)
OUT_IMG = os.path.join(BASE, '08_Planet_PlanetScope', 'imagenes_recortadas'); os.makedirs(OUT_IMG, exist_ok=True)
OUT_TAB = os.path.join(BASE, '01_Tablas_Inventarios'); os.makedirs(OUT_TAB, exist_ok=True)

COORD = {'PPAC': (41.4432, -86.9301), 'RICE': (41.3269, -86.8028), 'SEPAC': (39.0357, -85.5291),
         'SWPAC': (38.7372, -87.4845), 'ARIARI': (3.650321, -73.782597)}
NOMBRE = {'PPAC': 'PPAC · Porter, IN', 'RICE': 'RICE · LaPorte, IN', 'SEPAC': 'SEPAC · Jennings, IN',
          'SWPAC': 'SWPAC · Knox, IN', 'ARIARI': 'Río Ariari · El Castillo, Meta'}
CAL = {'Maíz': [('Siembra', '04-01', '05-20'), ('Establecimiento', '05-21', '06-15'), ('Vegetativo', '06-16', '07-20'),
                ('Reproductivo', '07-21', '09-10'), ('Madurez', '09-11', '09-30'), ('Cosecha', '10-01', '10-31')],
       'Semestre A': [('Siembra', '03-01', '04-30'), ('Establecimiento', '05-01', '05-31'), ('Vegetativo', '06-01', '06-30'),
                      ('Reproductivo', '07-01', '07-31'), ('Cosecha', '08-01', '09-15')],
       'Semestre B': [('Siembra', '08-15', '09-20'), ('Establecimiento', '09-21', '10-20'), ('Vegetativo', '10-21', '11-20'),
                      ('Reproductivo', '11-21', '12-20'), ('Cosecha', '12-21', '01-31')]}
ETAPAS = ['Siembra', 'Establecimiento', 'Vegetativo', 'Reproductivo', 'Madurez', 'Cosecha']

# Paleta validada (colores categóricos en orden fijo; secuencial azul de un solo tono)
COL_SITIO = {'PPAC': '#2a78d6', 'RICE': '#eb6834', 'SEPAC': '#1baf7a', 'SWPAC': '#eda100', 'ARIARI': '#e87ba4'}
AZULES = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']
TXT, TXT2, GRIS, FONDO = '#0b0b0b', '#52514e', '#c9c7c0', '#f3f2ee'
plt.rcParams.update({'font.size': 10, 'axes.edgecolor': GRIS, 'axes.labelcolor': TXT2, 'xtick.color': TXT2,
                     'ytick.color': TXT2, 'axes.titleweight': 'bold', 'axes.titlesize': 11, 'axes.titlelocation': 'left',
                     'axes.spines.top': False, 'axes.spines.right': False, 'figure.facecolor': 'white'})

def ventanas(camp, anio):
    et = CAL[camp]; m0, d0 = map(int, et[0][1].split('-'))
    def f(md):
        m, d = map(int, md.split('-'))
        return pd.Timestamp(anio + (1 if (m, d) < (m0, d0) else 0), m, d)
    return [(e, f(a), f(b)) for e, a, b in et]

def guardar(fig, nombre):
    fig.savefig(os.path.join(OUT_FIG, nombre), dpi=200, bbox_inches='tight')
    plt.show()

# ------------------------------- PREPARAR INVENTARIO -------------------------------
INV = PL_INV.copy()
INV['despejada'] = INV['despejada'].astype(str).eq('True')
INV['anio'] = INV['anio'].astype(int)
INV['n_bandas'] = pd.to_numeric(INV['n_bandas'], errors='coerce').fillna(4).astype(int)
INV['clear_pct'] = pd.to_numeric(INV.get('clear_pct', INV.get('p_clear_percent')), errors='coerce')
INV['cobertura_aoi_pct'] = pd.to_numeric(INV['cobertura_aoi_pct'], errors='coerce')
INV = INV[INV.campana.isin(CAL)]
SITIOS_INV = [s for s in COL_SITIO if s in INV.sitio.unique()]
print('Sitios en el inventario:', SITIOS_INV, '| años:', sorted(INV.anio.unique()))

# =====================================================================================
#  A. GRÁFICAS DEL INVENTARIO
# =====================================================================================
def estado_diario(d):
    """3 = despejada 8 bandas · 2 = despejada 4 bandas · 1 = solo nubosa o sin cubrir el AOI · 0 = sin imagen."""
    e = np.where(d.despejada & (d.n_bandas == 8), 3, np.where(d.despejada, 2, 1))
    return pd.Series(e, index=d.fecha).groupby(level=0).max()

def grafica_calendario(sitio):
    d0 = INV[INV.sitio == sitio]
    camps = [c for c in CAL if c in d0.campana.unique()]
    anios = sorted(d0.anio.unique())
    cmap = ListedColormap([FONDO, GRIS, '#1baf7a', '#2a78d6'])
    fig, axes = plt.subplots(len(camps), 1, figsize=(15, 0.48 * len(anios) * len(camps) + 1.6 * len(camps)), squeeze=False)
    for ax, camp in zip(axes[:, 0], camps):
        filas, etiquetas, res = [], [], []
        for anio in anios:
            vs = ventanas(camp, anio)
            dias = pd.date_range(vs[0][1], vs[-1][2])
            est = estado_diario(d0[(d0.campana == camp) & (d0.anio == anio)])
            est.index = pd.to_datetime(est.index)
            filas.append(est.reindex(dias).fillna(0).values)
            etiquetas.append(str(anio))
            res.append(f"{int((est >= 2).sum())} despejadas · {len(est)} con imagen")
        n = max(len(f) for f in filas)
        M = np.array([np.pad(f, (0, n - len(f))) for f in filas])
        ax.imshow(M, aspect='auto', cmap=cmap, vmin=0, vmax=3, interpolation='nearest')
        ax.set_yticks(range(len(anios))); ax.set_yticklabels(etiquetas)
        for y in np.arange(.5, len(anios) - .5):
            ax.axhline(y, color='white', lw=3)
        vs = ventanas(camp, anios[0]); t0 = vs[0][1]
        for e, a, b in vs:
            x0, x1 = (a - t0).days - .5, (b - t0).days + .5
            ax.axvline(x0, color='white', lw=2.5)
            ax.text((x0 + x1) / 2, -0.75, e, ha='center', va='bottom', fontsize=9, color=TXT)
        meses = pd.date_range(t0, vs[-1][2], freq='MS')
        ax.set_xticks([(m - t0).days for m in meses]); ax.set_xticklabels([m.strftime('%b') for m in meses])
        ax.set_xlim(-.5, n - .5); ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_visible(False)
        for i, r in enumerate(res):
            ax.text(n + 2, i, r, va='center', fontsize=8.5, color=TXT2)
        ax.set_title(f"{NOMBRE[sitio]} — {camp}", pad=22)
    ley = [Patch(color='#2a78d6', label='Despejada · 8 bandas (con Red Edge)'), Patch(color='#1baf7a', label='Despejada · 4 bandas'),
           Patch(color=GRIS, label='Nubosa o no cubre el sitio'), Patch(color=FONDO, label='Sin imagen')]
    fig.legend(handles=ley, loc='lower left', ncol=4, frameon=False, bbox_to_anchor=(0.06, -0.04))
    plt.tight_layout()
    guardar(fig, f'planet_calendario_{sitio}.png')

def grafica_etapas():
    t = (INV[INV.despejada].groupby(['sitio', 'campana', 'anio', 'etapa']).fecha.nunique()
         .reset_index().groupby(['sitio', 'etapa']).fecha.agg(['mean', 'min', 'max']))
    etapas = [e for e in ETAPAS if e in t.index.get_level_values(1)]
    fig, ax = plt.subplots(figsize=(13, 5))
    w = 0.8 / len(SITIOS_INV)
    for i, s in enumerate(SITIOS_INV):
        x = np.arange(len(etapas)) + (i - (len(SITIOS_INV) - 1) / 2) * w
        v = t.reindex([(s, e) for e in etapas])
        ax.bar(x, v['mean'], width=w - 0.02, color=COL_SITIO[s], label=NOMBRE[s], edgecolor='white', linewidth=1.5)
        ax.vlines(x, v['min'], v['max'], color=TXT2, lw=1)
    ax.set_xticks(range(len(etapas))); ax.set_xticklabels(etapas)
    ax.set_ylabel('Fechas despejadas por campaña')
    ax.yaxis.grid(True, color='#e6e5e0'); ax.set_axisbelow(True)
    ax.set_title('¿Cuántas fechas despejadas hay en cada etapa del cultivo? (barra = promedio · línea = mínimo–máximo entre años)')
    ax.legend(frameon=False, ncol=len(SITIOS_INV), loc='upper left', bbox_to_anchor=(0, -0.08))
    plt.tight_layout()
    guardar(fig, 'planet_fechas_por_etapa.png')

def grafica_sitio_anio():
    t = INV[INV.despejada].groupby(['sitio', 'anio']).fecha.nunique().unstack(fill_value=0).reindex(SITIOS_INV)
    tot = INV.groupby(['sitio', 'anio']).fecha.nunique().unstack(fill_value=0).reindex(SITIOS_INV)
    fig, ax = plt.subplots(figsize=(1.4 * t.shape[1] + 3, 0.7 * len(t) + 1.5))
    cmap = LinearSegmentedColormap.from_list('azul', AZULES)
    ax.imshow(t.values, cmap=cmap, aspect='auto')
    for i in range(t.shape[0]):
        for j in range(t.shape[1]):
            v = t.values[i, j]
            ax.text(j, i, f"{v}\nde {tot.values[i, j]}", ha='center', va='center', fontsize=9,
                    color='white' if (v - t.values.min()) / max(t.values.max() - t.values.min(), 1) > 0.5 else TXT)
    ax.set_xticks(range(t.shape[1])); ax.set_xticklabels(t.columns)
    ax.set_yticks(range(len(t))); ax.set_yticklabels([NOMBRE[s] for s in t.index])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    ax.set_title('Fechas despejadas por sitio y año (de las fechas con imagen en temporada)')
    plt.tight_layout()
    guardar(fig, 'planet_despejadas_sitio_anio.png')

def grafica_sensores():
    t = INV.drop_duplicates(['sitio', 'item_id']).groupby(['anio', 'p_instrument']).size().unstack(fill_value=0)
    t = t.reindex(columns=[c for c in ['PS2', 'PS2.SD', 'PSB.SD'] if c in t.columns])
    p = t.div(t.sum(axis=1), axis=0) * 100
    nombres = {'PS2': 'Dove Classic · 4 bandas', 'PS2.SD': 'Dove-R · 4 bandas', 'PSB.SD': 'SuperDove · 8 bandas'}
    cols = {'PS2': '#eb6834', 'PS2.SD': '#eda100', 'PSB.SD': '#2a78d6'}
    fig, ax = plt.subplots(figsize=(10, 3.2))
    izq = np.zeros(len(p))
    for c in p.columns:
        ax.barh(p.index.astype(str), p[c], left=izq, color=cols[c], edgecolor='white', linewidth=2, label=nombres[c])
        for y, (l, v) in enumerate(zip(izq, p[c])):
            if v >= 9:
                ax.text(l + v / 2, y, f'{v:.0f} %', ha='center', va='center', color='white', fontsize=9, fontweight='bold')
        izq += p[c].values
    ax.set_xlim(0, 100); ax.invert_yaxis(); ax.set_xlabel('% de escenas')
    ax.set_title('Sensores PlanetScope por año: desde 2022 casi todo es SuperDove de 8 bandas')
    ax.legend(frameon=False, ncol=3, loc='upper left', bbox_to_anchor=(0, -0.25))
    plt.tight_layout()
    guardar(fig, 'planet_sensores_por_anio.png')

if HACER_GRAFICAS:
    for s in SITIOS_INV:
        grafica_calendario(s)
    grafica_etapas()
    grafica_sitio_anio()
    grafica_sensores()

# =====================================================================================
#  B. IMÁGENES REALES E ÍNDICES POR ETAPA (Orders API: recorte al sitio)
# =====================================================================================
KEY = os.environ.get('PL_API_KEY') or getpass.getpass('API key de Planet: ').strip()
os.environ['PL_API_KEY'] = KEY
SES_O = requests.Session(); SES_O.auth = (KEY, '')
ORDERS = 'https://api.planet.com/compute/ops/orders/v2'

def aoi(sitio, b=BUFFER_IMG):
    lat, lon = COORD[sitio]
    dy = b / 111320; dx = b / (111320 * math.cos(math.radians(lat)))
    return {'type': 'Polygon', 'coordinates': [[[lon-dx, lat-dy], [lon+dx, lat-dy], [lon+dx, lat+dy], [lon-dx, lat+dy], [lon-dx, lat-dy]]]}

def elegir_escenas():
    """La mejor escena por etapa: despejada, cubre todo el sitio, prefiere 8 bandas y mayor % despejado."""
    sel = []
    for s in SITIOS_INV:
        d = INV[(INV.sitio == s) & INV.despejada & (INV.cobertura_aoi_pct >= 99)]
        if s == 'ARIARI':
            d = d[d.campana == CAMPANA_ARIARI]
            anio = ANIO_ARIARI or (d.groupby('anio').fecha.nunique().idxmax() if len(d) else None)
        else:
            anio = ANIO_INDIANA
        d = d[d.anio == anio].sort_values(['n_bandas', 'clear_pct'], ascending=False)
        sel.append(d.groupby('etapa', sort=False).head(1))
    sel = pd.concat(sel) if sel else pd.DataFrame()
    sel['_o'] = sel.etapa.map({e: i for i, e in enumerate(ETAPAS)})
    return sel.sort_values(['sitio', '_o'])[['sitio', 'campana', 'anio', 'etapa', 'fecha', 'item_id', 'n_bandas', 'clear_pct']]

REGISTRO = os.path.join(OUT_IMG, 'pedidos_planet.json')    # cada pedido queda anotado en Drive

def _reg():
    return json.load(open(REGISTRO)) if os.path.exists(REGISTRO) else {}

def _reg_guardar(r):
    json.dump(r, open(REGISTRO, 'w'), indent=1)

def ya_descargado(item_id):
    return any(os.path.getsize(f) > 0 for f in glob.glob(os.path.join(OUT_IMG, '**', f'{item_id}*SR*.tif'), recursive=True))

def descargar_pedido(oid, sitio):
    """Descarga (o termina de descargar) un pedido ya hecho. NO gasta cuota."""
    print(f'⏳ {sitio}: pedido {oid}', end='', flush=True)
    for _ in range(120):                                      # espera hasta ~30 min
        st = SES_O.get(f'{ORDERS}/{oid}', timeout=120).json()
        if st.get('state') in ('success', 'partial', 'failed', 'cancelled'):
            break
        print('.', end='', flush=True); time.sleep(15)
    print(f" {st.get('state')}")
    carpeta = os.path.join(OUT_IMG, sitio); os.makedirs(carpeta, exist_ok=True)
    n = 0
    for res in (st.get('_links') or {}).get('results') or []:
        nombre = os.path.basename(res['name']); destino = os.path.join(carpeta, nombre)
        if not nombre.endswith(('.tif', '.json', '.xml')) or (os.path.exists(destino) and os.path.getsize(destino) > 0):
            continue
        with SES_O.get(res['location'], stream=True, timeout=300) as dl:
            if dl.status_code != 200:
                print(f'   ⚠️ {nombre}: enlace vencido o no disponible ({dl.status_code})'); continue
            with open(destino + '.part', 'wb') as f:
                for ch in dl.iter_content(1 << 20):
                    f.write(ch)
        os.replace(destino + '.part', destino); n += 1
    print(f'   {n} archivos nuevos guardados en Drive → {carpeta}')

def pedir_y_descargar(sitio, ids):
    reg = _reg()
    # 1) Lo que ya se pidió antes: solo se descarga de nuevo, sin gastar cuota
    for oid, info in reg.items():
        if info['sitio'] == sitio and set(info['ids']) & {i for i in ids if not ya_descargado(i)}:
            descargar_pedido(oid, sitio)
    pedidas = {i for info in reg.values() for i in info['ids']}
    nuevas = [i for i in ids if not ya_descargado(i) and i not in pedidas]
    faltan = [i for i in ids if not ya_descargado(i) and i in pedidas]
    if faltan:
        print(f'   ⚠️ {sitio}: {len(faltan)} escenas ya se pidieron pero no se pudieron bajar; no se vuelven a pedir: {faltan}')
    if not nuevas:
        return
    # 2) Pedido nuevo (gasta cuota) — se anota en el registro ANTES de descargar
    cuerpo = {'name': f'TarSpot_{sitio}_{time.strftime("%Y%m%d_%H%M")}',
              'products': [{'item_ids': nuevas, 'item_type': 'PSScene', 'product_bundle': 'analytic_8b_sr_udm2,analytic_sr_udm2'}],
              'tools': [{'clip': {'aoi': aoi(sitio)}}]}
    r = SES_O.post(ORDERS, json=cuerpo, timeout=120)
    if r.status_code >= 400:
        print(f'❌ {sitio}: Planet rechazó el pedido ({r.status_code}): {r.text[:300]}'); return
    oid = r.json()['id']
    reg[oid] = {'sitio': sitio, 'ids': nuevas, 'fecha_pedido': time.strftime('%Y-%m-%d %H:%M'),
                'km2': len(nuevas) * (2 * BUFFER_IMG / 1000) ** 2}
    _reg_guardar(reg)
    descargar_pedido(oid, sitio)

def ver_guardadas():
    """Lista lo que ya tienes en Drive y los pedidos hechos (no gasta nada)."""
    f = sorted(glob.glob(os.path.join(OUT_IMG, '**', '*SR*.tif'), recursive=True))
    print(f'{len(f)} imágenes guardadas en {OUT_IMG}')
    for x in f:
        print('  ', os.path.relpath(x, OUT_IMG), f'{os.path.getsize(x) / 1e6:.1f} MB')
    reg = _reg()
    print(f"{len(reg)} pedidos registrados | km² usados en total: {sum(v.get('km2', 0) for v in reg.values()):.0f}")

def leer_tif(ruta):
    import rasterio
    with rasterio.open(ruta) as src:
        return src.read().astype('float32'), src.profile

def indices(sr):
    e = 1e-6
    if sr.shape[0] >= 8:
        b, g1, g, r, re, nir = sr[1], sr[2], sr[3], sr[5], sr[6], sr[7]
    else:
        b, g, r, nir = sr[:4]; re = g1 = None
    out = {'NDVI': (nir - r) / (nir + r + e), 'GNDVI': (nir - g) / (nir + g + e),
           'EVI2': 2.5 * (nir - r) / (nir + 2.4 * r + 1)}
    if re is not None:
        out.update({'NDRE': (nir - re) / (nir + re + e), 'CIrededge': nir / (re + e) - 1, 'PSRI': (r - b) / (re + e)})
    return out

def color(sr, bandas, gan=0.25):
    rgb = np.dstack([sr[i] for i in bandas])
    return np.clip(np.clip(rgb / gan, 0, 1) ** (1 / 1.8), 0, 1)

def cargar(sitio, item_id):
    sr_f = glob.glob(os.path.join(OUT_IMG, sitio, f'{item_id}*SR*clip*.tif')) + glob.glob(os.path.join(OUT_IMG, sitio, f'{item_id}*SR*.tif'))
    if not sr_f:
        return None
    sr, prof = leer_tif(sr_f[0]); sr = sr / 10000.0
    udm = glob.glob(os.path.join(OUT_IMG, sitio, f'{item_id}*udm2*.tif'))
    claro = leer_tif(udm[0])[0][0] == 1 if udm else np.ones(sr.shape[1:], bool)
    valido = claro & (sr.sum(axis=0) > 0)
    return {'sr': sr, 'valido': valido, 'prof': prof, 'n': sr.shape[0]}

FILAS_FIG = [('Color natural', 'rgb', None), ('Falso color (NIR·R·G)', 'fc', None),
             ('NDVI · vigor', 'NDVI', 'Greens'), ('NDRE · clorofila (Red Edge)', 'NDRE', 'Greens'),
             ('PSRI · senescencia', 'PSRI', 'Oranges')]

def figura_indices(sitio, escenas):
    datos = [(r, cargar(sitio, r.item_id)) for _, r in escenas.iterrows()]
    datos = [(r, d) for r, d in datos if d is not None]
    if not datos:
        print(f'⚠️ {sitio}: no hay imágenes descargadas'); return []
    calc = [indices(d['sr']) for _, d in datos]
    lim = {}
    for _, k, _c in FILAS_FIG[2:]:
        v = np.concatenate([c[k][d['valido']] for c, (_, d) in zip(calc, datos) if k in c] or [np.array([0., 1.])])
        lim[k] = np.nanpercentile(v, [2, 98])
    nC = len(datos)
    fig, ax_all = plt.subplots(len(FILAS_FIG), nC + 1, figsize=(2.9 * nC + 1.2, 2.95 * len(FILAS_FIG)), squeeze=False,
                               gridspec_kw={'width_ratios': [1] * nC + [0.06], 'wspace': 0.08, 'hspace': 0.12})
    axes = ax_all[:, :nC]
    for i, (_, k, _c) in enumerate(FILAS_FIG):
        ax_all[i, nC].set_visible(k not in ('rgb', 'fc'))
    stats = []
    for j, ((r, d), c) in enumerate(zip(datos, calc)):
        for i, (tit, k, cm) in enumerate(FILAS_FIG):
            ax = axes[i, j]; ax.set_xticks([]); ax.set_yticks([])
            for s in ax.spines.values():
                s.set_visible(False)
            if k == 'rgb':
                ax.imshow(color(d['sr'], [5, 3, 1] if d['n'] >= 8 else [2, 1, 0]))
                ax.set_title(f"{r.etapa}\n{pd.Timestamp(r.fecha):%d %b %Y}", fontsize=10, loc='center')
            elif k == 'fc':
                ax.imshow(color(d['sr'], [7, 5, 3] if d['n'] >= 8 else [3, 2, 1], gan=0.45))
            elif k in c:
                m = np.ma.masked_where(~d['valido'], c[k])
                cmo = plt.get_cmap(cm).copy(); cmo.set_bad('#d9d8d3')
                im = ax.imshow(m, cmap=cmo, vmin=lim[k][0], vmax=lim[k][1])
                ax.text(0.03, 0.04, f'media {np.nanmean(c[k][d["valido"]]):.2f}', transform=ax.transAxes, fontsize=8,
                        color=TXT, bbox=dict(facecolor='white', alpha=.8, edgecolor='none', pad=1.5))
                fig.colorbar(im, cax=ax_all[i, nC])
            else:
                ax.text(.5, .5, 'Sin Red Edge\n(escena de 4 bandas)', ha='center', va='center', fontsize=9, color=TXT2, transform=ax.transAxes)
            if j == 0:
                ax.set_ylabel(tit, fontsize=10, color=TXT)
        fila = {'sitio': sitio, 'campana': r.campana, 'anio': r.anio, 'etapa': r.etapa, 'fecha': r.fecha, 'item_id': r.item_id,
                'bandas': d['n'], 'pct_pixeles_claros': round(100 * d['valido'].mean(), 1)}
        fila.update({f'{k}_media': float(np.nanmean(v[d['valido']])) for k, v in c.items()})
        fila.update({f'{k}_desv': float(np.nanstd(v[d['valido']])) for k, v in c.items()})
        stats.append(fila)
        guardar_indices_tif(sitio, r.item_id, c, d['prof'])
    fig.suptitle(f"{NOMBRE[sitio]} · {datos[0][0].campana} {datos[0][0].anio} — PlanetScope por etapa (recorte {2*BUFFER_IMG/1000:.0f} × {2*BUFFER_IMG/1000:.0f} km; gris = nube/sombra según UDM2)",
                 fontsize=12, fontweight='bold', x=0.02, ha='left', y=0.93)
    guardar(fig, f'planet_indices_{sitio}_{datos[0][0].anio}.png')
    return stats

def guardar_indices_tif(sitio, item_id, c, prof):
    try:
        import rasterio
        p = prof.copy(); p.update(count=len(c), dtype='float32', nodata=np.nan)
        with rasterio.open(os.path.join(OUT_IMG, sitio, f'{item_id}_INDICES.tif'), 'w', **p) as dst:
            for i, (k, v) in enumerate(c.items(), 1):
                dst.write(v.astype('float32'), i); dst.set_band_description(i, k)
    except Exception as e:
        print('  (no se guardó el GeoTIFF de índices:', e, ')')

def grafica_evolucion(st):
    st = st.copy(); st['_o'] = st.etapa.map({e: i for i, e in enumerate(ETAPAS)})
    ks = [k for k in ['NDVI', 'NDRE', 'PSRI'] if f'{k}_media' in st]
    sitios = [s for s in COL_SITIO if s in st.sitio.unique()]
    fig, axes = plt.subplots(1, len(ks), figsize=(5.4 * len(ks), 4.6), squeeze=False)
    for ax, k in zip(axes[0], ks):
        for n, s in enumerate(sitios):
            g = st[st.sitio == s].sort_values('_o').dropna(subset=[f'{k}_media'])
            x = g._o + (n - (len(sitios) - 1) / 2) * 0.07
            ax.vlines(x, g[f'{k}_media'] - g[f'{k}_desv'], g[f'{k}_media'] + g[f'{k}_desv'], color=COL_SITIO[s], lw=1, alpha=.45)
            ax.plot(x, g[f'{k}_media'], color=COL_SITIO[s], lw=2, marker='o', ms=8, mec='white', mew=2, label=NOMBRE[s])
        ax.set_xticks(range(len(ETAPAS))); ax.set_xticklabels(ETAPAS, rotation=30, ha='right')
        ax.set_title(k); ax.yaxis.grid(True, color='#e6e5e0'); ax.set_axisbelow(True)
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, loc='lower center', ncol=len(sitios), bbox_to_anchor=(0.5, -0.02))
    fig.suptitle('Evolución de los índices a lo largo del cultivo (media del sitio; línea fina = ± 1 desv. estándar; solo píxeles claros)',
                 fontsize=12, fontweight='bold', x=0.02, ha='left')
    plt.tight_layout(rect=(0, 0.08, 1, 0.95))
    guardar(fig, 'planet_evolucion_indices.png')

if HACER_IMAGENES:
    SEL_IMG = elegir_escenas()
    print('\nEscenas elegidas (una por etapa):'); display(SEL_IMG)
    _pedidas = {i for v in _reg().values() for i in v['ids']}
    nuevas = SEL_IMG[~SEL_IMG.item_id.apply(ya_descargado)]
    print(f'Ya en Drive: {len(SEL_IMG) - len(nuevas)} | ya pedidas antes (se bajan sin costo): {nuevas.item_id.isin(_pedidas).sum()}')
    nuevas = nuevas[~nuevas.item_id.isin(_pedidas)]
    print(f'Pedidos NUEVOS: {len(nuevas)} escenas × {(2*BUFFER_IMG/1000)**2:.0f} km² ≈ {len(nuevas)*(2*BUFFER_IMG/1000)**2:.0f} km² de tu cuota mensual (3.000 km²)')
    if CONFIRMAR_PEDIDO:
        for s, g in SEL_IMG.groupby('sitio'):
            pedir_y_descargar(s, g.item_id.tolist())
    if True:
        STATS = []
        for s in SEL_IMG.sitio.unique():
            STATS += figura_indices(s, SEL_IMG[SEL_IMG.sitio == s])
        STATS = pd.DataFrame(STATS)
        if len(STATS):
            STATS.to_csv(os.path.join(OUT_TAB, 'PLANET_INDICES_POR_ETAPA.csv'), index=False, encoding='utf-8-sig')
            grafica_evolucion(STATS)
            display(STATS[['sitio', 'etapa', 'fecha', 'bandas', 'pct_pixeles_claros'] + [c for c in STATS if c.endswith('_media')]].round(3))
        ver_guardadas()
        print('✅ Figuras en', OUT_FIG, '| recortes e índices (GeoTIFF para QGIS) en', OUT_IMG)


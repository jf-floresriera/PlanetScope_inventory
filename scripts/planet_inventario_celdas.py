# %% [P1]
# ===================== 7. PLANET PLANETSCOPE · TEMPORADA DE CULTIVO =====================
# Configuración, API key y prueba rápida
import os, io, math, json, time, getpass, requests
PL_API_KEY = os.environ.get('PL_API_KEY') or getpass.getpass('Pega tu API key de Planet y presiona Enter: ').strip()
os.environ['PL_API_KEY'] = PL_API_KEY
PL_API = 'https://api.planet.com/data/v1'
PL_SES = requests.Session()
PL_SES.auth = (PL_API_KEY, '')

CARPETAS['planet'] = os.path.join(RUTA_BASE, '08_Planet_PlanetScope')
os.makedirs(os.path.join(CARPETAS['planet'], 'respuestas_api'), exist_ok=True)

# Sitios: los 4 de Indiana (tu diccionario SITIOS) + río Ariari (El Castillo, Meta, Colombia)
PL_SITIOS = {s: dict(lat=lat, lon=lon, region='Indiana, EE. UU.', calendario='INDIANA_MAIZ')
             for s, (lat, lon) in SITIOS.items()}
PL_SITIOS['ARIARI'] = dict(lat=3.650321, lon=-73.782597, region='El Castillo, Meta, Colombia', calendario='ARIARI')
PL_NOMBRES = {'PPAC': 'Pinney Purdue Agricultural Center (Porter)', 'RICE': 'Purdue Mary S. Rice Farm (LaPorte)',
              'SEPAC': 'Southeast Purdue Agricultural Center (Jennings)', 'SWPAC': 'Southwest Purdue Agricultural Center (Knox)',
              'ARIARI': 'Río Ariari – El Castillo (Meta)'}
PL_ACTIVOS = list(PL_SITIOS)          # p. ej. ['ARIARI'] para correr solo Colombia
PL_ANIOS = [2021, 2022, 2023, 2024, 2025]
PL_UMBRAL_CLEAR = 80                  # % despejado mínimo de la escena
PL_MIN_COB = 99                       # % del AOI que debe cubrir la escena
PL_KM2 = (2 * BUFFER_M / 1000) ** 2   # costo de un recorte al AOI (9 km² con BUFFER_M = 1500)

# Calendario de cultivo. Indiana = tu campaña 1 abr – 31 oct (SOLO_CAMPANA) dividida por etapas del maíz.
# Ariari = semestres A y B según las fechas de siembra del ICA para el piedemonte del Meta.
PL_CALENDARIOS = {
    'INDIANA_MAIZ': {'Maíz': [
        ('Siembra', '04-01', '05-20'), ('Establecimiento', '05-21', '06-15'),      # VE–V5
        ('Vegetativo', '06-16', '07-20'),                                           # V6–VT
        ('Reproductivo', '07-21', '09-10'),                                         # R1–R5 · ventana mancha de asfalto
        ('Madurez', '09-11', '09-30'), ('Cosecha', '10-01', '10-31')]},
    'ARIARI': {
        'Semestre A': [('Siembra', '03-01', '04-30'), ('Establecimiento', '05-01', '05-31'), ('Vegetativo', '06-01', '06-30'),
                       ('Reproductivo', '07-01', '07-31'), ('Cosecha', '08-01', '09-15')],
        'Semestre B': [('Siembra', '08-15', '09-20'), ('Establecimiento', '09-21', '10-20'), ('Vegetativo', '10-21', '11-20'),
                       ('Reproductivo', '11-21', '12-20'), ('Cosecha', '12-21', '01-31')]},
}
PL_ORDEN = ['Siembra', 'Establecimiento', 'Vegetativo', 'Reproductivo', 'Madurez', 'Cosecha']
PL_COLOR = {'Siembra': '#d9c8a9', 'Establecimiento': '#e8f3c6', 'Vegetativo': '#b9e09a',
            'Reproductivo': '#ffd27f', 'Madurez': '#f2b38a', 'Cosecha': '#d6b4d9'}

def pl_ventanas(cal, campana, anio):
    etapas = PL_CALENDARIOS[cal][campana]
    m0, d0 = map(int, etapas[0][1].split('-'))
    def f(md):
        m, d = map(int, md.split('-'))
        return pd.Timestamp(anio + (1 if (m, d) < (m0, d0) else 0), m, d)
    return [(e, f(i), f(fn) + pd.Timedelta(hours=23, minutes=59, seconds=59)) for e, i, fn in etapas]

def pl_aoi(sitio):
    c = PL_SITIOS[sitio]
    x0, y0, x1, y1 = bbox_aoi(c['lat'], c['lon'])
    return {'type': 'Polygon', 'coordinates': [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]}
PL_AOIS = {s: pl_aoi(s) for s in PL_SITIOS}

def _pl_req(metodo, url, **kw):
    espera = 2
    for _ in range(8):
        r = getattr(PL_SES, metodo)(url, timeout=120, **kw)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(espera); espera = min(espera * 2, 60); continue
        if r.status_code in (401, 403):
            raise PermissionError('API key de Planet inválida o sin permisos')
        r.raise_for_status()
        return r.json()
    raise RuntimeError('Demasiados reintentos con la API de Planet')

def pl_buscar(aoi, ini, fin):
    filtro = {'type': 'AndFilter', 'config': [
        {'type': 'GeometryFilter', 'field_name': 'geometry', 'config': aoi},
        {'type': 'DateRangeFilter', 'field_name': 'acquired',
         'config': {'gte': ini.strftime('%Y-%m-%dT%H:%M:%SZ'), 'lte': fin.strftime('%Y-%m-%dT%H:%M:%SZ')}}]}
    resp = _pl_req('post', f'{PL_API}/quick-search?_page_size=250&_sort=acquired%20asc',
                   json={'item_types': ['PSScene'], 'filter': filtro})
    feats = []
    while True:
        feats += resp.get('features', [])
        sig = (resp.get('_links') or {}).get('_next')
        if not sig or not resp.get('features'):
            return feats
        resp = _pl_req('get', sig)

# ---- Prueba rápida: julio 2024 en PPAC y en ARIARI (no gasta cuota) ----
for s in ('PPAC', 'ARIARI'):
    n = len(pl_buscar(PL_AOIS[s], pd.Timestamp('2024-07-01'), pd.Timestamp('2024-07-31 23:59:59')))
    print(f'✅ Prueba {s}: {n} escenas PlanetScope en julio de 2024')

# %% [P2]
# Bandas, resolución e índices posibles con PlanetScope
PL_BANDAS = pd.DataFrame([
    ('Azul costero (Coastal Blue)', '431–452', 443, 1, '—', '—', '—'),
    ('Azul (Blue)', '465–515', 490, 2, 1, '455–515', '464–517'),
    ('Verde I (Green I)', '513–549', 531, 3, '—', '—', '—'),
    ('Verde (Green)', '547–583', 565, 4, 2, '500–590', '547–585'),
    ('Amarillo (Yellow)', '600–620', 610, 5, '—', '—', '—'),
    ('Rojo (Red)', '650–680', 665, 6, 3, '590–670', '650–682'),
    ('Borde rojo (Red Edge)', '697–713', 705, 7, '—', '—', '—'),
    ('Infrarrojo cercano (NIR)', '845–885', 865, 8, 4, '780–860', '846–888'),
], columns=['Banda', 'SuperDove 8b (nm)', 'Centro (nm)', 'N.º en archivo 8b', 'N.º en archivo 4b',
            'Dove Classic PS2 (nm)', 'Dove-R PS2.SD (nm)'])

PL_RESOLUCION = pd.DataFrame([
    ('GSD (píxel real en tierra)', '≈ 3,7–4,1 m según la altura del satélite (columna p_gsd)'),
    ('Píxel del producto ortorectificado', '3 m (columna p_pixel_resolution)'),
    ('Radiometría', '12 bits, entregado en 16 bits; reflectancia de superficie (SR) × 10 000'),
    ('Tamaño de escena', '≈ 25 × 11,5 km (SuperDove ≈ 32,5 × 19,6 km)'),
    ('Revisita', 'Casi diaria'),
    ('Máscara de calidad', 'UDM2: clear, snow, shadow, light haze, heavy haze, cloud, confidence, unusable'),
], columns=['Característica', 'Valor'])

PL_INDICES = pd.DataFrame([
    ('NDVI', '(NIR − Rojo) / (NIR + Rojo)', True, True, 'Vigor y biomasa; se satura con dosel cerrado'),
    ('GNDVI', '(NIR − Verde) / (NIR + Verde)', True, True, 'Clorofila; se satura menos que el NDVI'),
    ('EVI', '2,5·(NIR − R) / (NIR + 6R − 7,5·Azul + 1)', True, True, 'Dosel denso (vegetativo y reproductivo)'),
    ('EVI2', '2,5·(NIR − R) / (NIR + 2,4R + 1)', True, True, 'Como el EVI, sin la banda azul'),
    ('SAVI', '1,5·(NIR − R) / (NIR + R + 0,5)', True, True, 'Siembra y establecimiento (suelo visible)'),
    ('MSAVI2', '(2NIR+1 − √((2NIR+1)² − 8(NIR−R))) / 2', True, True, 'Cobertura temprana'),
    ('OSAVI', '(NIR − R) / (NIR + R + 0,16)', True, True, 'Vegetación con suelo de fondo'),
    ('NDWI', '(Verde − NIR) / (Verde + NIR)', True, True, 'Agua y encharcamiento (arroz de riego, río Ariari)'),
    ('VARI', '(Verde − R) / (Verde + R − Azul)', True, True, 'Fracción verde con bandas visibles'),
    ('CIgreen', 'NIR / Verde − 1', True, True, 'Clorofila del dosel'),
    ('NDRE', '(NIR − RedEdge) / (NIR + RedEdge)', False, True, '⭐ Clorofila y N; estrés temprano (mancha de asfalto)'),
    ('CIrededge', 'NIR / RedEdge − 1', False, True, '⭐ Clorofila sin saturar en dosel denso'),
    ('MTCI*', '(NIR − RedEdge) / (RedEdge − R)', False, True, 'Clorofila (aprox., una sola banda Red Edge)'),
    ('CCCI', 'NDRE / NDVI', False, True, 'Separa clorofila de biomasa'),
    ('PSRI*', '(R − Azul) / RedEdge', False, True, '⭐ Senescencia y pérdida de clorofila (avance de lesiones)'),
    ('PRI*', '(Verde I − Verde) / (Verde I + Verde)', False, True, 'Estrés fotosintético (bandas anchas: con cautela)'),
    ('NDMI / NBR / LST', 'requieren SWIR o térmico', False, False, '❌ No posible: usa Sentinel-2, Landsat o EnMAP'),
], columns=['Índice', 'Fórmula (bandas PlanetScope)', '4 bandas', '8 bandas (SuperDove)', 'Utilidad'])
PL_IND_4B = ', '.join(PL_INDICES[PL_INDICES['4 bandas']]['Índice'])
PL_IND_8B = ', '.join(PL_INDICES[PL_INDICES['8 bandas (SuperDove)']]['Índice'])

print('BANDAS PLANETSCOPE'); display(PL_BANDAS)
print('RESOLUCIÓN'); display(PL_RESOLUCION)
print('ÍNDICES (* = adaptado a PlanetScope · ⭐ = más útiles para mancha de asfalto)'); display(PL_INDICES)
for n, d in (('bandas', PL_BANDAS), ('resolucion', PL_RESOLUCION), ('indices', PL_INDICES)):
    d.to_csv(os.path.join(CARPETAS['tablas'], f'REFERENCIA_PLANETSCOPE_{n}.csv'), index=False, encoding='utf-8-sig')

def pl_calcular_indices(arr, n_bandas):
    """Usar después de descargar: arr = rasterio.open(ruta).read().astype(float) / 10000 (reflectancia SR)."""
    if n_bandas == 8:
        cb, b, g1, g, y, r, re, nir = arr[:8]
    else:
        (b, g, r, nir), re, g1 = arr[:4], None, None
    e = 1e-9
    out = {'NDVI': (nir - r) / (nir + r + e), 'GNDVI': (nir - g) / (nir + g + e),
           'EVI': 2.5 * (nir - r) / (nir + 6 * r - 7.5 * b + 1), 'EVI2': 2.5 * (nir - r) / (nir + 2.4 * r + 1),
           'SAVI': 1.5 * (nir - r) / (nir + r + 0.5), 'NDWI': (g - nir) / (g + nir + e), 'CIgreen': nir / (g + e) - 1}
    if re is not None:
        out.update({'NDRE': (nir - re) / (nir + re + e), 'CIrededge': nir / (re + e) - 1,
                    'MTCI': (nir - re) / (re - r + e), 'PSRI': (r - b) / (re + e), 'PRI': (g1 - g) / (g1 + g + e)})
        out['CCCI'] = out['NDRE'] / (out['NDVI'] + e)
    return out

# %% [P3]
# Inventario de la temporada de cultivo con TODOS los metadatos (queda guardado en Drive)
PL_FORZAR = False
PL_RUTA_INV = os.path.join(CARPETAS['tablas'], 'INVENTARIO_PLANET_TEMPORADA_CULTIVO.csv')

def _pl_en_anillo(x, y, a):
    dentro, j = False, len(a) - 1
    for i in range(len(a)):
        if (a[i][1] > y) != (a[j][1] > y) and x < (a[j][0] - a[i][0]) * (y - a[i][1]) / ((a[j][1] - a[i][1]) or 1e-15) + a[i][0]:
            dentro = not dentro
        j = i
    return dentro

def pl_cobertura(aoi, g, n=25):
    polys = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates'] if g['type'] == 'MultiPolygon' else []
    xs = [p[0] for p in aoi['coordinates'][0]]; ys = [p[1] for p in aoi['coordinates'][0]]
    pts = [(min(xs) + (max(xs) - min(xs)) * (i + .5) / n, min(ys) + (max(ys) - min(ys)) * (j + .5) / n)
           for i in range(n) for j in range(n)]
    dentro = sum(any(_pl_en_anillo(x, y, p[0]) and not any(_pl_en_anillo(x, y, h) for h in p[1:]) for p in polys) for x, y in pts)
    return round(100 * dentro / len(pts), 1)

def _pl_fila(ft, sitio, campana, anio, etapa, t):
    p = ft.get('properties', {}) or {}
    assets = ft.get('assets', []) or []
    perms = ft.get('_permissions', []) or []
    a = set(assets)
    nb = 8 if {'ortho_analytic_8b_sr', 'ortho_analytic_8b'} & a else 4 if {'ortho_analytic_4b_sr', 'ortho_analytic_4b'} & a \
        else (8 if p.get('instrument') == 'PSB.SD' else 3)
    fila = {'sitio': sitio, 'region': PL_SITIOS[sitio]['region'], 'campana': campana, 'anio': anio, 'etapa': etapa,
            'fecha': t.strftime('%Y-%m-%d'), 'hora_utc': t.strftime('%H:%M:%S'), 'doy': t.dayofyear,
            'item_id': ft.get('id'), 'cobertura_aoi_pct': pl_cobertura(PL_AOIS[sitio], ft['geometry']),
            'n_bandas': nb, 'tiene_8b_sr': 'ortho_analytic_8b_sr' in a, 'tiene_4b_sr': 'ortho_analytic_4b_sr' in a,
            'tiene_udm2': 'ortho_udm2' in a, 'descargable': any(x.endswith(':download') for x in perms),
            'indices_posibles': PL_IND_8B if nb == 8 else PL_IND_4B,
            'assets': ';'.join(sorted(assets)), 'huella_geojson': json.dumps(ft.get('geometry'))}
    for k, v in p.items():                       # TODOS los metadatos de Planet (prefijo p_)
        fila[f'p_{k}'] = json.dumps(v) if isinstance(v, (list, dict)) else v
    return fila

def pl_inventario(forzar=PL_FORZAR):
    if os.path.exists(PL_RUTA_INV) and not forzar:
        print('⚡ Inventario Planet cargado desde Drive')
        return pd.read_csv(PL_RUTA_INV, low_memory=False)
    filas = []
    for sitio in PL_ACTIVOS:
        cal = PL_SITIOS[sitio]['calendario']
        for campana in PL_CALENDARIOS[cal]:
            for anio in PL_ANIOS:
                vs = pl_ventanas(cal, campana, anio)
                if vs[0][1] > pd.Timestamp.now():
                    continue
                feats = pl_buscar(PL_AOIS[sitio], vs[0][1], vs[-1][2])
                with open(os.path.join(CARPETAS['planet'], 'respuestas_api', f'{sitio}_{campana.replace(" ", "")}_{anio}.json'), 'w') as f:
                    json.dump(feats, f)
                n = 0
                for ft in feats:
                    t = pd.to_datetime(ft['properties']['acquired'], utc=True).tz_localize(None)
                    etapa = next((e for e, a, b in vs if a <= t <= b), None)
                    if etapa:
                        filas.append(_pl_fila(ft, sitio, campana, anio, etapa, t)); n += 1
                print(f'{sitio:7s} {campana:11s} {anio}: {n:5d} escenas ({vs[0][1]:%d %b %Y} → {vs[-1][2]:%d %b %Y})')
    df = pd.DataFrame(filas)
    df.to_csv(PL_RUTA_INV, index=False, encoding='utf-8-sig')
    print(f'✅ {len(df)} escenas guardadas en Drive')
    return df

PL_INV = pl_inventario()
_clear = pd.to_numeric(PL_INV['p_clear_percent'], errors='coerce')
_nub = pd.to_numeric(PL_INV['p_cloud_cover'], errors='coerce')
PL_INV['clear_pct'] = _clear
PL_INV['nubes_pct'] = _nub * 100
PL_INV['despejada'] = (PL_INV['cobertura_aoi_pct'] >= PL_MIN_COB) & (
    _clear.ge(PL_UMBRAL_CLEAR) | (_clear.isna() & _nub.le(1 - PL_UMBRAL_CLEAR / 100)))
print(f"\nTotal: {len(PL_INV)} escenas | despejadas y con AOI completo: {int(PL_INV['despejada'].sum())}")

# %% [P4]
# Ficha completa de CADA ÁREA: todos los datos resumidos + detalle por etapa
def _rango(serie, dec=1):
    s = pd.to_numeric(serie, errors='coerce').dropna()
    return f'{s.min():.{dec}f} – {s.max():.{dec}f}' if len(s) else '—'

def pl_ficha_area(sitio):
    d = PL_INV[PL_INV.sitio == sitio]
    c = PL_SITIOS[sitio]
    print('=' * 100)
    print(f"📍 {sitio} — {PL_NOMBRES.get(sitio, '')} | {c['region']} | lat {c['lat']}, lon {c['lon']}")
    print(f"   AOI {2 * BUFFER_M / 1000:.0f} × {2 * BUFFER_M / 1000:.0f} km = {PL_KM2:.0f} km² | campañas: {list(PL_CALENDARIOS[c['calendario']])}")
    print('=' * 100)
    if d.empty:
        print('Sin escenas'); return
    inst = d['p_instrument'].value_counts().to_dict()
    ficha = pd.DataFrame([
        ('Escenas en temporada', len(d)),
        ('Fechas con imagen', d.fecha.nunique()),
        ('Fechas despejadas con AOI completo', d[d.despejada].fecha.nunique()),
        ('Fechas despejadas con 8 bandas', d[d.despejada & (d.n_bandas == 8)].fecha.nunique()),
        ('Escenas que cubren todo el AOI', int((d.cobertura_aoi_pct >= PL_MIN_COB).sum())),
        ('Primera / última fecha', f'{d.fecha.min()} / {d.fecha.max()}'),
        ('Sensores (instrument)', ', '.join(f'{k}: {v}' for k, v in inst.items())),
        ('% de escenas con 8 bandas', f"{100 * (d.n_bandas == 8).mean():.0f} %"),
        ('Satélites distintos', d['p_satellite_id'].nunique() if 'p_satellite_id' in d else '—'),
        ('GSD (m)', _rango(d.get('p_gsd'), 2)),
        ('Píxel del producto (m)', _rango(d.get('p_pixel_resolution'), 0)),
        ('Nubosidad de escena (%)', f"media {d.nubes_pct.mean():.0f} | rango {_rango(d.nubes_pct, 0)}"),
        ('% despejado de escena', f"media {d.clear_pct.mean():.0f} | rango {_rango(d.clear_pct, 0)}"),
        ('Neblina ligera / densa (%)', f"{pd.to_numeric(d.get('p_light_haze_percent'), errors='coerce').mean():.1f} / "
                                        f"{pd.to_numeric(d.get('p_heavy_haze_percent'), errors='coerce').mean():.1f}"),
        ('Sombra (%) media', f"{pd.to_numeric(d.get('p_shadow_percent'), errors='coerce').mean():.1f}"),
        ('Elevación solar (°)', _rango(d.get('p_sun_elevation'))),
        ('Ángulo de vista (°)', _rango(d.get('p_view_angle'))),
        ('Hora de toma (UTC)', f'{d.hora_utc.min()} – {d.hora_utc.max()}'),
        ('Calidad (quality_category)', ', '.join(f'{k}: {v}' for k, v in d.get('p_quality_category', pd.Series(dtype=str)).value_counts().items())),
        ('Escenas descargables con tu cuenta', int(d.descargable.sum())),
    ], columns=['Dato', 'Valor'])
    display(ficha)
    # Por campaña, año y etapa
    filas = []
    for campana, etapas in PL_CALENDARIOS[c['calendario']].items():
        for anio in PL_ANIOS:
            for etapa, ini, fin in etapas:
                g = d[(d.campana == campana) & (d.anio == anio) & (d.etapa == etapa)]
                ok = g[g.despejada]
                filas.append({'campaña': campana, 'año': anio, 'etapa': etapa, 'ventana': f'{ini} → {fin}',
                              'escenas': len(g), 'fechas': g.fecha.nunique(), 'despejadas': ok.fecha.nunique(),
                              'despejadas_8b': ok[ok.n_bandas == 8].fecha.nunique(),
                              'nubes_media_%': round(g.nubes_pct.mean(), 0) if len(g) else np.nan,
                              'fechas despejadas': ', '.join(pd.to_datetime(sorted(ok.fecha.unique())).strftime('%d/%m'))})
    det = pd.DataFrame(filas)
    display(det.style.hide(axis='index').background_gradient(subset=['despejadas', 'despejadas_8b'], cmap='YlGn')
            .set_caption(f'{sitio}: imágenes por etapa del cultivo'))
    return ficha.assign(sitio=sitio), det.assign(sitio=sitio)

PL_FICHAS, PL_RES = [], []
for s in PL_ACTIVOS:
    f, r = pl_ficha_area(s)
    PL_FICHAS.append(f); PL_RES.append(r)
PL_FICHAS = pd.concat(PL_FICHAS, ignore_index=True)
PL_RES = pd.concat(PL_RES, ignore_index=True)
PL_RES.to_csv(os.path.join(CARPETAS['tablas'], 'PLANET_RESUMEN_POR_ETAPA.csv'), index=False, encoding='utf-8-sig')

# %% [P5]
# Gráfica: fechas despejadas por etapa (mapa de calor). Número = despejadas · (entre paréntesis) = fechas totales
def pl_heatmap_etapas():
    fig, axes = plt.subplots(len(PL_ACTIVOS), 1, figsize=(12, 2.6 * len(PL_ACTIVOS) + 1), squeeze=False)
    for ax, s in zip(axes[:, 0], PL_ACTIVOS):
        r = PL_RES[PL_RES.sitio == s].copy()
        r['fila'] = r['campaña'] + ' · ' + r['año'].astype(str)
        cols = [e for e in PL_ORDEN if e in r.etapa.unique()]
        v = r.pivot_table(index='fila', columns='etapa', values='despejadas', aggfunc='sum').reindex(columns=cols)
        t = r.pivot_table(index='fila', columns='etapa', values='fechas', aggfunc='sum').reindex(columns=cols)
        sns.heatmap(v, annot=v.astype(int).astype(str) + '\n(' + t.astype(int).astype(str) + ')', fmt='', cmap='YlGn',
                    vmin=0, linewidths=.5, cbar_kws={'label': 'fechas despejadas'}, ax=ax)
        ax.set_title(f"{s} — {PL_NOMBRES.get(s, '')}", loc='left', fontsize=11); ax.set_xlabel(''); ax.set_ylabel('')
    fig.suptitle(f'PlanetScope: fechas despejadas (≥{PL_UMBRAL_CLEAR}% y AOI completo) por etapa del cultivo', fontsize=13, y=1.0)
    plt.tight_layout(rect=(0, 0, 1, 0.985))
    plt.savefig(os.path.join(CARPETAS['figuras'], 'planet_heatmap_etapas.png'), dpi=200, bbox_inches='tight')
    plt.show()

pl_heatmap_etapas()

# %% [P6]
# Gráfica: línea de tiempo por área (fondo = etapa · ● 4 bandas · ▲ 8 bandas · relleno = despejada)
def pl_linea_tiempo(sitio):
    cal = PL_SITIOS[sitio]['calendario']
    combos = [(c, a) for c in PL_CALENDARIOS[cal] for a in PL_ANIOS if pl_ventanas(cal, c, a)[0][1] <= pd.Timestamp.now()]
    fig, axes = plt.subplots(len(combos), 1, figsize=(15, 1.25 * len(combos) + 1.5), squeeze=False)
    d0 = PL_INV[PL_INV.sitio == sitio].copy()
    d0['t'] = pd.to_datetime(d0.fecha)
    d0 = d0.sort_values(['despejada', 'clear_pct', 'n_bandas'], ascending=False).drop_duplicates(['campana', 'fecha'])
    for ax, (camp, anio) in zip(axes[:, 0], combos):
        vs = pl_ventanas(cal, camp, anio)
        for e, a, b in vs:
            ax.axvspan(a, b, color=PL_COLOR.get(e, '#eee'), zorder=0)
            ax.text(a + (b - a) / 2, 1.02, e, transform=ax.get_xaxis_transform(), ha='center', va='bottom', fontsize=7)
        d = d0[(d0.campana == camp) & (d0.anio == anio)]
        for nb, mk in ((4, 'o'), (8, '^')):
            ok = d[(d.n_bandas == nb) & d.despejada]; no = d[(d.n_bandas == nb) & ~d.despejada]
            ax.scatter(no.t, [0] * len(no), marker=mk, s=28, facecolors='none', edgecolors='#999', zorder=2)
            ax.scatter(ok.t, [0] * len(ok), marker=mk, s=60, color='#1b7837' if nb == 4 else '#2166ac', zorder=3)
        ax.set_xlim(vs[0][1], vs[-1][2]); ax.set_yticks([])
        ax.set_ylabel(f'{camp}\n{anio}', rotation=0, ha='right', va='center', fontsize=9)
        ax.xaxis.set_major_locator(mdates.MonthLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
        ax.text(1.005, .5, f'{int(d.despejada.sum())} desp.\n{len(d)} fechas', transform=ax.transAxes, fontsize=8, va='center')
    ley = [Line2D([0], [0], marker='o', color='w', markerfacecolor='#1b7837', ms=8, label='Despejada · 4 bandas'),
           Line2D([0], [0], marker='^', color='w', markerfacecolor='#2166ac', ms=9, label='Despejada · 8 bandas (Red Edge)'),
           Line2D([0], [0], marker='o', color='w', markerfacecolor='none', markeredgecolor='#999', ms=7, label='Nubosa / no cubre el AOI')]
    ley += [Patch(color=PL_COLOR[e], label=e) for e in PL_ORDEN if any(e == x[0] for et in PL_CALENDARIOS[cal].values() for x in et)]
    fig.legend(handles=ley, loc='lower center', ncol=5, fontsize=8, bbox_to_anchor=(.5, -0.01))
    fig.suptitle(f"{sitio} — {PL_NOMBRES.get(sitio, '')}: PlanetScope por etapa del cultivo", fontsize=13)
    plt.tight_layout(rect=(0, .05, .96, .97))
    plt.savefig(os.path.join(CARPETAS['figuras'], f'planet_linea_tiempo_{sitio}.png'), dpi=200, bbox_inches='tight')
    plt.show()

for s in PL_ACTIVOS:
    pl_linea_tiempo(s)

# %% [P7]
# Gráfica: fechas despejadas por mes (solo temporada de cultivo)
def pl_mensual():
    d = PL_INV[PL_INV.despejada].drop_duplicates(['sitio', 'fecha']).copy()
    f = pd.to_datetime(d.fecha)
    t = d.assign(mes=f.dt.month, anio_cal=f.dt.year).pivot_table(index=['sitio', 'anio_cal'], columns='mes', values='fecha',
                                                                  aggfunc='count', fill_value=0).reindex(columns=range(1, 13), fill_value=0)
    t.columns = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    plt.figure(figsize=(12, 0.35 * len(t) + 1.5))
    sns.heatmap(t, annot=True, fmt='d', cmap='YlGnBu', linewidths=.3, cbar_kws={'label': 'fechas despejadas'})
    plt.title('PlanetScope: fechas despejadas por mes (solo temporada de cultivo)'); plt.ylabel('')
    plt.tight_layout()
    plt.savefig(os.path.join(CARPETAS['figuras'], 'planet_distribucion_mensual.png'), dpi=200, bbox_inches='tight')
    plt.show()
    t.to_csv(os.path.join(CARPETAS['tablas'], 'PLANET_DISTRIBUCION_MENSUAL.csv'), encoding='utf-8-sig')
    return t

PL_MENSUAL = pl_mensual()

# %% [P8]
# Mejores escenas por etapa (candidatas a descargar) y costo en km² de tu cuota
PL_N_POR_ETAPA = 2

def pl_mejores(n=PL_N_POR_ETAPA):
    d = PL_INV[PL_INV.cobertura_aoi_pct >= PL_MIN_COB].sort_values(['despejada', 'clear_pct', 'n_bandas'], ascending=False)
    d = d.drop_duplicates(['sitio', 'campana', 'fecha'])
    m = d.groupby(['sitio', 'campana', 'anio', 'etapa'], sort=False).head(n).copy()
    m['km2_recorte'] = PL_KM2
    m['_o'] = m.etapa.map({e: i for i, e in enumerate(PL_ORDEN)})
    cols = ['sitio', 'campana', 'anio', 'etapa', 'fecha', 'item_id', 'despejada', 'clear_pct', 'nubes_pct',
            'p_instrument', 'n_bandas', 'tiene_8b_sr', 'tiene_udm2', 'descargable', 'km2_recorte']
    return m.sort_values(['sitio', 'campana', 'anio', '_o', 'fecha'])[cols]

PL_MEJORES = pl_mejores()
PL_MEJORES.to_csv(os.path.join(CARPETAS['tablas'], 'PLANET_MEJORES_ESCENAS_POR_ETAPA.csv'), index=False, encoding='utf-8-sig')
display(PL_MEJORES)
_tot = PL_MEJORES.km2_recorte.sum()
print(f'Total: {len(PL_MEJORES)} escenas × {PL_KM2:.0f} km² = {_tot:,.0f} km² → ≈ {math.ceil(_tot / 3000)} mes(es) de cuota (3.000 km²/mes)')
display(PL_MEJORES.groupby('sitio').km2_recorte.agg(escenas='count', km2='sum'))

# %% [P9]
# Vista previa: mejor imagen de cada etapa recortada al AOI (color natural). No gasta km², solo "scene tiles".
PL_ZOOM = 15   # 16 = más detalle

def _pl_xy(lat, lon, z):
    n = 2 ** z
    return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n

def pl_recorte(item_id, sitio, z=PL_ZOOM):
    ring = PL_AOIS[sitio]['coordinates'][0]
    lons = [p[0] for p in ring]; lats = [p[1] for p in ring]
    x0, y0 = _pl_xy(max(lats), min(lons), z); x1, y1 = _pl_xy(min(lats), max(lons), z)
    tx, ty = range(int(x0), int(x1) + 1), range(int(y0), int(y1) + 1)
    lienzo = Image.new('RGBA', (256 * len(tx), 256 * len(ty)))
    for i, x in enumerate(tx):
        for j, y in enumerate(ty):
            r = PL_SES.get(f'https://tiles.planet.com/data/v1/PSScene/{item_id}/{z}/{x}/{y}.png', timeout=60)
            if r.status_code == 200:
                lienzo.paste(Image.open(io.BytesIO(r.content)).convert('RGBA'), (256 * i, 256 * j))
    return lienzo.crop((int((x0 - tx[0]) * 256), int((y0 - ty[0]) * 256), int((x1 - tx[0]) * 256), int((y1 - ty[0]) * 256)))

def pl_vista_previa(sitio, anio, campana=None):
    campana = campana or list(PL_CALENDARIOS[PL_SITIOS[sitio]['calendario']])[0]
    sel_ = PL_MEJORES[(PL_MEJORES.sitio == sitio) & (PL_MEJORES.anio == anio) & (PL_MEJORES.campana == campana)].drop_duplicates('etapa')
    if sel_.empty:
        print('Sin escenas para esa combinación'); return
    fig, axes = plt.subplots(1, len(sel_), figsize=(4.2 * len(sel_), 4.8), squeeze=False)
    for ax, (_, r) in zip(axes[0], sel_.iterrows()):
        try:
            img = pl_recorte(r.item_id, sitio)
            ax.imshow(img); ax.plot(img.width / 2, img.height / 2, '+', color='red', ms=14, mew=2)
        except Exception as e:
            ax.text(.5, .5, f'Error\n{e}', ha='center', va='center', transform=ax.transAxes)
        ax.set_title(f"{r.etapa}\n{r.fecha} · {'✓' if r.despejada else '☁'} despejado {r.clear_pct:.0f}%\n{r.p_instrument} · {r.n_bandas} bandas", fontsize=9)
        ax.axis('off')
    fig.suptitle(f'{sitio} · {campana} {anio} — mejor imagen PlanetScope por etapa (+ = sitio)', fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(CARPETAS['figuras'], f"planet_preview_{sitio}_{campana.replace(' ', '')}_{anio}.png"), dpi=150, bbox_inches='tight')
    plt.show()

# Cambia sitio, año y campaña (Ariari: 'Semestre A' o 'Semestre B')
pl_vista_previa('PPAC', 2024)
pl_vista_previa('ARIARI', 2024, 'Semestre A')

# %% [P10]
# PlanetScope dentro de TUS gráficas y tablas combinadas (disponibilidad de todos los sensores) + Excel
CATALOGO['PlanetScope'] = {'Tipo': 'Multiespectral óptico (constelación)', 'Resolución': '3 m (GSD ≈ 3,7–4,1 m)',
                           'Espectral': '4 bandas (Dove) / 8 bandas con Red Edge (SuperDove)',
                           'Revisita (aprox.)': 'Casi diaria', 'Fuente': 'Planet E&R (Data API)'}

if '_unificar_sin_planet' not in globals():
    _unificar_sin_planet = _unificar_disponibilidad

def _unificar_disponibilidad():
    d = _unificar_sin_planet()
    p = PL_INV[PL_INV.sitio.isin(SITIOS) & (PL_INV.cobertura_aoi_pct >= PL_MIN_COB)]
    p = p.sort_values('nubes_pct').drop_duplicates(['sitio', 'fecha'])
    p = pd.DataFrame({'sitio': p.sitio, 'fecha': p.fecha, 'sensor': 'PlanetScope (3 m)',
                      'nube_pct': p.nubes_pct, 'cubre': True, 'fecha_dt': pd.to_datetime(p.fecha)})
    return pd.concat([d, p[d.columns]], ignore_index=True)

# Vuelve a dibujar tus gráficas y tablas combinadas, ahora con PlanetScope
DISP = disponibilidad_todos_sensores()
DISP_2024 = disponibilidad_anio(2024)
TABLA_DET, DISP_TODOS = tabla_resumen_todos()
display(TABLA_DET[TABLA_DET.Sensor.str.startswith('PlanetScope')])

# Excel con todo lo de Planet
PL_XLSX = os.path.join(CARPETAS['tablas'], 'INVENTARIO_PLANET_TEMPORADA_CULTIVO.xlsx')
PL_CAL = pd.DataFrame([(k, c, e, i, f) for k, v in PL_CALENDARIOS.items() for c, et in v.items() for e, i, f in et],
                      columns=['calendario', 'campaña', 'etapa', 'inicio MM-DD', 'fin MM-DD'])
with pd.ExcelWriter(PL_XLSX) as xw:
    PL_FICHAS.to_excel(xw, sheet_name='fichas_areas', index=False)
    PL_RES.to_excel(xw, sheet_name='resumen_etapa', index=False)
    PL_MEJORES.to_excel(xw, sheet_name='mejores_por_etapa', index=False)
    PL_MENSUAL.reset_index().to_excel(xw, sheet_name='mensual', index=False)
    PL_INV.drop(columns=['huella_geojson']).to_excel(xw, sheet_name='escenas_metadatos', index=False)
    PL_BANDAS.to_excel(xw, sheet_name='bandas', index=False)
    PL_INDICES.to_excel(xw, sheet_name='indices', index=False)
    PL_RESOLUCION.to_excel(xw, sheet_name='resolucion', index=False)
    PL_CAL.to_excel(xw, sheet_name='calendario', index=False)
print('✅ Excel en Drive:', PL_XLSX)

with open(os.path.join(CARPETAS['tablas'], 'PLANET_HUELLAS_DESPEJADAS.geojson'), 'w') as f:
    json.dump({'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'geometry': json.loads(r.huella_geojson),
         'properties': {'sitio': r.sitio, 'campana': r.campana, 'anio': int(r.anio), 'etapa': r.etapa, 'fecha': r.fecha,
                        'item_id': r.item_id, 'clear_pct': None if pd.isna(r.clear_pct) else float(r.clear_pct), 'n_bandas': int(r.n_bandas)}}
        for _, r in PL_INV[PL_INV.despejada].iterrows()]}, f)
print('✅ GeoJSON de huellas (QGIS) en Drive')
print('\nCita obligatoria: Planet Team (2026). Planet Application Program Interface: In Space for Life on Earth. San Francisco, CA. https://api.planet.com')

# ===== COMPLETAR INVENTARIO PLANET: río Ariari (2021–2025) + Indiana 2025 =====
import os, json, time, math, getpass, glob, requests
import pandas as pd

BUFFER_COMP = 500          # mismo AOI que tu inventario actual (1 × 1 km). Pon 1500 para 3 × 3 km
UMBRAL, MIN_COB = 80, 99
KEY = os.environ.get('PL_API_KEY') or getpass.getpass('API key de Planet: ').strip()
os.environ['PL_API_KEY'] = KEY
S = requests.Session(); S.auth = (KEY, '')

CAL = {'INDIANA': {'Maíz': [('Siembra', '04-01', '05-20'), ('Establecimiento', '05-21', '06-15'), ('Vegetativo', '06-16', '07-20'),
                            ('Reproductivo', '07-21', '09-10'), ('Madurez', '09-11', '09-30'), ('Cosecha', '10-01', '10-31')]},
       'ARIARI': {'Semestre A': [('Siembra', '03-01', '04-30'), ('Establecimiento', '05-01', '05-31'), ('Vegetativo', '06-01', '06-30'),
                                 ('Reproductivo', '07-01', '07-31'), ('Cosecha', '08-01', '09-15')],
                  'Semestre B': [('Siembra', '08-15', '09-20'), ('Establecimiento', '09-21', '10-20'), ('Vegetativo', '10-21', '11-20'),
                                 ('Reproductivo', '11-21', '12-20'), ('Cosecha', '12-21', '01-31')]}}
# (sitio, latitud, longitud, calendario, años)
TAREAS = [('ARIARI', 3.650321, -73.782597, 'ARIARI', [2021, 2022, 2023, 2024, 2025]),
          ('PPAC', 41.4432, -86.9301, 'INDIANA', [2025]), ('RICE', 41.3269, -86.8028, 'INDIANA', [2025]),
          ('SEPAC', 39.0357, -85.5291, 'INDIANA', [2025]), ('SWPAC', 38.7372, -87.4845, 'INDIANA', [2025])]

def ventanas(cal, camp, anio):
    et = CAL[cal][camp]; m0, d0 = map(int, et[0][1].split('-'))
    f = lambda md: pd.Timestamp(anio + (1 if tuple(map(int, md.split('-'))) < (m0, d0) else 0), *map(int, md.split('-')))
    return [(e, f(i), f(fn) + pd.Timedelta(hours=23, minutes=59, seconds=59)) for e, i, fn in et]

def aoi(lat, lon, b=BUFFER_COMP):
    dy = b / 111320; dx = b / (111320 * math.cos(math.radians(lat)))
    return {'type': 'Polygon', 'coordinates': [[[lon-dx, lat-dy], [lon+dx, lat-dy], [lon+dx, lat+dy], [lon-dx, lat+dy], [lon-dx, lat-dy]]]}

def req(m, url, **kw):
    for i in range(8):
        r = getattr(S, m)(url, timeout=120, **kw)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 ** min(i + 1, 6))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError('Demasiados reintentos')

def buscar(g, a, b):
    flt = {'type': 'AndFilter', 'config': [{'type': 'GeometryFilter', 'field_name': 'geometry', 'config': g},
           {'type': 'DateRangeFilter', 'field_name': 'acquired', 'config': {'gte': f'{a:%Y-%m-%dT%H:%M:%SZ}', 'lte': f'{b:%Y-%m-%dT%H:%M:%SZ}'}}]}
    r = req('post', 'https://api.planet.com/data/v1/quick-search?_page_size=250', json={'item_types': ['PSScene'], 'filter': flt})
    out = []
    while True:
        out += r.get('features', [])
        nxt = (r.get('_links') or {}).get('_next')
        if not nxt or not r.get('features'):
            return out
        r = req('get', nxt)

def dentro(x, y, ring):
    c, j = False, len(ring) - 1
    for i in range(len(ring)):
        if (ring[i][1] > y) != (ring[j][1] > y) and x < (ring[j][0]-ring[i][0]) * (y-ring[i][1]) / ((ring[j][1]-ring[i][1]) or 1e-15) + ring[i][0]:
            c = not c
        j = i
    return c

def cobertura(a, g, n=20):
    polys = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
    xs = [p[0] for p in a['coordinates'][0]]; ys = [p[1] for p in a['coordinates'][0]]
    pts = [(min(xs) + (max(xs)-min(xs)) * (i+.5) / n, min(ys) + (max(ys)-min(ys)) * (j+.5) / n) for i in range(n) for j in range(n)]
    return round(100 * sum(any(dentro(x, y, p[0]) for p in polys) for x, y in pts) / len(pts), 1)

filas = []
for sitio, lat, lon, cal, anios in TAREAS:
    g = aoi(lat, lon)
    for camp in CAL[cal]:
        for anio in anios:
            vs = ventanas(cal, camp, anio)
            if vs[0][1] > pd.Timestamp.now():
                continue
            fts = buscar(g, vs[0][1], min(vs[-1][2], pd.Timestamp.now()))
            for ft in fts:
                p = ft['properties']; t = pd.to_datetime(p['acquired'], utc=True).tz_localize(None)
                et = next((e for e, a, b in vs if a <= t <= b), None)
                if not et:
                    continue
                a = set(ft.get('assets', []))
                nb = 8 if 'ortho_analytic_8b_sr' in a or p.get('instrument') == 'PSB.SD' else 4
                fila = {'sitio': sitio, 'campana': camp, 'anio': anio, 'etapa': et, 'fecha': f'{t:%Y-%m-%d}', 'hora_utc': f'{t:%H:%M:%S}',
                        'doy': t.dayofyear, 'item_id': ft['id'], 'cobertura_aoi_pct': cobertura(g, ft['geometry']), 'n_bandas': nb,
                        'tiene_8b_sr': 'ortho_analytic_8b_sr' in a, 'tiene_4b_sr': 'ortho_analytic_4b_sr' in a, 'tiene_udm2': 'ortho_udm2' in a,
                        'descargable': any(x.endswith(':download') for x in ft.get('_permissions', [])),
                        'huella_geojson': json.dumps(ft['geometry'])}
                fila.update({f'p_{k}': (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in p.items()})
                filas.append(fila)
            print(f'{sitio:7s} {camp:11s} {anio}: {len(fts):4d} escenas')

NUEVO = pd.DataFrame(filas)
NUEVO['clear_pct'] = pd.to_numeric(NUEVO['p_clear_percent'], errors='coerce')
NUEVO['nubes_pct'] = pd.to_numeric(NUEVO['p_cloud_cover'], errors='coerce') * 100
NUEVO['despejada'] = (NUEVO.cobertura_aoi_pct >= MIN_COB) & NUEVO.clear_pct.ge(UMBRAL)
print(f"\n✅ {len(NUEVO)} escenas nuevas | despejadas: {int(NUEVO.despejada.sum())}")
print(NUEVO.groupby(['sitio', 'campana', 'anio']).agg(escenas=('item_id', 'size'), fechas=('fecha', 'nunique'),
      fechas_despejadas=('fecha', lambda f: f[NUEVO.loc[f.index, 'despejada']].nunique())).to_string())

# Unir con tu inventario actual (PL_INV en memoria, o el Excel guardado)
if 'PL_INV' not in globals():
    xl = (glob.glob('/content/**/INVENTARIO_PLANET_TEMPORADA_CULTIVO.xlsx', recursive=True) or
          glob.glob('/content/drive/MyDrive/**/INVENTARIO_PLANET_TEMPORADA_CULTIVO.xlsx', recursive=True))
    PL_INV = pd.read_excel(xl[0], sheet_name='escenas_metadatos')
    print('Inventario anterior leído de', xl[0])
PL_INV = PL_INV[~PL_INV.item_id.isin(NUEVO.item_id) | ~PL_INV.sitio.isin(NUEVO.sitio)]
PL_INV = pd.concat([PL_INV, NUEVO], ignore_index=True)
PL_INV['despejada'] = PL_INV['despejada'].astype(str).eq('True')
PL_INV['anio'] = PL_INV['anio'].astype(int)
PL_INV.to_csv('INVENTARIO_PLANET_COMPLETO.csv', index=False, encoding='utf-8-sig')
print(f'✅ Inventario completo: {len(PL_INV)} escenas →', PL_INV.groupby('sitio').size().to_dict())
print('Ahora vuelve a ejecutar tus celdas de fichas, gráficas, mejores escenas y Excel.')

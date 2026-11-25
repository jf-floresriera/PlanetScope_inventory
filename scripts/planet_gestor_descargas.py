# =====================================================================================
#  PLANET · GESTOR DE DESCARGAS MES A MES (control de cuota)
#     %run -i /content/drive/MyDrive/Purdue_TarSpot_Project/PlanetScope_inventory/scripts/planet_gestor_descargas.py
#
#  1. Baja a Drive TODO lo que ya pediste (gratis: Planet cobra al hacer el pedido, no al descargar)
#  2. Arma la lista de escenas deseadas (la mejor escena despejada por sitio, año y etapa)
#  3. Documenta el estado de cada una: descargada / pedida sin bajar / fallida / por pedir
#  4. Planifica qué pedir cada mes sin pasarse de la cuota (mínimo 100 km² por escena en E&R Basic)
#  5. SOLO hace pedidos si PEDIR = True, y solo lo que cabe en la cuota que te queda este mes
# =====================================================================================
import os, glob, json, time, math, getpass, requests
import pandas as pd
try:
    display
except NameError:
    display = print

# ------------------------------- CONFIGURACIÓN -------------------------------
PEDIR              = False      # ⚠️ True = hace los pedidos de ESTE mes (gasta cuota). False = solo documenta y planifica
CUOTA_RESTANTE_HOY = 200        # km² que muestra HOY tu cuenta en "Remaining" (actualízalo antes de pedir)
CUOTA_MENSUAL      = 3000
KM2_POR_ESCENA     = 100        # E&R Basic "preferred clipping": mínimo 100 km² por escena aunque recortes menos
MARGEN_KM2         = 100        # reserva que nunca se gasta (por seguridad)
BUFFER_PEDIDO_M    = 4900       # recorte de 9,8 × 9,8 km ≈ 96 km²: cuesta lo mismo que 1 km² y trae más contexto
ANIOS_PRIORIDAD    = [2024, 2023, 2022, 2021, 2025]   # orden en que se piden los años
ESPERA_MAX_MIN     = 60

COORD = {'PPAC': (41.4432, -86.9301), 'RICE': (41.3269, -86.8028), 'SEPAC': (39.0357, -85.5291),
         'SWPAC': (38.7372, -87.4845), 'ARIARI': (3.650321, -73.782597)}
ETAPAS = ['Siembra', 'Establecimiento', 'Vegetativo', 'Reproductivo', 'Madurez', 'Cosecha']

def _gestor():
    # ---------- Drive ----------
    try:
        from google.colab import drive
        if not os.path.isdir('/content/drive/MyDrive'):
            drive.mount('/content/drive')
    except ImportError:
        pass
    base = '/content/drive/MyDrive/Purdue_TarSpot_Project' if os.path.isdir('/content/drive/MyDrive') \
        else globals().get('RUTA_BASE', './Purdue_TarSpot_Project')
    destino = os.path.join(base, '08_Planet_PlanetScope', 'imagenes_recortadas'); os.makedirs(destino, exist_ok=True)
    ruta_reg = os.path.join(destino, 'pedidos_planet.json')
    ruta_ctl = os.path.join(base, '08_Planet_PlanetScope', 'CONTROL_DESCARGAS_PLANET')
    print('📁 Drive:', destino)

    key = os.environ.get('PL_API_KEY') or getpass.getpass('API key de Planet: ').strip()
    os.environ['PL_API_KEY'] = key
    ses = requests.Session(); ses.auth = (key, '')
    URL = 'https://api.planet.com/compute/ops/orders/v2'

    def get_json(url):
        for i in range(6):
            r = ses.get(url, timeout=120)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** (i + 1)); continue
            return r.json()

    def descargar(det, sitio):
        carpeta = os.path.join(destino, sitio); os.makedirs(carpeta, exist_ok=True)
        n = 0
        for res in (det.get('_links') or {}).get('results') or []:
            arch = os.path.basename(res['name']); dst = os.path.join(carpeta, arch)
            if os.path.exists(dst) and os.path.getsize(dst) > 0:
                continue
            dl = ses.get(res['location'], stream=True, timeout=600)
            if dl.status_code != 200:
                print(f'   ❌ {arch}: HTTP {dl.status_code}'); continue
            with open(dst + '.part', 'wb') as f:
                for ch in dl.iter_content(1 << 20):
                    f.write(ch)
            os.replace(dst + '.part', dst); n += 1
        return n

    def sitio_de(nombre):
        p = nombre.split('_')
        return p[1] if len(p) > 2 and p[1] in COORD else 'otros'

    # ---------- 1) Todos los pedidos ya hechos → Drive (gratis) ----------
    print('\n1) PEDIDOS YA HECHOS EN TU CUENTA (descarga sin costo)')
    pedidos, j = [], get_json(URL)
    while j:
        pedidos += j.get('orders', [])
        nxt = (j.get('_links') or {}).get('next')
        j = get_json(nxt) if nxt else None
    reg = json.load(open(ruta_reg)) if os.path.exists(ruta_reg) else {}
    t0 = time.time()
    while any(p.get('state') in ('queued', 'running') for p in pedidos) and time.time() - t0 < ESPERA_MAX_MIN * 60:
        print('   ⏳ hay pedidos en proceso en Planet, espero 30 s…'); time.sleep(30)
        pedidos = [get_json(f"{URL}/{p['id']}") if p.get('state') in ('queued', 'running') else p for p in pedidos]
    nuevos = 0
    for p in pedidos:
        det = get_json(f"{URL}/{p['id']}")
        nombre = det.get('name', p['id']); sitio = sitio_de(nombre)
        ids = [i for x in det.get('products', []) for i in x.get('item_ids', [])]
        reg[det['id']] = {'nombre': nombre, 'sitio': sitio, 'estado': det.get('state'), 'creado': det.get('created_on', ''),
                          'ids': ids, 'mensaje': det.get('last_message', '')}
        if det.get('state') in ('success', 'partial'):
            nuevos += descargar(det, sitio)
    json.dump(reg, open(ruta_reg, 'w'), indent=1)
    print(f'   {len(pedidos)} pedidos · {nuevos} archivos nuevos guardados en Drive')

    # ---------- 2) Lista de escenas deseadas ----------
    inv = globals().get('PL_INV')
    copia = os.path.join(base, '08_Planet_PlanetScope', 'INVENTARIO_PLANET_COMPLETO.csv')
    if inv is None:                       # sesión nueva: buscar el inventario guardado en Drive
        cands = [copia] + glob.glob(os.path.join(base, '**', 'INVENTARIO_PLANET*.csv'), recursive=True) \
                + glob.glob(os.path.join(base, '**', 'INVENTARIO_PLANET*.xlsx'), recursive=True) \
                + glob.glob('/content/INVENTARIO_PLANET*.csv')
        cands = sorted({c for c in cands if os.path.exists(c)}, key=lambda c: (c != copia, -os.path.getmtime(c)))
        if not cands:
            print('\n⚠️ No encontré el inventario (PL_INV). Las descargas YA quedaron hechas; el control y el plan')
            print('   se generan cuando vuelvas a tener el inventario (corre antes las celdas del inventario Planet).')
            return None, None
        inv = pd.read_excel(cands[0], sheet_name='escenas_metadatos') if cands[0].endswith('.xlsx') else pd.read_csv(cands[0], low_memory=False)
        print(f'\n📄 Inventario leído de Drive: {cands[0]} ({len(inv)} escenas)')
    globals()['PL_INV'] = inv
    inv.to_csv(copia, index=False, encoding='utf-8-sig')      # copia de seguridad en Drive para la próxima sesión
    d = inv.copy()
    d['despejada'] = d['despejada'].astype(str).eq('True')
    d['anio'] = d['anio'].astype(int)
    d['n_bandas'] = pd.to_numeric(d['n_bandas'], errors='coerce').fillna(4)
    d['clear_pct'] = pd.to_numeric(d.get('clear_pct', d.get('p_clear_percent')), errors='coerce')
    d = d[d.despejada & (pd.to_numeric(d.cobertura_aoi_pct, errors='coerce') >= 99)]
    d = d.sort_values(['n_bandas', 'clear_pct'], ascending=False)
    lista = d.groupby(['sitio', 'campana', 'anio', 'etapa'], sort=False).head(1).copy()
    lista['_pa'] = lista.anio.map({a: i for i, a in enumerate(ANIOS_PRIORIDAD)}).fillna(99)
    lista['_pe'] = lista.etapa.map({e: i for i, e in enumerate(ETAPAS)})
    lista = lista.sort_values(['_pa', 'sitio', 'campana', '_pe']).reset_index(drop=True)
    lista['prioridad'] = range(1, len(lista) + 1)

    # ---------- 3) Estado de cada escena ----------
    def en_drive(i):
        return any(os.path.getsize(f) > 0 for f in glob.glob(os.path.join(destino, '**', f'{i}*AnalyticMS_SR*.tif'), recursive=True))
    estado_pedido = {}
    for oid, v in reg.items():
        for i in v['ids']:
            prev = estado_pedido.get(i)
            if prev is None or prev[1] == 'failed':
                estado_pedido[i] = (oid, v['estado'], v['creado'][:7])
    def estado(i):
        if en_drive(i):
            return '✅ descargada'
        if i in estado_pedido:
            e = estado_pedido[i][1]
            return '❌ pedido fallido' if e in ('failed', 'cancelled') else '⏳ pedida, falta bajar'
        return '🕒 por pedir'
    lista['estado'] = lista.item_id.map(estado)
    lista['id_pedido'] = lista.item_id.map(lambda i: estado_pedido.get(i, ('',))[0])
    lista['mes_pedido'] = lista.item_id.map(lambda i: estado_pedido.get(i, ('', '', ''))[2])
    lista['km2_cobrados'] = lista.estado.map(lambda e: 0 if e == '🕒 por pedir' else KM2_POR_ESCENA)
    # escenas pedidas que no están en la lista (p. ej. de pruebas anteriores)
    extra = [{'sitio': v['sitio'], 'item_id': i, 'estado': estado(i) + ' (fuera de la lista)', 'id_pedido': oid,
              'mes_pedido': v['creado'][:7], 'km2_cobrados': KM2_POR_ESCENA}
             for oid, v in reg.items() for i in v['ids'] if i not in set(lista.item_id)]

    # ---------- 4) Plan mes a mes ----------
    hoy = pd.Timestamp.now()
    mes = hoy.strftime('%Y-%m')
    # Control de cuota: recuerda cuánto declaraste y resta lo que el gestor pide después
    ruta_cuota = os.path.join(destino, 'control_cuota.json')
    cq = json.load(open(ruta_cuota)) if os.path.exists(ruta_cuota) else {}
    if cq.get('valor') != CUOTA_RESTANTE_HOY or cq.get('mes') != mes:
        valor = CUOTA_RESTANTE_HOY if cq.get('valor') != CUOTA_RESTANTE_HOY else CUOTA_MENSUAL   # mes nuevo → cuota completa
        cq = {'valor': CUOTA_RESTANTE_HOY, 'mes': mes, 'restante_base': valor, 'pedidos_gestor': {}}
        json.dump(cq, open(ruta_cuota, 'w'), indent=1)
    gastado = sum(km for oid, km in cq['pedidos_gestor'].items()
                  if reg.get(oid, {}).get('estado') not in ('failed', 'cancelled'))
    restante = cq['restante_base'] - gastado
    print(f"\n   Cuota estimada de {mes}: {restante} km² (declarado {cq['restante_base']} − {gastado} pedidos por el gestor desde entonces)")
    cap = {mes: max(restante - MARGEN_KM2, 0)}
    plan = []
    for i, r in lista.iterrows():
        if r.estado != '🕒 por pedir':
            plan.append(''); continue
        m = hoy
        while True:
            k = m.strftime('%Y-%m')
            cap.setdefault(k, CUOTA_MENSUAL - MARGEN_KM2)
            if cap[k] >= KM2_POR_ESCENA:
                cap[k] -= KM2_POR_ESCENA; plan.append(k); break
            m = (m + pd.offsets.MonthBegin(1))
    lista['mes_planeado'] = plan

    # ---------- 5) Pedidos de este mes (solo si PEDIR = True) ----------
    este_mes = lista[(lista.mes_planeado == hoy.strftime('%Y-%m'))]
    print(f"\n2) ESTE MES caben {len(este_mes)} escenas nuevas ({len(este_mes) * KM2_POR_ESCENA} km² de {restante} restantes, reserva {MARGEN_KM2})")
    if PEDIR and len(este_mes):
        for sitio, g in este_mes.groupby('sitio'):
            lat, lon = COORD[sitio]
            dy = BUFFER_PEDIDO_M / 111320; dx = BUFFER_PEDIDO_M / (111320 * math.cos(math.radians(lat)))
            aoi = {'type': 'Polygon', 'coordinates': [[[lon-dx, lat-dy], [lon+dx, lat-dy], [lon+dx, lat+dy], [lon-dx, lat+dy], [lon-dx, lat-dy]]]}
            cuerpo = {'name': f'TarSpot_{sitio}_{time.strftime("%Y%m%d_%H%M")}',
                      'products': [{'item_ids': g.item_id.tolist(), 'item_type': 'PSScene', 'product_bundle': 'analytic_8b_sr_udm2,analytic_sr_udm2'}],
                      'tools': [{'clip': {'aoi': aoi}}]}
            r = ses.post(URL, json=cuerpo, timeout=120)
            if r.status_code >= 400:
                print(f'   ❌ {sitio}: Planet rechazó el pedido ({r.status_code}) {r.text[:200]}'); continue
            oid = r.json()['id']
            reg[oid] = {'nombre': cuerpo['name'], 'sitio': sitio, 'estado': 'queued', 'creado': pd.Timestamp.now(tz='UTC').isoformat(), 'ids': g.item_id.tolist(), 'mensaje': ''}
            json.dump(reg, open(ruta_reg, 'w'), indent=1)          # anotado ANTES de esperar
            cq['pedidos_gestor'][oid] = len(g) * KM2_POR_ESCENA
            json.dump(cq, open(ruta_cuota, 'w'), indent=1)
            print(f'   📨 {sitio}: pedido {oid} con {len(g)} escenas (registrado)')
            t0 = time.time(); det = get_json(f'{URL}/{oid}')
            while det.get('state') in ('queued', 'running') and time.time() - t0 < ESPERA_MAX_MIN * 60:
                time.sleep(30); det = get_json(f'{URL}/{oid}')
            reg[oid]['estado'] = det.get('state'); json.dump(reg, open(ruta_reg, 'w'), indent=1)
            n = descargar(det, sitio) if det.get('state') in ('success', 'partial') else 0
            print(f"   {sitio}: estado {det.get('state')} · {n} archivos guardados" +
                  ('' if n else ' · si sigue en proceso, vuelve a correr este gestor más tarde (bajará sin costo)'))
        lista.loc[lista.mes_planeado == hoy.strftime('%Y-%m'), 'estado'] = lista.loc[lista.mes_planeado == hoy.strftime('%Y-%m'), 'item_id'].map(estado)
    elif len(este_mes):
        print('   (PEDIR = False: no se pidió nada. Cámbialo a True cuando quieras gastar esa cuota)')

    # ---------- 6) Documentar ----------
    cols = ['prioridad', 'sitio', 'campana', 'anio', 'etapa', 'fecha', 'item_id', 'n_bandas', 'clear_pct',
            'estado', 'id_pedido', 'mes_pedido', 'km2_cobrados', 'mes_planeado']
    ctl = pd.concat([lista[cols], pd.DataFrame(extra)], ignore_index=True)
    resumen = ctl.groupby('estado').agg(escenas=('item_id', 'size'), km2=('km2_cobrados', 'sum')).reset_index()
    meses = lista[lista.mes_planeado != ''].groupby('mes_planeado').agg(escenas=('item_id', 'size')).reset_index()
    meses['km2'] = meses.escenas * KM2_POR_ESCENA
    ctl.to_csv(ruta_ctl + '.csv', index=False, encoding='utf-8-sig')
    with pd.ExcelWriter(ruta_ctl + '.xlsx') as xw:
        resumen.to_excel(xw, sheet_name='resumen', index=False)
        meses.to_excel(xw, sheet_name='plan_por_mes', index=False)
        ctl.to_excel(xw, sheet_name='control_escenas', index=False)
        pd.DataFrame([{'id': k, **{kk: (', '.join(vv) if isinstance(vv, list) else vv) for kk, vv in v.items()}} for k, v in reg.items()]
                     ).to_excel(xw, sheet_name='pedidos', index=False)
    print('\n3) ESTADO DE LAS ESCENAS'); display(resumen)
    print('\n4) PLAN POR MES (lo que falta, sin pasarse de la cuota)'); display(meses)
    print(f'\n✅ Control guardado en Drive: {ruta_ctl}.xlsx / .csv')
    return ctl, meses

CONTROL_PLANET, PLAN_MESES = _gestor()

# =====================================================================================
#  PLANET · COMPOSICIONES DE COLOR DE TODAS LAS IMÁGENES GUARDADAS EN DRIVE (no gasta cuota)
#     %run -i /content/drive/MyDrive/Purdue_TarSpot_Project/PlanetScope_inventory/scripts/planet_composiciones.py
#  Ejecutar DESPUÉS de planet_gestor_descargas.py (con PEDIR = False), que baja las imágenes.
# =====================================================================================
import os, glob, re
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
try:
    display
except NameError:
    display = print

# Composiciones (número de banda en el archivo de 8 bandas SuperDove → R, G, B)
#  1 Azul costero · 2 Azul · 3 Verde I · 4 Verde · 5 Amarillo · 6 Rojo · 7 Red Edge · 8 NIR
COMPOSICIONES_8B = [
    ('Color natural',              (6, 4, 2), 'Como lo ve el ojo: suelo, rastrojo, agua, caminos'),
    ('Falso color infrarrojo',     (8, 6, 4), 'Vegetación sana en rojo intenso; estrés y suelo en tonos apagados'),
    ('Red Edge',                   (8, 7, 6), 'Diferencias de clorofila dentro del dosel (útil para estrés y enfermedad)'),
    ('Senescencia (RedEdge·Amarillo·Azul)', (7, 5, 2), 'Resalta el amarilleo y la pérdida de verde hacia madurez y cosecha'),
]
COMPOSICIONES_4B = [  # escenas de 4 bandas: 1 Azul · 2 Verde · 3 Rojo · 4 NIR
    ('Color natural',          (3, 2, 1), 'Como lo ve el ojo'),
    ('Falso color infrarrojo', (4, 3, 2), 'Vegetación sana en rojo intenso'),
]

def _composiciones():
    base = '/content/drive/MyDrive/Purdue_TarSpot_Project' if os.path.isdir('/content/drive/MyDrive') \
        else globals().get('RUTA_BASE', './Purdue_TarSpot_Project')
    carpeta = os.path.join(base, '08_Planet_PlanetScope', 'imagenes_recortadas')
    salida = os.path.join(base, '07_Figuras', 'Planet', 'composiciones'); os.makedirs(salida, exist_ok=True)
    import rasterio

    print('Composiciones que se generan (8 bandas):')
    display(pd.DataFrame([(n, '-'.join(map(str, b)), u) for n, b, u in COMPOSICIONES_8B], columns=['Composición', 'Bandas R-G-B', 'Para qué sirve']))

    inv = globals().get('PL_INV')
    info = {}
    if inv is not None:
        for _, r in inv.drop_duplicates('item_id').iterrows():
            info[r['item_id']] = (r.get('etapa', ''), r.get('fecha', ''))

    def estirar(arr, valido):
        """Estiramiento común a las 3 bandas (percentiles 2–98) + gamma suave: conserva los tonos reales."""
        v = arr[:, valido]
        lo, hi = (np.percentile(v, 2), np.percentile(v, 98)) if v.size else (0.0, 0.3)
        if hi - lo < 1e-4:
            lo, hi = 0.0, max(float(v.max()) if v.size else 0.3, 1e-3)
        out = np.clip((np.moveaxis(arr, 0, -1) - lo) / (hi - lo), 0, 1) ** (1 / 1.4)
        out[~valido] = 1.0       # sin dato en blanco
        return out.astype('float32')

    filas = []
    for sr in sorted(glob.glob(os.path.join(carpeta, '*', '*AnalyticMS_SR*.tif'))):
        sitio = os.path.basename(os.path.dirname(sr))
        item = os.path.basename(sr).split('_3B_')[0]
        with rasterio.open(sr) as img:
            a = img.read().astype('float32') / 10000.0
        n = a.shape[0]
        comps = COMPOSICIONES_8B if n >= 8 else COMPOSICIONES_4B
        valido = a.sum(axis=0) > 0
        etapa, fecha = info.get(item, ('', ''))
        if not fecha:
            m = re.match(r'(\d{4})(\d{2})(\d{2})', item)
            fecha = f'{m.group(1)}-{m.group(2)}-{m.group(3)}' if m else item
        fig, axes = plt.subplots(1, len(comps), figsize=(4.2 * len(comps), 4.6), squeeze=False)
        imgs = {}
        for ax, (nom, bandas, _) in zip(axes[0], comps):
            rgb = estirar(a[[b - 1 for b in bandas]], valido)
            imgs[nom] = rgb
            ax.imshow(rgb); ax.set_title(f"{nom}\nbandas {'-'.join(map(str, bandas))}", fontsize=10)
            ax.set_xticks([]); ax.set_yticks([])
            plt.imsave(os.path.join(salida, f'{sitio}_{fecha}_{item}_{nom.split(" (")[0].replace(" ", "_")}.png'), rgb)
        fig.suptitle(f'{sitio} · {fecha} · {etapa} · {n} bandas · {item}', fontsize=12, fontweight='bold', x=0.02, ha='left')
        plt.tight_layout()
        fig.savefig(os.path.join(salida, f'{sitio}_{fecha}_{item}_PANEL.png'), dpi=150, bbox_inches='tight')
        plt.show()
        filas.append({'sitio': sitio, 'fecha': fecha, 'etapa': etapa, 'item_id': item, 'bandas': n, 'imgs': imgs})

    if not filas:
        print('⚠️ No hay imágenes en', carpeta, '→ corre primero planet_gestor_descargas.py con PEDIR = False'); return

    # Hoja de contacto por sitio: filas = fechas/etapas, columnas = composiciones
    for sitio in sorted({f['sitio'] for f in filas}):
        fs = sorted([f for f in filas if f['sitio'] == sitio], key=lambda f: f['fecha'])
        noms = [c[0] for c in COMPOSICIONES_8B]
        fig, axes = plt.subplots(len(fs), len(noms), figsize=(3.2 * len(noms), 3.2 * len(fs)), squeeze=False)
        for i, f in enumerate(fs):
            for j, nom in enumerate(noms):
                ax = axes[i, j]; ax.set_xticks([]); ax.set_yticks([])
                if nom in f['imgs']:
                    ax.imshow(f['imgs'][nom])
                else:
                    ax.text(.5, .5, 'No disponible\n(escena de 4 bandas)', ha='center', va='center', fontsize=9, transform=ax.transAxes)
                if i == 0:
                    ax.set_title(nom, fontsize=10)
                if j == 0:
                    ax.set_ylabel(f"{f['fecha']}\n{f['etapa']}", fontsize=9)
        fig.suptitle(f'{sitio}: todas las fechas descargadas × composiciones', fontsize=13, fontweight='bold', x=0.02, ha='left')
        plt.tight_layout()
        fig.savefig(os.path.join(salida, f'{sitio}_HOJA_CONTACTO.png'), dpi=150, bbox_inches='tight')
        plt.show()

    tabla = pd.DataFrame([{k: v for k, v in f.items() if k != 'imgs'} for f in filas])
    tabla.to_csv(os.path.join(salida, 'LISTA_COMPOSICIONES.csv'), index=False, encoding='utf-8-sig')
    display(tabla)
    print(f'✅ {len(filas)} imágenes procesadas · PNG en Drive: {salida}')

_composiciones()

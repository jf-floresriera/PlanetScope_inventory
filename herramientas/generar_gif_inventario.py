# Genera assets/inventario_animado.gif a partir del inventario (solo datos agregados: no usa imágenes).
#   python herramientas/generar_gif_inventario.py RUTA_INVENTARIO.csv|.xlsx [assets/inventario_animado.gif]
import io, sys
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from PIL import Image

ruta = sys.argv[1]
salida = sys.argv[2] if len(sys.argv) > 2 else 'assets/inventario_animado.gif'
inv = pd.read_excel(ruta, sheet_name='escenas_metadatos') if ruta.endswith('.xlsx') else pd.read_csv(ruta, low_memory=False)
inv['d'] = inv.despejada.astype(str).eq('True')
inv['n_bandas'] = pd.to_numeric(inv.n_bandas, errors='coerce')
sitios = [s for s in ['PPAC', 'RICE', 'SEPAC', 'SWPAC'] if s in set(inv.sitio)]
anios = sorted(inv[inv.sitio.isin(sitios)].anio.astype(int).unique())
dias = pd.date_range('2001-04-01', '2001-10-31'); N = len(dias)
MESES = ['', 'ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
COL = ['#f3f2ee', '#c9c7c0', '#1baf7a', '#2a78d6']
ETAPAS = [('Siembra', '04-01'), ('Establec.', '05-21'), ('Vegetativo', '06-16'), ('Reproductivo', '07-21'), ('Madurez', '09-11'), ('Cosecha', '10-01')]

M = {}
for s in sitios:
    A = np.zeros((len(anios), N))
    for i, a in enumerate(anios):
        g = inv[(inv.sitio == s) & (inv.anio.astype(int) == a)]
        e = np.where(g.d & (g.n_bandas == 8), 3, np.where(g.d, 2, 1))
        st = pd.Series(e, index=pd.to_datetime(g.fecha)).groupby(level=0).max()
        for t, v in st.items():
            k = (pd.Timestamp(2001, t.month, t.day) - dias[0]).days
            if 0 <= k < N:
                A[i, k] = v
    M[s] = A

frames = []
for corte in list(range(7, N + 1, 7)) + [N] * 8:
    fig, axes = plt.subplots(len(sitios), 1, figsize=(9, 1.35 * len(sitios) + 0.6), dpi=90, squeeze=False)
    for ax, s in zip(axes[:, 0], sitios):
        B = M[s].copy(); B[:, corte:] = 0
        ax.imshow(B, aspect='auto', cmap=ListedColormap(COL), vmin=0, vmax=3, interpolation='nearest')
        for y in np.arange(.5, len(anios) - .5):
            ax.axhline(y, color='white', lw=1.5)
        for n, md in ETAPAS:
            x = (pd.Timestamp('2001-' + md) - dias[0]).days - .5
            ax.axvline(x, color='white', lw=1.5)
            if s == sitios[0]:
                ax.text(x + 2, -0.8, n, fontsize=7, va='bottom', color='#0b0b0b')
        ax.axvline(corte - .5, color='#eb6834', lw=1.2)
        ax.set_yticks(range(len(anios))); ax.set_yticklabels(anios, fontsize=6.5)
        ax.set_xticks([]); ax.set_ylabel(s, rotation=0, ha='right', va='center', fontsize=9, fontweight='bold')
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.tick_params(length=0)
        ax.text(N + 3, len(anios) / 2 - .5, f'{int((M[s][:, :corte] >= 2).sum())} fechas\ndespejadas', fontsize=7, va='center', color='#52514e')
    f = dias[min(corte, N) - 1]
    fig.suptitle(f'Imágenes PlanetScope despejadas en temporada ({anios[0]}–{anios[-1]}) · hasta el {f.day} de {MESES[f.month]}',
                 fontsize=10, fontweight='bold', x=0.02, ha='left')
    fig.legend(handles=[Patch(color=COL[3], label='Despejada · 8 bandas'), Patch(color=COL[2], label='Despejada · 4 bandas'),
                        Patch(color=COL[1], label='Nubosa o no cubre el sitio')], loc='lower left', ncol=3, fontsize=7, frameon=False)
    plt.tight_layout(rect=(0.02, 0.05, 0.9, 0.95))
    b = io.BytesIO(); fig.savefig(b, format='png', facecolor='white'); plt.close(fig); b.seek(0)
    frames.append(Image.open(b).convert('P', palette=Image.ADAPTIVE, colors=64))
frames[0].save(salida, save_all=True, append_images=frames[1:], duration=180, loop=0, optimize=True)
print('GIF:', salida, len(frames), 'cuadros')

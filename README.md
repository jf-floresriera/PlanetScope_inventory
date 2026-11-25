<!-- ═══════════════════════════ ENCABEZADO ANIMADO ═══════════════════════════ -->
<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0d366b,50:2a78d6,100:1baf7a&height=220&section=header&text=PlanetScope%20Inventory&fontSize=52&fontColor=ffffff&animation=fadeIn&fontAlignY=36&desc=Mancha%20de%20asfalto%20del%20ma%C3%ADz%20%C2%B7%20Purdue%20(Indiana)%20%2B%20R%C3%ADo%20Ariari%20(Meta)&descAlignY=58&descSize=17" width="100%" alt="PlanetScope Inventory"/>
</p>

<p align="center">
  <a href="https://github.com/jf-floresriera/PlanetScope_inventory">
    <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=20&duration=3200&pause=900&color=2A78D6&center=true&vCenter=true&width=760&lines=Inventario+PlanetScope+por+etapa+del+cultivo+%F0%9F%8C%BD;8+bandas+SuperDove+%C2%B7+Red+Edge+%C2%B7+3+m+de+resoluci%C3%B3n+%F0%9F%9B%B0%EF%B8%8F;Descargas+con+control+de+cuota+mes+a+mes+%F0%9F%93%8A;NDVI+%C2%B7+NDRE+%C2%B7+PSRI+para+la+mancha+de+asfalto+%F0%9F%94%AC" alt="Typing SVG" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-2a78d6?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/Google%20Colab-listo-F9AB00?style=for-the-badge&logo=googlecolab&logoColor=white"/>
  <img src="https://img.shields.io/badge/Planet-E%26R%20Basic-1baf7a?style=for-the-badge&logo=planet&logoColor=white"/>
  <img src="https://img.shields.io/badge/PlanetScope-SuperDove%208b-0d366b?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/estado-en%20desarrollo-eb6834?style=for-the-badge"/>
</p>

---

## 🛰️ ¿Qué es este repositorio?

Documenta el **flujo metodológico completo** para buscar, inventariar, descargar con control de cuota y analizar
imágenes **PlanetScope** (Planet Labs, programa *Education & Research*) en la tesis sobre la
**mancha de asfalto del maíz** (*tar spot*, *Phyllachora maydis*):

| | Sitio | Lugar | Calendario |
|---|---|---|---|
| 🌽 | **PPAC** · Pinney Purdue Agricultural Center | Porter, Indiana | Maíz · 1 abr → 31 oct |
| 🌽 | **RICE** · Purdue Mary S. Rice Farm | LaPorte, Indiana | Maíz · 1 abr → 31 oct |
| 🌽 | **SEPAC** · Southeast Purdue Agricultural Center | Jennings, Indiana | Maíz · 1 abr → 31 oct |
| 🌽 | **SWPAC** · Southwest Purdue Agricultural Center | Knox, Indiana | Maíz · 1 abr → 31 oct |
| 🌾 | **ARIARI** · Río Ariari – El Castillo | Meta, Colombia | Semestres A y B |

<p align="center"><img src="assets/flujo_animado.svg" width="100%" alt="Flujo de trabajo animado"/></p>

---

## 📈 El inventario en movimiento

Cada franja es un día de la temporada; cada fila, un año. Así se van acumulando las fechas con imagen despejada
(datos agregados del inventario 2020–2024, Indiana):

<p align="center"><img src="assets/inventario_animado.gif" width="92%" alt="Inventario animado"/></p>

<details>
<summary><b>📊 Números clave del inventario (clic para ver)</b></summary>

| Indicador (Indiana, 2020–2024, 1 abr – 31 oct) | Valor |
|---|---|
| Escenas encontradas | **5.658** |
| Fechas con imagen por sitio y temporada | 131 – 186 |
| Fechas despejadas por sitio y temporada | 54 – 91 |
| Fechas despejadas en etapa reproductiva (ventana de la mancha de asfalto) | ~8 – 20 por sitio y año |
| Escenas de 8 bandas (SuperDove) | 14 % (2020) → 60 % (2021) → **99–100 %** (2022–2024) |

Tablas completas: [`datos/RESUMEN_INVENTARIO_POR_ETAPA.csv`](datos/RESUMEN_INVENTARIO_POR_ETAPA.csv) ·
[`datos/RESUMEN_INVENTARIO_SITIO_ANIO.csv`](datos/RESUMEN_INVENTARIO_SITIO_ANIO.csv)
</details>

---

## 🌱 Calendario del cultivo

<p align="center"><img src="assets/fenologia_animada.svg" width="100%" alt="Calendario fenológico animado"/></p>

---

## ⚠️ La regla de oro de la cuota

<p align="center"><img src="assets/cuota_animada.svg" width="100%" alt="Cuota animada"/></p>

> [!IMPORTANT]
> Con el plan E&R Basic **cada escena pedida cuesta mínimo 100 km²**, aunque se recorte 1 km².
> Hay **3.000 km²/mes** → ≈ **29 escenas al mes**. Los pedidos se hacen **solo** con el gestor, **una vez al mes**.
> Descargar lo ya pedido es **gratis**. Detalles en [`docs/02_cuota_y_pedidos.md`](docs/02_cuota_y_pedidos.md).

---

## 🚀 Inicio rápido (Google Colab)

[![Abrir en Colab](https://img.shields.io/badge/Abrir%20en-Colab-F9AB00?style=for-the-badge&logo=googlecolab&logoColor=white)](https://colab.research.google.com/github/jf-floresriera/PlanetScope_inventory/blob/main/notebooks/INICIO_Colab.ipynb)

```python
# 1 · Drive + API key (nunca la escribas en el código)
from google.colab import drive; drive.mount('/content/drive')
import os, getpass; os.environ['PL_API_KEY'] = getpass.getpass('API key de Planet: ')

# 2 · Clonar/actualizar el repo dentro de Drive
%cd /content/drive/MyDrive/Purdue_TarSpot_Project
!git clone https://github.com/jf-floresriera/PlanetScope_inventory.git || (cd PlanetScope_inventory && git pull)
S = '/content/drive/MyDrive/Purdue_TarSpot_Project/PlanetScope_inventory/scripts'

# 3 · Descargar lo ya pedido + control + plan (PEDIR = False → no gasta)
%run -i $S/planet_gestor_descargas.py

# 4 · Composiciones de color
%run -i $S/planet_composiciones.py
```

---

## 🧭 Arquitectura: qué vive dónde

```mermaid
flowchart LR
    subgraph GH["🐙 GitHub · público"]
        A[scripts/] --- B[docs/] --- C[notebooks/] --- D[datos agregados]
    end
    subgraph CO["🧪 Google Colab"]
        E[INICIO_Colab.ipynb]
    end
    subgraph PL["🛰️ Planet API"]
        F[Data API<br/>búsqueda · 0 km²]
        G[Orders API<br/>pedido · 100 km²/escena]
        H[Tiles<br/>vistas · 0 km²]
    end
    subgraph DR["🔒 Google Drive · privado"]
        I[imágenes SR 8b + UDM2 + XML]
        J[CONTROL_DESCARGAS.xlsx]
        K[inventario completo]
    end
    GH -- git clone/pull --> E
    E --> F --> K
    E -- PEDIR=True · 1 vez/mes --> G --> I
    E --> H
    I --> E
    E --> J
```

---

## 📚 Documentación de procesos

| # | Proceso | Documento |
|:-:|---|---|
| 0 | Contexto completo del proyecto | [`docs/00_contexto_proyecto.md`](docs/00_contexto_proyecto.md) |
| 1 | Inventario por etapa del cultivo (Data API) | [`docs/01_inventario.md`](docs/01_inventario.md) |
| 2 | Cuota y pedidos mes a mes | [`docs/02_cuota_y_pedidos.md`](docs/02_cuota_y_pedidos.md) |
| 3 | Descarga, registro y control | [`docs/03_descarga_y_control.md`](docs/03_descarga_y_control.md) |
| 4 | Composiciones de color e índices | [`docs/04_composiciones_e_indices.md`](docs/04_composiciones_e_indices.md) |
| 5 | Scene tiles y mosaicos mensuales | [`docs/05_tiles_y_basemaps.md`](docs/05_tiles_y_basemaps.md) |
| 6 | Sesión de trabajo: Colab + Drive + GitHub | [`docs/06_sesion_colab_github.md`](docs/06_sesion_colab_github.md) |
| 7 | Qué datos se pueden publicar (licencia E&R) | [`docs/07_datos_y_licencia.md`](docs/07_datos_y_licencia.md) |
| 📓 | Bitácora del proyecto | [`docs/BITACORA.md`](docs/BITACORA.md) |

---

## 🗂️ Estructura

```
PlanetScope_inventory/
├── 📄 README.md
├── 🎞️ assets/          animaciones del README (SVG/GIF)
├── 📚 docs/            procesos documentados + bitácora
├── 🐍 scripts/         gestor de descargas, composiciones, tiles, índices, inventario
├── 📓 notebooks/       INICIO_Colab.ipynb + cuaderno multisensor v3
├── 📊 datos/           sitios y tablas AGREGADAS (sin imágenes de Planet)
├── 🖼️ resultados/      figuras del inventario
└── 🧰 herramientas/    generadores de las animaciones
```

Cada carpeta tiene su propio `README.md`.

---

## 📝 Cita obligatoria (programa E&R de Planet)

```
Planet Team (2026). Planet Application Program Interface: In Space for Life on Earth. San Francisco, CA. https://api.planet.com
```

<p align="center">
  <b>Jesús Enrique Flores Riera</b> · Universidad Nacional de Colombia<br/>
  <sub>Imágenes PlanetScope © Planet Labs PBC — uso académico no comercial (programa Education & Research).</sub>
</p>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:1baf7a,50:2a78d6,100:0d366b&height=120&section=footer" width="100%"/>

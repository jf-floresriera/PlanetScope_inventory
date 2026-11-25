<p align="center"><img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=22&duration=3000&pause=800&color=2A78D6&center=true&vCenter=true&width=720&lines=06+%C2%B7+Sesi%C3%B3n+de+trabajo;Colab+%2B+Drive+%2B+GitHub" alt="typing"/></p>

# 06 · Sesión de trabajo: Colab + Drive + GitHub

| Pieza | Qué guarda | Por qué |
|---|---|---|
| **GitHub** (este repo, público) | Código, documentación, tablas agregadas, figuras del inventario | Historial de cambios; nada se pierde si se reinicia Colab |
| **Google Drive** (privado) | Imágenes, inventario completo, control de descargas, registros | Licencia E&R y tamaño de los archivos |
| **Google Colab** | Ejecución | Gratis, conectado a Drive |

## Cada sesión

1. Abrir [`notebooks/INICIO_Colab.ipynb`](../notebooks/INICIO_Colab.ipynb) en Colab
   ([enlace directo](https://colab.research.google.com/github/jf-floresriera/PlanetScope_inventory/blob/main/notebooks/INICIO_Colab.ipynb)).
2. Celda 1: montar Drive y escribir la API key (con `getpass`, nunca en el código).
3. Celda 2: `git clone` la primera vez, `git pull` las siguientes → el repo queda en
   `Mi unidad/Purdue_TarSpot_Project/PlanetScope_inventory/`.
4. Celdas 3–6 según lo que toque (ver [`02`](02_cuota_y_pedidos.md), [`04`](04_composiciones_e_indices.md), [`05`](05_tiles_y_basemaps.md)).
5. Anotar la sesión en [`BITACORA.md`](BITACORA.md).

## Guardar cambios en GitHub

Lo más simple: editar en la web de GitHub (lápiz ✏️) o subir archivos con **Add file → Upload files**.

Desde Colab (opcional), con un *token* personal de GitHub que **no** se escribe en el código:

```python
import getpass, subprocess
tok = getpass.getpass('Token de GitHub: ')
%cd /content/drive/MyDrive/Purdue_TarSpot_Project/PlanetScope_inventory
!git config user.name "jf-floresriera"
!git config user.email "TU_CORREO"
!git add -A && git commit -m "Actualiza bitácora"
subprocess.run(['git', 'push', f'https://{tok}@github.com/jf-floresriera/PlanetScope_inventory.git', 'main'])
```

> [!CAUTION]
> Antes de `git add -A`, revisa con `!git status` que no aparezcan imágenes `.tif`, el inventario completo ni archivos
> con claves. El [`.gitignore`](../.gitignore) ya los excluye.

## Dónde desarrollar modelos

* **Colab**: procesamiento, índices, modelos clásicos (Random Forest, regresión, series de tiempo).
* **Colab Pro / servidor universitario**: modelos que necesiten más memoria o GPU por horas.
* **Google Earth Engine**: cruzar PlanetScope (subido como *asset*) con Sentinel-2 y Landsat.

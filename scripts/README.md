<p align="center"><img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=21&duration=2800&pause=800&color=2A78D6&center=true&vCenter=true&width=680&lines=%F0%9F%90%8D+scripts%2F;Los+procesos+en+Python" alt="typing"/></p>

# 🐍 scripts/

Se ejecutan en Colab con `%run -i <ruta>` (ver [`notebooks/INICIO_Colab.ipynb`](../notebooks/INICIO_Colab.ipynb)).

| Script | Qué hace | ¿Gasta km²? | Doc |
|---|---|:-:|---|
| [`planet_gestor_descargas.py`](planet_gestor_descargas.py) | Baja lo ya pedido, documenta el estado de cada escena, planifica mes a mes y (solo con `PEDIR = True`) hace el pedido del mes | Solo con `PEDIR = True` | [02](../docs/02_cuota_y_pedidos.md) · [03](../docs/03_descarga_y_control.md) |
| [`planet_composiciones.py`](planet_composiciones.py) | Composiciones de color (natural, infrarrojo, Red Edge, senescencia) y hojas de contacto | ❌ | [04](../docs/04_composiciones_e_indices.md) |
| [`planet_graficas_e_indices.py`](planet_graficas_e_indices.py) | Gráficas del inventario + mapas y series de NDVI, NDRE, PSRI con lo descargado | ❌ (`CONFIRMAR_PEDIDO = False`) | [01](../docs/01_inventario.md) · [04](../docs/04_composiciones_e_indices.md) |
| [`planet_tiles_aprovechar.py`](planet_tiles_aprovechar.py) | Vistas rápidas (scene tiles) con nube sobre el sitio + mosaicos mensuales | ❌ (usa tiles) | [05](../docs/05_tiles_y_basemaps.md) |
| [`planet_inventario_celdas.py`](planet_inventario_celdas.py) | Celdas P1–P10 del inventario por etapa (se agregan al cuaderno multisensor) | ❌ | [01](../docs/01_inventario.md) |
| [`planet_completar_ariari_2025.py`](planet_completar_ariari_2025.py) | Agrega Ariari 2021–2025 e Indiana 2025 al inventario | ❌ | [01](../docs/01_inventario.md) |

> [!IMPORTANT]
> El **único** script que puede hacer pedidos es el gestor. Todos los demás trabajan con lo que ya está en Drive.

Variables de entorno: `PL_API_KEY` (se escribe con `getpass`, nunca en el código).

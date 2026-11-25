<p align="center"><img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=22&duration=3000&pause=800&color=2A78D6&center=true&vCenter=true&width=720&lines=04+%C2%B7+Composiciones+e+%C3%ADndices;NDVI+%C2%B7+NDRE+%C2%B7+CIrededge+%C2%B7+PSRI" alt="typing"/></p>

# 04 · Composiciones de color e índices

## Composiciones ([`scripts/planet_composiciones.py`](../scripts/planet_composiciones.py))

| Composición | R-G-B (8 bandas) | R-G-B (4 bandas) | Para qué sirve |
|---|:-:|:-:|---|
| Color natural | 6-4-2 | 3-2-1 | Ver el lote como el ojo: suelo, rastrojo, agua, caminos |
| Falso color infrarrojo | 8-6-4 | 4-3-2 | Vegetación sana en rojo intenso; estrés y suelo apagados |
| Red Edge | 8-7-6 | — | Diferencias de clorofila en el dosel (estrés, mancha de asfalto) |
| Senescencia | 7-5-2 | — | Amarilleo hacia madurez y cosecha |

Estiramiento común a las tres bandas (percentiles 2–98 de los píxeles válidos) con gamma 1/1,4, para conservar los tonos.
Salidas en Drive (`07_Figuras/Planet/composiciones/`): un panel por imagen, cada composición en PNG y una
**hoja de contacto por sitio** (filas = fechas/etapas, columnas = composiciones).

## Índices ([`scripts/planet_graficas_e_indices.py`](../scripts/planet_graficas_e_indices.py))

| Índice | Fórmula (bandas PlanetScope) | 4b | 8b | Utilidad |
|---|---|:-:|:-:|---|
| NDVI | (NIR − R) / (NIR + R) | ✅ | ✅ | Vigor y biomasa (se satura en dosel cerrado) |
| GNDVI | (NIR − G) / (NIR + G) | ✅ | ✅ | Clorofila |
| EVI2 | 2,5·(NIR − R) / (NIR + 2,4R + 1) | ✅ | ✅ | Dosel denso |
| SAVI | 1,5·(NIR − R) / (NIR + R + 0,5) | ✅ | ✅ | Siembra y establecimiento |
| NDWI | (G − NIR) / (G + NIR) | ✅ | ✅ | Agua y encharcamiento (Ariari) |
| **NDRE** | (NIR − RE) / (NIR + RE) | — | ✅ | ⭐ Clorofila y N, estrés temprano |
| **CIrededge** | NIR / RE − 1 | — | ✅ | ⭐ Clorofila sin saturación |
| **PSRI\*** | (R − Azul) / RE | — | ✅ | ⭐ Senescencia, avance de lesiones |
| MTCI\* · CCCI · PRI\* | ver [`datos/REFERENCIA_PLANETSCOPE_indices.csv`](../datos/REFERENCIA_PLANETSCOPE_indices.csv) | — | ✅ | Clorofila / estrés |
| NDMI · NBR · LST | requieren SWIR o térmico | ❌ | ❌ | Usar Sentinel-2 · Landsat · EnMAP |

\* Adaptados a las bandas de PlanetScope (una sola banda Red Edge, a 705 nm).

### Flujo de cálculo

```mermaid
flowchart LR
    A[SR × 10 000] -->|÷ 10 000| B[Reflectancia 0–1]
    C[UDM2 banda 1 = clear] --> D[Máscara de píxeles válidos]
    B --> E[Índices]
    D --> E
    E --> F[Mapas por etapa<br/>misma escala de color]
    E --> G[GeoTIFF de índices<br/>para QGIS]
    E --> H[Media ± DE por sitio<br/>PLANET_INDICES_POR_ETAPA.csv]
    H --> I[Evolución siembra → cosecha]
```

> [!NOTE]
> `planet_graficas_e_indices.py` tiene `CONFIRMAR_PEDIDO = False`: **nunca** hace pedidos; trabaja con lo que ya está en Drive.

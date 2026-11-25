<p align="center"><img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=22&duration=3000&pause=800&color=2A78D6&center=true&vCenter=true&width=720&lines=01+%C2%B7+Inventario+por+etapa+del+cultivo;Data+API+de+Planet+%C2%B7+0+km%C2%B2+de+cuota" alt="typing"/></p>

# 01 · Inventario por etapa del cultivo

> **Buscar no consume cuota.** El inventario se puede repetir todas las veces que haga falta.

## Qué hace

Consulta la **Data API** de Planet (`quick-search`) para cada sitio, campaña, año y **etapa del cultivo**,
y guarda **todos los metadatos** de cada escena PlanetScope (`PSScene`).

```mermaid
flowchart TD
    A[Sitio + AOI cuadrado] --> B[Calendario del cultivo<br/>ventanas por etapa]
    B --> C[quick-search<br/>GeometryFilter + DateRangeFilter]
    C --> D[Paginación _links._next]
    D --> E[Etiquetar etapa<br/>por fecha de toma]
    E --> F[Cobertura del AOI<br/>malla de puntos]
    F --> G[Despejada = clear ≥ 80 %<br/>y AOI ≥ 99 %]
    G --> H[(Inventario CSV/Excel<br/>en Drive)]
```

## Scripts

| Script | Uso |
|---|---|
| [`scripts/planet_inventario_celdas.py`](../scripts/planet_inventario_celdas.py) | Celdas P1–P10 que se agregan al cuaderno multisensor (inventario, fichas por área, gráficas, mejores escenas, Excel) |
| [`scripts/planet_completar_ariari_2025.py`](../scripts/planet_completar_ariari_2025.py) | Completa el inventario con **Ariari 2021–2025** e **Indiana 2025** y lo une a `PL_INV` |
| [`scripts/planet_graficas_e_indices.py`](../scripts/planet_graficas_e_indices.py) | Gráficas del inventario (calendario por sitio, fechas por etapa, sitio × año, sensores) |

## Columnas principales del inventario

| Columna | Significado |
|---|---|
| `sitio`, `campana`, `anio`, `etapa`, `fecha`, `hora_utc`, `doy` | Ubicación temporal de la escena en el calendario |
| `item_id` | Identificador de la escena en Planet |
| `cobertura_aoi_pct` | % del área de interés cubierto por la huella de la escena |
| `n_bandas`, `tiene_8b_sr`, `tiene_4b_sr`, `tiene_udm2` | Qué productos se pueden pedir |
| `clear_pct`, `nubes_pct`, `despejada` | Calidad (⚠️ calculada por Planet sobre **toda la escena**) |
| `p_*` | **Todos** los metadatos originales de Planet: `p_instrument`, `p_gsd`, `p_sun_elevation`, `p_view_angle`, `p_light_haze_percent`, `p_shadow_percent`, `p_quality_category`… |

## Limitación importante

El `% despejado` de Planet se calcula sobre **toda la escena** (≈ 25 × 11 km o 32 × 20 km), no sobre el sitio.
Una escena "despejada" puede tener una nube justo encima de la finca. Se corrige con:

1. Las **vistas rápidas** con scene tiles → columna `nubes_sobre_sitio_%` ([`05_tiles_y_basemaps.md`](05_tiles_y_basemaps.md)).
2. La máscara **UDM2** de las imágenes descargadas ([`03_descarga_y_control.md`](03_descarga_y_control.md)).

## Resultados (Indiana 2020–2024)

![Fechas por etapa](../resultados/figuras/planet_fechas_por_etapa.png)

![Sensores por año](../resultados/figuras/planet_sensores_por_anio.png)

Tablas agregadas: [`datos/RESUMEN_INVENTARIO_POR_ETAPA.csv`](../datos/RESUMEN_INVENTARIO_POR_ETAPA.csv) ·
[`datos/RESUMEN_INVENTARIO_SITIO_ANIO.csv`](../datos/RESUMEN_INVENTARIO_SITIO_ANIO.csv).
El inventario completo escena por escena se guarda **solo en Drive** (ver [`07_datos_y_licencia.md`](07_datos_y_licencia.md)).

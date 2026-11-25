<p align="center"><img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=22&duration=3000&pause=800&color=1BAF7A&center=true&vCenter=true&width=720&lines=03+%C2%B7+Descarga%2C+registro+y+control;Todo+queda+en+Google+Drive+%F0%9F%94%92" alt="typing"/></p>

# 03 · Descarga, registro y control

## Producto que se pide

| Elemento | Detalle |
|---|---|
| Bundle | `analytic_8b_sr_udm2` (si la escena es de 4 bandas: `analytic_sr_udm2`) |
| Nivel | **L3B ortorectificado · reflectancia de superficie (BOA)** — equivalente a Sentinel-2 L2A |
| Escala | reflectancia × 10 000 (`uint16`) · píxel de 3 m |
| Recorte | ~10 × 10 km alrededor del sitio (100 km² de cuota) |

### Archivos por escena

| Archivo | Contenido |
|---|---|
| `*_3B_AnalyticMS_SR_8b_clip.tif` | Imagen con las 8 bandas |
| `*_3B_udm2_clip.tif` | Máscara de calidad: clear, snow, shadow, light haze, heavy haze, cloud, confidence, unusable |
| `*_3B_AnalyticMS_8b_metadata_clip.xml` | Metadatos de calibración y adquisición |
| `*_metadata.json` | Metadatos de la escena (los mismos del inventario) |

### Bandas SuperDove

| N.º | Banda | Centro (nm) | N.º | Banda | Centro (nm) |
|:-:|---|:-:|:-:|---|:-:|
| 1 | Azul costero | 443 | 5 | Amarillo | 610 |
| 2 | Azul | 490 | 6 | Rojo | 665 |
| 3 | Verde I | 531 | 7 | **Red Edge** | 705 |
| 4 | Verde | 565 | 8 | NIR | 865 |

## Dónde queda todo (Drive)

```
Mi unidad/Purdue_TarSpot_Project/08_Planet_PlanetScope/
├── INVENTARIO_PLANET_COMPLETO.csv      ← respaldo del inventario (lo crea el gestor)
├── CONTROL_DESCARGAS_PLANET.xlsx       ← hojas: resumen · plan_por_mes · control_escenas · pedidos
└── imagenes_recortadas/
    ├── pedidos_planet.json             ← registro de pedidos   (NO BORRAR)
    ├── control_cuota.json              ← km² pedidos por el gestor este mes (NO BORRAR)
    ├── PPAC/  RICE/  SEPAC/  SWPAC/  ARIARI/   ← imágenes + UDM2 + XML + JSON
```

## Estados de una escena en el control

| Estado | Significado | Acción |
|---|---|---|
| ✅ descargada | La imagen SR está en Drive | Ninguna |
| ⏳ pedida, falta bajar | El pedido existe en Planet | Se baja **gratis** al volver a correr el gestor |
| ❌ pedido fallido | Planet no pudo procesar el pedido | Revisar el mensaje; no se repite sola |
| 🕒 por pedir | Nunca se ha pedido | Queda en el plan mensual |

## Si algo no se guardó

Ejecutar el gestor con `PEDIR = False`: lista **todos** los pedidos de la cuenta en Planet, espera los que
siguen en proceso (hasta 60 min) y baja a Drive lo que falte. **No gasta cuota.**

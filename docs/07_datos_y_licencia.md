<p align="center"><img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=22&duration=3000&pause=800&color=EB6834&center=true&vCenter=true&width=720&lines=07+%C2%B7+Qu%C3%A9+datos+se+pueden+publicar;Licencia+Education+%26+Research+de+Planet" alt="typing"/></p>

# 07 · Qué datos se pueden publicar

Este repositorio es **público**. Según las *Dataset Sharing Guidelines* del programa Education & Research Basic,
las imágenes de Planet y los conjuntos de datos con valores crudos de imagen son de **uso privado del proyecto**;
públicamente solo se permiten "Permitted Imagery" y productos derivados que **no conserven los valores crudos**.
Consulta siempre la versión vigente:
[Dataset Sharing Guidelines](https://support.planet.com/hc/en-us/articles/22540409084701-Dataset-Sharing-Guidelines-for-the-Education-and-Research-Basic-Program).

| Contenido | ¿En GitHub (público)? | Dónde va |
|---|:-:|---|
| Código, documentación, cuadernos | ✅ | Este repo |
| Tablas **agregadas** (conteos por sitio/año/etapa, % de 8 bandas) | ✅ | `datos/` |
| Figuras del inventario (calendarios, conteos) | ✅ | `resultados/figuras/`, `assets/` |
| Coordenadas de los sitios | ✅ | `datos/sitios_estudio.geojson` |
| Imágenes GeoTIFF (SR, UDM2), índices en GeoTIFF | ❌ | Drive privado |
| Composiciones, vistas rápidas, mosaicos (PNG de imágenes) | ❌ | Drive privado |
| Inventario completo escena por escena, control de descargas | ❌ | Drive privado |
| API key, tokens, contraseñas | ❌ **nunca** | Solo con `getpass` en Colab |

El [`.gitignore`](../.gitignore) bloquea estos archivos por nombre y extensión.

## Cita obligatoria en publicaciones

```
Planet Team (2026). Planet Application Program Interface: In Space for Life on Earth. San Francisco, CA. https://api.planet.com
```

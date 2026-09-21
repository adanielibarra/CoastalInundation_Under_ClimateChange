<p align="center"><img src="assets/logo.png" width="140" alt="Coastal Inundation Under Climate Change logo"></p>

# Coastal Inundation Under Climate Change

QGIS plugin to model coastal inundation under sea level rise scenarios.

Plugin created by Daniel Ibarra Marinas, Facultad de Ingeniería y Ciencias, Universidad Autónoma de Tamaulipas.

[English](#english) · [Español](#español)

---

## English

### What it does

For each sea level rise scenario, the plugin raises the sea over a DEM and floods only the pixels that lie below the new level **and** connect to the sea through pixels that are also below it. Low areas behind dunes, dykes or other higher ground are stored in a separate layer as disconnected low areas.

- **NoData as sea:** many coastal DEMs leave the sea as NoData. By default, NoData connected to a sea point is treated as sea, so you can click directly on the sea.
- **Uncertainty bands:** lower, central and upper bands from the DEM error (RMSE and bias) and the projection uncertainty, given as a symmetric σ or as percentiles (17/83 or 5/95). With percentiles the bands are asymmetric and the central level stays at the median of the projection.
- **Outputs:** depth GeoTIFF with style, and a GeoPackage with flooding by band, classified disconnected low areas, statistics and full run metadata.
- **Bilingual:** labels and help in English and Spanish.

It is a static threshold model with connectivity: no erosion, waves, storm surge, drainage or groundwater. See the limitations in the manual.

### Requirements

QGIS 3.44 or later. numpy and GDAL come with QGIS; scipy is recommended (faster), but not required.

### Installation

1. Download the zip from the [Releases](../../releases) page, or build it with `python build_zip.py`.
2. In QGIS: **Plugins › Manage and Install Plugins › Install from ZIP**.
3. The tool appears in the **Processing Toolbox** under *Coastal Inundation Under Climate Change*.

### Manual

- [User manual (English, PDF)](doc/CoastalInundation_Under_ClimateChange_Manual_EN.pdf)
- [Manual de uso (español, PDF)](doc/CoastalInundation_Under_ClimateChange_Manual_ES.pdf)

### How to cite

Use the **Cite this repository** button on the right of this page, which reads [`CITATION.cff`](CITATION.cff).

### License

GNU General Public License, version 2 or later ([GPL-2.0-or-later](LICENSE)).

### Author

Daniel Ibarra Marinas · Facultad de Ingeniería y Ciencias, Universidad Autónoma de Tamaulipas
[daniel.ibarra@uat.edu.mx](mailto:daniel.ibarra@uat.edu.mx) · ORCID [0000-0003-3683-4456](https://orcid.org/0000-0003-3683-4456) · [ResearchGate](https://www.researchgate.net/profile/Daniel-Ibarra-Marinas)

Bug reports and suggestions: [Issues](../../issues).

---

## Español

### Qué hace

Para cada escenario de subida del nivel del mar, el plugin sube el mar sobre un MDT e inunda solo los píxeles que quedan por debajo del nuevo nivel **y** conectan con el mar a través de píxeles también por debajo. Las zonas bajas detrás de dunas, motas u otro terreno más alto se guardan en una capa aparte como zonas bajas desconectadas.

- **NoData como mar:** muchos MDT costeros dejan el mar como NoData. Por defecto, el NoData conectado a un punto de mar se trata como mar, así que puedes hacer clic directamente en el mar.
- **Bandas de incertidumbre:** banda baja, central y alta a partir del error del MDT (RMSE y sesgo) y de la incertidumbre de la proyección, como σ simétrica o como percentiles (17/83 o 5/95). Con percentiles las bandas salen asimétricas y el nivel central se queda en la mediana de la proyección.
- **Resultados:** GeoTIFF de profundidad con estilo, y un GeoPackage con la inundación por bandas, las zonas bajas desconectadas clasificadas, estadísticas y todos los metadatos de la ejecución.
- **Bilingüe:** etiquetas y ayuda en inglés y en español.

Es un modelo estático de umbral con conectividad: sin erosión, oleaje, marea meteorológica, drenaje ni freático. Las limitaciones están en el manual.

### Requisitos

QGIS 3.44 o posterior. numpy y GDAL vienen con QGIS; se recomienda scipy (más rápido), pero no es obligatorio.

### Instalación

1. Descarga el zip de la página de [Releases](../../releases), o créalo con `python build_zip.py`.
2. En QGIS: **Complementos › Administrar e instalar complementos › Instalar a partir de ZIP**.
3. La herramienta aparece en la **Caja de herramientas de Procesos**, en *Coastal Inundation Under Climate Change*.

### Manual

- [Manual de uso (español, PDF)](doc/CoastalInundation_Under_ClimateChange_Manual_ES.pdf)
- [User manual (English, PDF)](doc/CoastalInundation_Under_ClimateChange_Manual_EN.pdf)

### Cómo citar

Usa el botón **Cite this repository** de la derecha de esta página, que lee el fichero [`CITATION.cff`](CITATION.cff).

### Licencia

GNU General Public License, versión 2 o posterior ([GPL-2.0-or-later](LICENSE)).

### Autor

Daniel Ibarra Marinas · Facultad de Ingeniería y Ciencias, Universidad Autónoma de Tamaulipas
[daniel.ibarra@uat.edu.mx](mailto:daniel.ibarra@uat.edu.mx) · ORCID [0000-0003-3683-4456](https://orcid.org/0000-0003-3683-4456) · [ResearchGate](https://www.researchgate.net/profile/Daniel-Ibarra-Marinas)

Errores y sugerencias: [Issues](../../issues).

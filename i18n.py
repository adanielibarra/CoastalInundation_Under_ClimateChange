"""Lightweight translation: English by default, Spanish if QGIS runs in Spanish."""
from qgis.core import QgsApplication

_ES = None


def _es():
    global _ES
    if _ES is None:
        try:
            _ES = str(QgsApplication.locale()).lower().startswith("es")
        except Exception:
            _ES = False
    return _ES


def bi(text):
    """Bilingual label: English first, then Spanish."""
    es = ES.get(text)
    return f"{text} / {es}" if es and es != text else text


def tr(text, **kw):
    t = ES.get(text, text) if _es() else text
    return t.format(**kw) if kw else t


ES = {
    # --- provider / algorithm
    # --- parameters
    "Coastal DEM (CRS in metres)": "MDT costero (CRS en metros)",
    "Band": "Banda",
    "Sea point (click on the map)": "Punto de mar (clic en el mapa)",
    "Sea points layer (optional)": "Capa de puntos de mar (opcional)",
    "Sea level rise scenarios in m (separated by ';')": "Subidas del nivel del mar en m (separadas por ';')",
    "The rise you enter is...": "La subida que metes es...",
    "Relative (already includes vertical land motion)": "Relativa (ya incluye movimiento vertical del terreno)",
    "Absolute (no vertical land motion)": "Absoluta (sin movimiento vertical del terreno)",
    "Base level above the DEM vertical datum (m), e.g. high tide":
        "Nivel base sobre el datum vertical del MDT (m), p. ej. pleamar",
    "Uniform subsidence (m, positive = sinking). Absolute rise only":
        "Subsidencia uniforme (m, positivo = hundimiento). Solo si es absoluta",
    "Subsidence raster (m). Absolute rise only": "Raster de subsidencia (m). Solo si es absoluta",
    "DEM vertical RMSE (m)": "RMSE vertical del MDT (m)",
    "Projection σ (m), 0 if unknown": "σ de la proyección (m), 0 si no la tienes",
    "Band factor k": "Factor k de las bandas",
    "[pending] Land use (raster or polygons)": "[pendiente] Usos del suelo (raster o polígonos)",
    "[pending] Class field (if vector)": "[pendiente] Campo de clase (si es vectorial)",
    "[pending] Barriers (lines)": "[pendiente] Barreras (líneas)",
    "[pending] Water passages or culverts (lines)": "[pendiente] Pasos de agua (líneas)",
    "Connectivity": "Conectividad",
    "4 neighbours (conservative)": "4 vecinos (conservador)",
    "8 neighbours": "8 vecinos",
    "Output folder": "Carpeta de salida",
    # --- help
    "HELP": (
        "Plugin creado por Daniel Ibarra Marinas, Facultad de Ingeniería y Ciencias, Universidad Autónoma de "
        "Tamaulipas, para modelizar la inundación costera bajo escenarios de subida del nivel del mar. Inunda solo "
        "lo que queda por debajo del nuevo nivel y conecta con el mar a través de píxeles también por debajo; las "
        "zonas bajas sin esa conexión se guardan en una capa aparte.\n\n"
        "Punto de mar: haz clic en el mapa con el botón '...' del campo, o usa una capa de puntos (útil si el mar "
        "llega a zonas separadas por NoData).\n\n"
        "NoData: por defecto, el NoData conectado a un punto de mar se trata como mar, porque muchos MDT costeros "
        "dejan el mar como NoData. El resto de NoData no deja pasar el agua. Los huecos de NoData tierra adentro "
        "que conectan con el NoData del mar (por ejemplo, lagunas sin retorno LiDAR) también cuentan como mar. La "
        "opción 'también el NoData que toca el borde del raster es mar' puede meter agua desde tierra fuera del "
        "vuelo: úsala con cuidado.\n\n"
        "Incertidumbre: σ del MDT = √(RMSE² − sesgo²); σ total = √(σ MDT² + σ proyección²). El MDT se corrige "
        "restándole el sesgo. Se rellena a nivel − kσ (banda baja), nivel (central) y nivel + kσ (banda alta). Con "
        "errores normales sin sesgo y k = 1,28, la probabilidad de que un píxel esté bajo el agua es ≥ 90 % en la "
        "banda baja, aproximadamente 50–90 % en la central y 10–50 % si solo se inunda en la alta; el valor exacto "
        "en el nivel central sale en el registro y en la tabla de estadísticas. Son valores por píxel: no tienen en "
        "cuenta la conectividad ni la correlación espacial del error del MDT, así que son orientativos.\n\n"
        "Percentiles: las proyecciones del nivel del mar suelen tener la cola alta más larga, y una σ simétrica "
        "puede infravalorar la banda alta. Con 'Percentiles', los valores de los escenarios son las medianas (el "
        "nivel central sigue en la mediana de la proyección) y metes un percentil bajo y uno alto por escenario "
        "(17/83 o 5/95). La proyección se trata como dos medias normales unidas en la mediana (50 % de la masa a "
        "cada lado), ajustadas a los percentiles dados, y se combina con el error del MDT; las "
        "bandas baja y alta son los percentiles de esa suma, así que salen asimétricas. Gesch "
        "(2009, J. Coastal Research SI 53: 49–58) es una referencia para tener en cuenta la incertidumbre vertical "
        "del MDT en mapas de subida del nivel del mar.\n\n"
        "Nivel base: valor uniforme, o un raster (por ejemplo, una superficie de pleamar) donde tenga dato.\n\n"
        "Salidas: GeoTIFF de profundidad del nivel central con estilo azul (.qml al lado) y un GeoPackage con "
        "inundación por bandas, zonas bajas desconectadas clasificadas, estadísticas y metadatos.\n\n"
        "Lo que NO hace: erosión, dinámica, oleaje, drenaje ni freático. Es un modelo estático de umbral con "
        "conectividad.\n\n"
        "Versión {v}. Los parámetros marcados [pendiente] aún no se usan."
    ),
    # --- new in 0.5.0
    "Sea level rise scenarios in m (separated by ';'). With percentiles: the medians":
        "Subidas del nivel del mar en m (separadas por ';'). Con percentiles: las medianas",
    'Projection uncertainty given as':
        'Incertidumbre de la proyección como',
    'Symmetric σ':
        'σ simétrica',
    'Percentiles (asymmetric)':
        'Percentiles (asimétrica)',
    'Percentile pair':
        'Par de percentiles',
    "Low percentile per scenario in m (separated by ';')":
        "Percentil bajo por escenario en m (separados por ';')",
    "High percentile per scenario in m (separated by ';')":
        "Percentil alto por escenario en m (separados por ';')",
    'With percentiles, enter the low and high percentile of every scenario.':
        'Con percentiles, mete el percentil bajo y el alto de cada escenario.',
    'There must be one low and one high percentile per scenario.':
        'Tiene que haber un percentil bajo y uno alto por escenario.',
    'Each scenario needs low percentile ≤ median ≤ high percentile.':
        'Cada escenario necesita percentil bajo ≤ mediana ≤ percentil alto.',
    'DEM σ = {a:.3f} m. Projection given as percentiles {l}/50/{h}; the central level is the median of the projection.':
        'σ del MDT = {a:.3f} m. Proyección en percentiles {l}/50/{h}; el nivel central es la mediana de la proyección.',
    'With percentiles, the projection σ is ignored.':
        'Con percentiles, la σ de la proyección no se usa.',
    '  Percentiles {a:.3f} / {b:.3f} / {c:.3f} m -> bands: level − {d:.3f} m and level + {e:.3f} m.':
        '  Percentiles {a:.3f} / {b:.3f} / {c:.3f} m -> bandas: nivel − {d:.3f} m y nivel + {e:.3f} m.',
    '  Probability of being under water at the central level: {p:.0f} %.':
        '  Probabilidad de estar bajo el agua en el nivel central: {p:.0f} %.',
    # --- new in 0.4.1
    '  No sea point is on a valid pixel below the central level (with the Barrier option, points on NoData do not count): nothing floods.':
        '  Ningún punto de mar está en un píxel con valor por debajo del nivel central (con la opción Barrera, los puntos en NoData no cuentan): no se inunda nada.',
    '  No sea point is on sea NoData or on a valid pixel below the central level: nothing floods.':
        '  Ningún punto de mar está en NoData de mar ni en un píxel con valor por debajo del nivel central: no se inunda nada.',
    '  {a} of {b} sea points are unusable at the central level (on a valid pixel above it, or on NoData with the Barrier option).':
        '  {a} de {b} puntos de mar no sirven en el nivel central (en un píxel con valor por encima, o en NoData con la opción Barrera).',
    '  {a} of {b} sea points are unusable at the central level (on a valid pixel above it).':
        '  {a} de {b} puntos de mar no sirven en el nivel central (en un píxel con valor por encima).',
    '  Nothing floods: no valid pixel below the level connects to the sea.':
        '  No se inunda nada: ningún píxel con valor por debajo del nivel conecta con el mar.',
    '  Nothing floods at the central level: no valid pixel below it connects to the sea. Only the upper band has water.':
        '  No se inunda nada con el nivel central: ningún píxel con valor por debajo conecta con el mar. Solo la banda alta tiene agua.',
    '  The lower band (level {n:.3f} m) is empty: no valid pixel below that level connects to the sea.':
        '  La banda baja (nivel {n:.3f} m) sale vacía: ningún píxel con valor por debajo de ese nivel conecta con el mar.',
    # --- new in 0.4.0
    "NoData handling": "Tratamiento del NoData",
    "Barrier (water cannot pass)": "Barrera (el agua no pasa)",
    "NoData connected to a sea point is sea": "El NoData conectado a un punto de mar es mar",
    "Also NoData touching the raster edge is sea": "También el NoData que toca el borde del raster es mar",
    "Base level raster (m), e.g. high tide surface": "Raster de nivel base (m), p. ej. superficie de pleamar",
    "DEM vertical bias (m, positive = DEM too high)": "Sesgo vertical del MDT (m, positivo = MDT demasiado alto)",
    "The bias cannot be larger than the RMSE (RMSE² = bias² + σ²). Check both values.":
        "El sesgo no puede ser mayor que el RMSE (RMSE² = sesgo² + σ²). Revisa los dos valores.",
    "DEM σ = {a:.3f} m; total σ = {s:.3f} m; k·σ = {d:.3f} m.":
        "σ del MDT = {a:.3f} m; σ total = {s:.3f} m; k·σ = {d:.3f} m.",
    "DEM corrected by a bias of {b:.3f} m.": "MDT corregido con un sesgo de {b:.3f} m.",
    "The base level raster has no data in {p:.1f} % of the DEM. The uniform base level is used there.":
        "El raster de nivel base no tiene dato en {p:.1f} % del MDT. Ahí se usa el nivel base uniforme.",
    "Variable base level: {a:.3f} to {b:.3f} m.": "Nivel base variable: de {a:.3f} a {b:.3f} m.",
    "{n} sea point(s) fall on NoData, which is set as a barrier. If your DEM leaves the sea as NoData, choose "
    "'NoData connected to a sea point is sea'.":
        "{n} punto(s) de mar caen en NoData, que está como barrera. Si tu MDT deja el mar como NoData, elige "
        "'El NoData conectado a un punto de mar es mar'.",
    "NoData treated as sea: {p:.1f} % of the raster.": "NoData tratado como mar: {p:.1f} % del raster.",
    "NoData touching the raster edge is treated as sea. Check that it is really sea and not land outside the survey.":
        "El NoData que toca el borde del raster se trata como mar. Comprueba que de verdad es mar y no tierra "
        "fuera del vuelo.",
    "Scenario +{s} m -> variable level (base level raster + rise)":
        "Escenario +{s} m -> nivel variable (raster de nivel base + subida)",
    # --- validation
    "No sea: pick a point on the map or choose a points layer.":
        "Falta el mar: marca un punto en el mapa o elige una capa de puntos.",
    "No scenarios. Enter values separated by ';'.":
        "No hay ningún escenario. Escribe valores separados por ';'.",
    "Invalid scenario value: '{v}'": "Valor de escenario no válido: '{v}'",
    "You marked a relative rise and also entered subsidence: sinking would be counted twice. "
    "Set subsidence to 0 or choose 'Absolute'.":
        "Has marcado subida relativa y además metes subsidencia: el hundimiento contaría dos "
        "veces. Pon la subsidencia a 0 o marca 'Absoluta'.",
    # --- run messages
    "The DEM must be a file raster read by GDAL.": "El MDT tiene que ser un raster leído por GDAL (archivo).",
    "GDAL cannot open the DEM.": "GDAL no puede abrir el MDT.",
    "The DEM is rotated. Reproject it to a north-up grid.": "El MDT está rotado. Reproyéctalo a una malla norte-arriba.",
    "DEM of {c} x {f} pixels. Estimated memory: {m:.1f} GB.":
        "MDT de {c} x {f} píxeles. Memoria estimada: {m:.1f} GB.",
    "Warning: very large raster. If memory runs out, clip it to the coastal strip or resample.":
        "Ojo: raster muy grande. Si se queda sin memoria, recórtalo a la franja costera o remuestrea.",
    "Connectivity engine: {e}.": "Motor de conectividad: {e}.",
    "pure Python (slow)": "Python puro (lento)",
    "Total σ = {s:.3f} m; k·σ = {d:.3f} m.": "σ total = {s:.3f} m; k·σ = {d:.3f} m.",
    "σ or k is 0: no bands. Everything flooded is labelled 'central'.":
        "σ o k son 0: no hay bandas. Todo lo inundado sale como 'central'.",
    "The subsidence raster has no data in {p:.1f} % of the DEM. Subsidence 0 is used there.":
        "El raster de subsidencia no tiene dato en {p:.1f} % del MDT. Ahí se toma subsidencia 0.",
    "No sea point falls inside the DEM.": "Ningún punto de mar cae dentro del MDT.",
    "Overwriting {r}": "Se sobrescribe {r}",
    "Scenario +{s} m -> level {n:.3f} m above the DEM datum":
        "Escenario +{s} m -> nivel {n:.3f} m sobre el datum del MDT",
    "  No sea point is below the central level or all fall on NoData: central and lower bands empty.":
        "  Ningún punto de mar queda por debajo del nivel central o todos caen en NoData: "
        "bandas central y baja vacías.",
    "  {a} of {b} sea points are unusable at the central level (above it or on NoData).":
        "  {a} de {b} puntos de mar no sirven en el nivel central (por encima o en NoData).",
    "Cancelled.": "Cancelado.",
    "  The lower band (level {n:.3f} m) is empty: sea points lie above it.":
        "  La banda baja (nivel {n:.3f} m) sale vacía: los puntos de mar quedan por encima.",
    "  Bands are not nested. This should not happen: check the data.":
        "  Las bandas no salen anidadas. No debería pasar: revisa los datos.",
    "  Flooded at central level: {t:.4f} km² (lower band {s:.4f}, upper band adds {p:.4f}).":
        "  Inundado con nivel central: {t:.4f} km² (banda baja {s:.4f}, la banda alta añade {p:.4f}).",
    "The DEM has no CRS.": "El MDT no tiene CRS.",
    "The DEM CRS is not in metres. Reproject it (e.g. UTM).":
        "El CRS del MDT no está en metros. Reproyéctalo (p. ej. UTM).",
    "The DEM declares no vertical datum. Make sure rise and base level refer to the same datum as "
    "the DEM heights.":
        "El MDT no declara datum vertical. Asegúrate de que subida y nivel base van referidos al "
        "mismo datum que las cotas del MDT.",
    "Vertical datum: {d}": "Datum vertical: {d}",
    "Not implemented yet: {p}. Ignored in this run.": "Aún no implementado: {p}. Se ignora en esta ejecución.",
    "land use statistics": "estadísticas por usos del suelo",
    "barriers and water passages": "barreras y pasos de agua",
    "{n} sea point(s) fall outside the DEM and are ignored.":
        "{n} punto(s) de mar caen fuera del MDT y se ignoran.",
    "Could not align the subsidence raster with the DEM.":
        "No se ha podido alinear el raster de subsidencia con el MDT.",
    "Cannot write {r}": "No se puede escribir {r}",
    "Could not open {n} to save its style.": "No se ha podido abrir {n} para guardarle el estilo.",
    # --- legend
    "Flooded at level − kσ": "Inundado con nivel − kσ",
    "Flooded at central level": "Inundado con nivel central",
    "Flooded only at level + kσ": "Inundado solo con nivel + kσ",
    "Connects at level + kσ": "Se conecta con nivel + kσ",
    "Isolated": "Aislada",
    "Low only at level + kσ": "Baja solo con nivel + kσ",
    "Plugin style": "Estilo del plugin",
}

"""Processing algorithm: Coastal Inundation Under Climate Change."""
import datetime
import os

import numpy as np
from osgeo import gdal, ogr, osr

from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QColor, QIcon
from qgis.core import (
    Qgis,
    QgsCategorizedSymbolRenderer,
    QgsColorRampShader,
    QgsCoordinateTransform,
    QgsFillSymbol,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingParameterBand,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterMapLayer,
    QgsProcessingParameterNumber,
    QgsProcessingParameterPoint,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
    QgsRasterLayer,
    QgsRasterShader,
    QgsRendererCategory,
    QgsSingleBandPseudoColorRenderer,
    QgsVectorLayer,
)

from . import nucleo
from .i18n import bi, tr

VERSION = "0.5.4"
AUTHOR = ("Daniel Ibarra Marinas, Facultad de Ingeniería y Ciencias, "
          "Universidad Autónoma de Tamaulipas")
NODATA_OUT = -9999.0
DOUBLE = Qgis.ProcessingNumberParameterType.Double

HELP_EN = (
    "Plugin created by Daniel Ibarra Marinas, Facultad de Ingeniería y Ciencias, Universidad Autónoma de "
    "Tamaulipas, to model coastal inundation under sea level rise scenarios. It floods only what lies below "
    "the new level and connects to the sea through pixels that are also below it; low areas without that "
    "connection are stored in a separate layer.\n\n"
    "Sea point: click on the map with the '...' button of the field, or use a points layer (useful when the "
    "sea reaches areas separated by NoData).\n\n"
    "NoData: by default, NoData connected to a sea point is treated as sea, because many coastal DEMs leave "
    "the sea as NoData. Other NoData blocks the water. Inland NoData gaps connected to the sea NoData (e.g. "
    "lagoons without lidar returns) also count as sea. The option 'NoData touching the raster edge is sea' "
    "can bring water in from land outside the survey: use it with care.\n\n"
    "Uncertainty: DEM σ = √(RMSE² − bias²); total σ = √(DEM σ² + projection σ²). The DEM is corrected "
    "by subtracting the bias. Flooding is computed at level − kσ (lower band), level (central) and "
    "level + kσ (upper band). With normal, unbiased errors and k = 1.28, the probability of a pixel being "
    "under water is ≥ 90 % in the lower band, about 50–90 % in the central band and 10–50 % if it floods only in "
    "the upper band; the exact value at the central level is written to the log and to the statistics table. "
    "These are per-pixel values: they ignore connectivity and the spatial correlation of the DEM error, so they "
    "are indicative.\n\n"
    "Percentiles: sea level projections are usually skewed towards high values, and a symmetric σ may "
    "underestimate the upper band. With 'Percentiles', the scenario values are the medians (the central level "
    "stays at the median of the projection) and you enter a low and a high percentile per scenario (17/83 or "
    "5/95). The projection is treated as two half-normals joined at the median (50 % of the mass on each side), "
    "fitted to the given percentiles, and combined with the DEM error; the lower and upper "
    "bands are the percentiles of that sum, so they become asymmetric. Gesch (2009, J. Coastal Research SI 53: 49–58) is a reference for "
    "accounting for DEM vertical uncertainty in sea level rise mapping.\n\n"
    "Base level: uniform value, or a raster (e.g. a high tide surface) where it has data.\n\n"
    "Outputs: central-level depth GeoTIFF with blue style (.qml alongside) and a GeoPackage with flooding "
    "by band, classified low disconnected areas, statistics and metadata.\n\n"
    "What it does NOT do: erosion, dynamics, waves, drainage or groundwater. It is a static threshold "
    "model with connectivity.\n\n"
    "Version {v}. Parameters marked [pending] are not used yet."
)


def _advanced(param):
    param.setFlags(param.flags() | Qgis.ProcessingParameterFlag.Advanced)
    return param


def _parse(text):
    """Scenario parsing with translated errors."""
    try:
        return nucleo.parsear_escenarios(text)
    except ValueError as e:
        if e.args and e.args[0] == "bad_value":
            raise ValueError(tr("Invalid scenario value: '{v}'", v=e.args[1]))
        raise ValueError(tr("No scenarios. Enter values separated by ';'."))


class CoastalInundationAlgorithm(QgsProcessingAlgorithm):
    DEM = "DEM"
    BAND = "BAND"
    POINT = "POINT"
    POINTS = "POINTS"
    SCENARIOS = "SCENARIOS"
    RISE_TYPE = "RISE_TYPE"
    BASE_LEVEL = "BASE_LEVEL"
    BASE_RASTER = "BASE_RASTER"
    NODATA_MODE = "NODATA_MODE"
    DEM_BIAS = "DEM_BIAS"
    SUBS_VALUE = "SUBS_VALUE"
    SUBS_RASTER = "SUBS_RASTER"
    RMSE = "RMSE"
    SIGMA_PROJ = "SIGMA_PROJ"
    PROJ_MODE = "PROJ_MODE"
    PCT_PAIR = "PCT_PAIR"
    P_LOW = "P_LOW"
    P_HIGH = "P_HIGH"
    K = "K"
    LANDUSE = "LANDUSE"
    LANDUSE_FIELD = "LANDUSE_FIELD"
    BARRIERS = "BARRIERS"
    PASSAGES = "PASSAGES"
    CONNECTIVITY = "CONNECTIVITY"
    OUTPUT = "OUTPUT"

    # ------------------------------------------------------------------ meta
    def name(self):
        return "coastal_inundation"

    def displayName(self):
        return "Coastal Inundation Under Climate Change"

    def createInstance(self):
        return CoastalInundationAlgorithm()

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), "icon.png"))

    def shortHelpString(self):
        """Always bilingual: English first, then Spanish."""
        from .i18n import ES
        here = os.path.dirname(__file__)
        logos = "".join(
            f'<img src="{QUrl.fromLocalFile(os.path.join(here, png)).toString()}" width="{w}" height="64"> '
            for png, w in (("logo_uat.png", 105), ("logo_facultad.png", 64), ("logo_plugin.png", 64)))
        html = lambda s: s.replace("\n", "<br>")
        en = HELP_EN.format(v=VERSION)
        es = ES["HELP"].format(v=VERSION)
        rg = "https://www.researchgate.net/profile/Daniel-Ibarra-Marinas"
        orcid = "https://orcid.org/0000-0003-3683-4456"
        return (f"<p>{logos}</p><p>{html(en)}</p>"
                f'<p>More information: <a href="{rg}">Daniel Ibarra Marinas on ResearchGate</a> · '
                f'ORCID: <a href="{orcid}">0000-0003-3683-4456</a></p>'
                f"<p>&nbsp;</p><p>{html(es)}</p>"
                f'<p>Más información: <a href="{rg}">Daniel Ibarra Marinas en ResearchGate</a> · '
                f'ORCID: <a href="{orcid}">0000-0003-3683-4456</a></p>')

    # ------------------------------------------------------------ parameters
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DEM, bi("Coastal DEM (CRS in metres)")))
        self.addParameter(QgsProcessingParameterBand(
            self.BAND, bi("Band"), 1, self.DEM))
        self.addParameter(QgsProcessingParameterPoint(
            self.POINT, bi("Sea point (click on the map)"), optional=True))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.POINTS, bi("Sea points layer (optional)"),
            [Qgis.ProcessingSourceType.VectorPoint], optional=True))
        self.addParameter(QgsProcessingParameterEnum(
            self.NODATA_MODE, bi("NoData handling"),
            [bi("Barrier (water cannot pass)"),
             bi("NoData connected to a sea point is sea"),
             bi("Also NoData touching the raster edge is sea")], defaultValue=1))
        self.addParameter(QgsProcessingParameterString(
            self.SCENARIOS, bi("Sea level rise scenarios in m (separated by ';'). With percentiles: the medians"),
            defaultValue="1"))
        self.addParameter(QgsProcessingParameterEnum(
            self.RISE_TYPE, bi("The rise you enter is..."),
            [bi("Relative (already includes vertical land motion)"),
             bi("Absolute (no vertical land motion)")], defaultValue=0))
        self.addParameter(QgsProcessingParameterNumber(
            self.BASE_LEVEL, bi("Base level above the DEM vertical datum (m), e.g. high tide"),
            DOUBLE, 0.0))
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.BASE_RASTER, bi("Base level raster (m), e.g. high tide surface"), optional=True))
        self.addParameter(QgsProcessingParameterNumber(
            self.SUBS_VALUE, bi("Uniform subsidence (m, positive = sinking). Absolute rise only"),
            DOUBLE, 0.0))
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.SUBS_RASTER, bi("Subsidence raster (m). Absolute rise only"), optional=True))
        self.addParameter(QgsProcessingParameterNumber(
            self.RMSE, bi("DEM vertical RMSE (m)"), DOUBLE, 0.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.DEM_BIAS, bi("DEM vertical bias (m, positive = DEM too high)"), DOUBLE, 0.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.SIGMA_PROJ, bi("Projection σ (m), 0 if unknown"), DOUBLE, 0.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterEnum(
            self.PROJ_MODE, bi("Projection uncertainty given as"),
            [bi("Symmetric σ"), bi("Percentiles (asymmetric)")], defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(
            self.PCT_PAIR, bi("Percentile pair"), ["17 / 83", "5 / 95"], defaultValue=0))
        self.addParameter(QgsProcessingParameterString(
            self.P_LOW, bi("Low percentile per scenario in m (separated by ';')"), optional=True))
        self.addParameter(QgsProcessingParameterString(
            self.P_HIGH, bi("High percentile per scenario in m (separated by ';')"), optional=True))
        self.addParameter(_advanced(QgsProcessingParameterNumber(
            self.K, bi("Band factor k"), DOUBLE, 1.28, minValue=0.0)))
        self.addParameter(_advanced(QgsProcessingParameterMapLayer(
            self.LANDUSE, bi("[pending] Land use (raster or polygons)"), optional=True,
            types=[Qgis.ProcessingSourceType.Raster, Qgis.ProcessingSourceType.VectorPolygon])))
        self.addParameter(_advanced(QgsProcessingParameterString(
            self.LANDUSE_FIELD, bi("[pending] Class field (if vector)"), optional=True)))
        self.addParameter(_advanced(QgsProcessingParameterFeatureSource(
            self.BARRIERS, bi("[pending] Barriers (lines)"),
            [Qgis.ProcessingSourceType.VectorLine], optional=True)))
        self.addParameter(_advanced(QgsProcessingParameterFeatureSource(
            self.PASSAGES, bi("[pending] Water passages or culverts (lines)"),
            [Qgis.ProcessingSourceType.VectorLine], optional=True)))
        self.addParameter(_advanced(QgsProcessingParameterEnum(
            self.CONNECTIVITY, bi("Connectivity"),
            [bi("4 neighbours (conservative)"), bi("8 neighbours")], defaultValue=0)))
        self.addParameter(QgsProcessingParameterFolderDestination(
            self.OUTPUT, bi("Output folder")))

    # ----------------------------------------------------------- validation
    def checkParameterValues(self, parameters, context):
        ok, msg = super().checkParameterValues(parameters, context)
        if not ok:
            return ok, msg
        if parameters.get(self.POINT) in (None, "") and parameters.get(self.POINTS) in (None, ""):
            return False, tr("No sea: pick a point on the map or choose a points layer.")
        try:
            meds = _parse(self.parameterAsString(parameters, self.SCENARIOS, context))
        except ValueError as e:
            return False, str(e)
        rel = self.parameterAsEnum(parameters, self.RISE_TYPE, context) == 0
        subs = self.parameterAsDouble(parameters, self.SUBS_VALUE, context)
        if rel and (subs != 0 or parameters.get(self.SUBS_RASTER) not in (None, "")):
            return False, tr(
                "You marked a relative rise and also entered subsidence: sinking would be counted "
                "twice. Set subsidence to 0 or choose 'Absolute'.")
        rmse = self.parameterAsDouble(parameters, self.RMSE, context)
        bias = self.parameterAsDouble(parameters, self.DEM_BIAS, context)
        if abs(bias) > rmse:
            return False, tr("The bias cannot be larger than the RMSE (RMSE² = bias² + σ²). Check both values.")
        if self.parameterAsEnum(parameters, self.PROJ_MODE, context) == 1:
            try:
                lows = nucleo.parsear_escenarios(self.parameterAsString(parameters, self.P_LOW, context))
                highs = nucleo.parsear_escenarios(self.parameterAsString(parameters, self.P_HIGH, context))
            except ValueError:
                return False, tr("With percentiles, enter the low and high percentile of every scenario.")
            if not (len(lows) == len(highs) == len(meds)):
                return False, tr("There must be one low and one high percentile per scenario.")
            if any(not (lo <= md <= hi) for lo, md, hi in zip(lows, meds, highs)):
                return False, tr("Each scenario needs low percentile ≤ median ≤ high percentile.")
        return True, ""

    # -------------------------------------------------------------- process
    def processAlgorithm(self, parameters, context, feedback):
        dem_layer = self.parameterAsRasterLayer(parameters, self.DEM, context)
        if dem_layer is None or dem_layer.providerType() != "gdal":
            raise QgsProcessingException(tr("The DEM must be a file raster read by GDAL."))
        crs = dem_layer.crs()
        self._check_crs(crs, feedback)
        self._warn_pending(parameters, feedback)

        scenarios = _parse(self.parameterAsString(parameters, self.SCENARIOS, context))
        absolute = self.parameterAsEnum(parameters, self.RISE_TYPE, context) == 1
        base = self.parameterAsDouble(parameters, self.BASE_LEVEL, context)
        eight = self.parameterAsEnum(parameters, self.CONNECTIVITY, context) == 1
        rmse = self.parameterAsDouble(parameters, self.RMSE, context)
        sigma_proj = self.parameterAsDouble(parameters, self.SIGMA_PROJ, context)
        k = self.parameterAsDouble(parameters, self.K, context)
        bias = self.parameterAsDouble(parameters, self.DEM_BIAS, context)
        sigma_dem = nucleo.sigma_mdt(rmse, bias)
        nodata_mode = self.parameterAsEnum(parameters, self.NODATA_MODE, context)
        pct_mode = self.parameterAsEnum(parameters, self.PROJ_MODE, context) == 1
        if pct_mode:
            sigma = None
            p_lo_pct, p_hi_pct, z_pair = nucleo.PARES[self.parameterAsEnum(parameters, self.PCT_PAIR, context)]
            p_lows = nucleo.parsear_escenarios(self.parameterAsString(parameters, self.P_LOW, context))
            p_highs = nucleo.parsear_escenarios(self.parameterAsString(parameters, self.P_HIGH, context))
            feedback.pushInfo(tr("DEM σ = {a:.3f} m. Projection given as percentiles {l}/50/{h}; the central "
                                 "level is the median of the projection.", a=sigma_dem, l=p_lo_pct, h=p_hi_pct))
            if sigma_proj:
                feedback.pushWarning(tr("With percentiles, the projection σ is ignored."))
        else:
            sigma = nucleo.sigma_total(sigma_dem, sigma_proj)
            if k * sigma > 0:
                feedback.pushInfo(tr("DEM σ = {a:.3f} m; total σ = {s:.3f} m; k·σ = {d:.3f} m.",
                                     a=sigma_dem, s=sigma, d=k * sigma))
            else:
                feedback.pushWarning(tr("σ or k is 0: no bands. Everything flooded is labelled 'central'."))
        folder = self.parameterAsString(parameters, self.OUTPUT, context)
        os.makedirs(folder, exist_ok=True)

        # --- read DEM
        ds = gdal.Open(dem_layer.source())
        if ds is None:
            raise QgsProcessingException(tr("GDAL cannot open the DEM."))
        gt = ds.GetGeoTransform()
        if gt[2] != 0 or gt[4] != 0:
            raise QgsProcessingException(tr("The DEM is rotated. Reproject it to a north-up grid."))
        rows, cols = ds.RasterYSize, ds.RasterXSize
        wkt = ds.GetProjection()
        mem = nucleo.estimar_memoria_bytes(rows, cols)
        feedback.pushInfo(tr("DEM of {c} x {f} pixels. Estimated memory: {m:.1f} GB.",
                             c=cols, f=rows, m=mem / 1024**3))
        if mem > 4 * 1024**3:
            feedback.pushWarning(tr("Warning: very large raster. If memory runs out, clip it to the "
                                    "coastal strip or resample."))
        band = ds.GetRasterBand(self.parameterAsInt(parameters, self.BAND, context))
        raw = band.ReadAsArray()
        valid = nucleo.mascara_validos(raw, band.GetNoDataValue())
        dem = raw.astype(np.float32, copy=False)
        del raw
        ds = None
        feedback.pushInfo(tr("Connectivity engine: {e}.",
                             e="scipy" if nucleo.HAY_SCIPY else tr("pure Python (slow)")))

        # --- bias correction
        dem_eff = dem - np.float32(bias) if bias else dem
        if bias:
            feedback.pushInfo(tr("DEM corrected by a bias of {b:.3f} m.", b=bias))

        # --- base level (uniform or raster)
        base_arr = None
        base_layer = self.parameterAsRasterLayer(parameters, self.BASE_RASTER, context)
        if base_layer is not None:
            arr = self._read_aligned(base_layer.source(), gt, rows, cols, wkt)
            missing = ~np.isfinite(arr) & valid
            if missing.any():
                feedback.pushWarning(tr("The base level raster has no data in {p:.1f} % of the DEM. The uniform "
                                        "base level is used there.", p=100 * missing.sum() / valid.sum()))
            base_arr = np.where(np.isfinite(arr), arr, np.float32(base)).astype(np.float32)
            feedback.pushInfo(tr("Variable base level: {a:.3f} to {b:.3f} m.",
                                 a=float(base_arr[valid].min()), b=float(base_arr[valid].max())))

        # --- subsidence (absolute rise only)
        if absolute:
            subs_value = self.parameterAsDouble(parameters, self.SUBS_VALUE, context)
            subs_layer = self.parameterAsRasterLayer(parameters, self.SUBS_RASTER, context)
            if subs_value:
                dem_eff = dem_eff - np.float32(subs_value)
            if subs_layer is not None:
                arr = self._read_aligned(subs_layer.source(), gt, rows, cols, wkt)
                missing = ~np.isfinite(arr) & valid
                if missing.any():
                    feedback.pushWarning(tr(
                        "The subsidence raster has no data in {p:.1f} % of the DEM. Subsidence 0 is "
                        "used there.", p=100 * missing.sum() / valid.sum()))
                dem_eff = dem_eff - np.nan_to_num(arr, nan=0.0)

        # --- seeds
        seeds = self._read_seeds(parameters, context, crs, gt, rows, cols, feedback)
        if not seeds:
            raise QgsProcessingException(tr("No sea point falls inside the DEM."))
        on_nodata = sum(1 for f, c in seeds if not valid[f, c])
        if on_nodata and nodata_mode == 0:
            feedback.pushWarning(tr("{n} sea point(s) fall on NoData, which is set as a barrier. If your DEM "
                                    "leaves the sea as NoData, choose 'NoData connected to a sea point is sea'.",
                                    n=on_nodata))
        sea = nucleo.mar_nodata(valid, seeds, nodata_mode, eight)
        if sea.any():
            feedback.pushInfo(tr("NoData treated as sea: {p:.1f} % of the raster.", p=100 * sea.mean()))
        if nodata_mode == 2:
            feedback.pushWarning(tr("NoData touching the raster edge is treated as sea. Check that it is really "
                                    "sea and not land outside the survey."))

        # --- scenarios
        gpkg_path = os.path.join(folder, "inundation.gpkg")
        if os.path.exists(gpkg_path):
            feedback.pushWarning(tr("Overwriting {r}", r=gpkg_path))
            os.remove(gpkg_path)
        gpkg = ogr.GetDriverByName("GPKG").CreateDataSource(gpkg_path)
        srs = osr.SpatialReference(wkt=wkt)
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        px_area = abs(gt[1] * gt[5])

        stats, vect_layers, rasters = [], [], []
        for i, rise in enumerate(scenarios):
            if feedback.isCanceled():
                break
            level = (base_arr + np.float32(rise)) if base_arr is not None else base + rise
            level_m = None if base_arr is not None else base + rise
            level_min = float(base_arr[valid].min()) + rise if base_arr is not None else base + rise
            tag = nucleo.etiqueta_escenario(rise)
            if level_m is None:
                feedback.pushInfo(tr("Scenario +{s} m -> variable level (base level raster + rise)", s=rise))
            else:
                feedback.pushInfo(tr("Scenario +{s} m -> level {n:.3f} m above the DEM datum", s=rise, n=level_m))

            if pct_mode:
                d_lo, d_hi, p_central = nucleo.bandas_percentiles(
                    p_lows[i], rise, p_highs[i], z_pair, sigma_dem, k)
                feedback.pushInfo(tr("  Percentiles {a:.3f} / {b:.3f} / {c:.3f} m -> bands: level − {d:.3f} m and "
                                     "level + {e:.3f} m.", a=p_lows[i], b=rise, c=p_highs[i], d=d_lo, e=d_hi))
            else:
                d_lo = d_hi = k * sigma
                p_central = 0.5 if sigma > 0 else None
            if p_central is not None:
                feedback.pushInfo(tr("  Probability of being under water at the central level: {p:.0f} %.",
                                     p=100 * p_central))

            n_ok = nucleo.semillas_utiles(seeds, valid, dem_eff, level, sea)
            if n_ok == 0:
                if nodata_mode == 0:
                    feedback.pushWarning(tr("  No sea point is on a valid pixel below the central level (with the "
                                            "Barrier option, points on NoData do not count): nothing floods."))
                else:
                    feedback.pushWarning(tr("  No sea point is on sea NoData or on a valid pixel below the central "
                                            "level: nothing floods."))
            elif n_ok < len(seeds):
                if nodata_mode == 0:
                    feedback.pushWarning(tr("  {a} of {b} sea points are unusable at the central level (on a valid "
                                            "pixel above it, or on NoData with the Barrier option).",
                                            a=len(seeds) - n_ok, b=len(seeds)))
                else:
                    feedback.pushWarning(tr("  {a} of {b} sea points are unusable at the central level (on a valid "
                                            "pixel above it).", a=len(seeds) - n_ok, b=len(seeds)))
            try:
                bands, status, depth, info = nucleo.calcular_bandas(
                    dem_eff, valid, level, d_lo, seeds, eight, feedback.isCanceled, mar=sea, delta_alto=d_hi)
            except InterruptedError:
                raise QgsProcessingException(tr("Cancelled."))
            if n_ok and not (bands > 0).any():
                feedback.pushWarning(tr("  Nothing floods: no valid pixel below the level connects to the sea."))
            elif n_ok and not (bands == 2).any() and not (bands == 1).any():
                feedback.pushWarning(tr("  Nothing floods at the central level: no valid pixel below it connects "
                                        "to the sea. Only the upper band has water."))
            elif info.get("bandas") and info["seguro_vacio"] and n_ok:
                feedback.pushWarning(tr("  The lower band (level {n:.3f} m) is empty: no valid pixel below that "
                                        "level connects to the sea.", n=level_min - d_lo))

            # A) depth raster (central level)
            tif = os.path.join(folder, f"depth_{tag}.tif")
            self._write_tif(tif, depth, gt, wkt)
            max_d = float(np.nanpercentile(depth, 98)) if np.isfinite(depth).any() else 1.0
            self._style_raster(tif, max(max_d, 0.01))
            rasters.append((tif, f"depth_{tag}"))

            # B) polygons
            n_flood, n_disc = f"flood_{tag}", f"disconnected_{tag}"
            self._polygonize(gpkg, n_flood, bands, "band", nucleo.BANDAS, gt, wkt, srs, eight, rise, level_m)
            self._polygonize(gpkg, n_disc, status, "status", nucleo.SITUACIONES, gt, wkt, srs, eight,
                             rise, level_m)
            vect_layers += [(n_flood, "band"), (n_disc, "status")]

            areas = {f"flood_{v}_m2": float((bands == c).sum() * px_area) for c, v in nucleo.BANDAS.items()}
            areas.update({f"disc_{v}_m2": float((status == c).sum() * px_area)
                          for c, v in nucleo.SITUACIONES.items()})
            total = areas["flood_lower_m2"] + areas["flood_central_m2"]
            row = {"rise_m": rise, "level_m": level_m, "sigma_m": sigma, "dem_sigma_m": sigma_dem, "k": k,
                   "p_low_m": p_lows[i] if pct_mode else None, "p_high_m": p_highs[i] if pct_mode else None,
                   "band_lower_offset_m": d_lo, "band_upper_offset_m": d_hi, "prob_at_central": p_central,
                   "flood_total_central_m2": total}
            row.update(areas)
            stats.append(row)
            feedback.pushInfo(tr("  Flooded at central level: {t:.4f} km² (lower band {s:.4f}, upper band "
                                 "adds {p:.4f}).", t=total / 1e6, s=areas["flood_lower_m2"] / 1e6,
                                 p=areas["flood_upper_m2"] / 1e6))
            feedback.setProgress(100.0 * (i + 1) / len(scenarios))

        self._stats_table(gpkg, stats)
        self._metadata_table(gpkg, dem_layer, crs, parameters, context, scenarios, eight)
        gpkg = None  # close before saving styles

        for name, field in vect_layers:
            self._style_vector(gpkg_path, name, field, feedback)
            det = QgsProcessingContext.LayerDetails(name, context.project(), name)
            context.addLayerToLoadOnCompletion(f"{gpkg_path}|layername={name}", det)
        for path, name in rasters:
            det = QgsProcessingContext.LayerDetails(name, context.project(), name)
            context.addLayerToLoadOnCompletion(path, det)
        return {self.OUTPUT: folder}

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _check_crs(crs, feedback):
        if not crs.isValid():
            raise QgsProcessingException(tr("The DEM has no CRS."))
        if crs.isGeographic() or crs.mapUnits() != Qgis.DistanceUnit.Meters:
            raise QgsProcessingException(tr("The DEM CRS is not in metres. Reproject it (e.g. UTM)."))
        vertical = crs.verticalCrs() if hasattr(crs, "verticalCrs") else None
        if vertical is None or not vertical.isValid():
            feedback.pushWarning(tr("The DEM declares no vertical datum. Make sure rise and base level "
                                    "refer to the same datum as the DEM heights."))
        else:
            feedback.pushInfo(tr("Vertical datum: {d}", d=vertical.description()))

    def _warn_pending(self, parameters, feedback):
        pending = []
        if parameters.get(self.LANDUSE) not in (None, ""):
            pending.append(tr("land use statistics"))
        if parameters.get(self.BARRIERS) not in (None, "") or parameters.get(self.PASSAGES) not in (None, ""):
            pending.append(tr("barriers and water passages"))
        for p in pending:
            feedback.pushWarning(tr("Not implemented yet: {p}. Ignored in this run.", p=p))

    def _read_seeds(self, parameters, context, crs, gt, rows, cols, feedback):
        xy = []
        if parameters.get(self.POINT) not in (None, ""):
            p = self.parameterAsPoint(parameters, self.POINT, context, crs)
            xy.append((p.x(), p.y()))
        source = self.parameterAsSource(parameters, self.POINTS, context)
        if source is not None:
            tr_ = QgsCoordinateTransform(source.sourceCrs(), crs, context.transformContext())
            for f in source.getFeatures():
                g = f.geometry()
                if g.isEmpty():
                    continue
                g.transform(tr_)
                xy += [(v.x(), v.y()) for v in g.vertices()]
        seeds = []
        for x, y in xy:
            c = int(np.floor((x - gt[0]) / gt[1]))
            f = int(np.floor((y - gt[3]) / gt[5]))
            if 0 <= f < rows and 0 <= c < cols:
                seeds.append((f, c))
        if len(seeds) < len(xy):
            feedback.pushWarning(tr("{n} sea point(s) fall outside the DEM and are ignored.",
                                    n=len(xy) - len(seeds)))
        return seeds

    @staticmethod
    def _read_aligned(path, gt, rows, cols, wkt):
        xmin, ymax = gt[0], gt[3]
        xmax, ymin = gt[0] + cols * gt[1], gt[3] + rows * gt[5]
        opts = gdal.WarpOptions(format="MEM", outputBounds=(xmin, ymin, xmax, ymax),
                                width=cols, height=rows, dstSRS=wkt, resampleAlg="bilinear",
                                outputType=gdal.GDT_Float32, dstNodata=float("nan"))
        ds = gdal.Warp("", path, options=opts)
        if ds is None:
            raise QgsProcessingException(tr("Could not align the subsidence raster with the DEM."))
        b = ds.GetRasterBand(1)
        arr = b.ReadAsArray().astype(np.float32)
        nd = b.GetNoDataValue()
        if nd is not None and np.isfinite(nd):
            arr[arr == nd] = np.nan
        return arr

    @staticmethod
    def _write_tif(path, depth, gt, wkt):
        rows, cols = depth.shape
        ds = gdal.GetDriverByName("GTiff").Create(
            path, cols, rows, 1, gdal.GDT_Float32,
            options=["COMPRESS=DEFLATE", "PREDICTOR=3", "TILED=YES"])
        if ds is None:
            raise QgsProcessingException(tr("Cannot write {r}", r=path))
        ds.SetGeoTransform(gt)
        ds.SetProjection(wkt)
        b = ds.GetRasterBand(1)
        b.SetNoDataValue(NODATA_OUT)
        b.WriteArray(np.where(np.isfinite(depth), depth, NODATA_OUT).astype(np.float32))
        b.FlushCache()
        ds = None

    @staticmethod
    def _style_raster(tif, max_d):
        layer = QgsRasterLayer(tif, "tmp")
        ramp = QgsColorRampShader(0.0, max_d)
        ramp.setColorRampType(Qgis.ShaderInterpolationMethod.Linear)
        ramp.setColorRampItemList([
            QgsColorRampShader.ColorRampItem(0.0, QColor(198, 219, 239, 110), "0 m"),
            QgsColorRampShader.ColorRampItem(max_d / 2, QColor(66, 146, 198, 170), f"{max_d / 2:.2f} m"),
            QgsColorRampShader.ColorRampItem(max_d, QColor(8, 48, 107, 220), f"≥ {max_d:.2f} m"),
        ])
        shader = QgsRasterShader()
        shader.setRasterShaderFunction(ramp)
        renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, shader)
        renderer.setClassificationMin(0.0)
        renderer.setClassificationMax(max_d)
        layer.setRenderer(renderer)
        layer.saveNamedStyle(os.path.splitext(tif)[0] + ".qml")

    @staticmethod
    def _polygonize(gpkg, name, classes, class_field, labels, gt, wkt, srs, eight, rise, level):
        rows, cols = classes.shape
        mem = gdal.GetDriverByName("MEM").Create("", cols, rows, 1, gdal.GDT_Byte)
        mem.SetGeoTransform(gt)
        mem.SetProjection(wkt)
        b = mem.GetRasterBand(1)
        b.WriteArray(classes)
        lyr = gpkg.CreateLayer(name, srs, ogr.wkbPolygon, ["GEOMETRY_NAME=geom", "FID=fid"])
        for fld, ftype in (("value", ogr.OFTInteger), (class_field, ogr.OFTString),
                           ("rise_m", ogr.OFTReal), ("level_m", ogr.OFTReal), ("area_m2", ogr.OFTReal)):
            lyr.CreateField(ogr.FieldDefn(fld, ftype))
        lyr.StartTransaction()
        gdal.Polygonize(b, b, lyr, 0, ["8CONNECTED=8"] if eight else [])  # 0 is masked out
        lyr.ResetReading()
        feat = lyr.GetNextFeature()
        while feat is not None:
            feat.SetField(class_field, labels.get(feat.GetField("value"), ""))
            feat.SetField("rise_m", rise)
            if level is None:
                feat.SetFieldNull("level_m")
            else:
                feat.SetField("level_m", level)
            feat.SetField("area_m2", feat.GetGeometryRef().GetArea())
            lyr.SetFeature(feat)
            feat = lyr.GetNextFeature()
        lyr.CommitTransaction()
        mem = None

    @staticmethod
    def _stats_table(gpkg, rows_):
        t = gpkg.CreateLayer("statistics", geom_type=ogr.wkbNone)
        fields = ["rise_m", "level_m", "sigma_m", "dem_sigma_m", "k", "p_low_m", "p_high_m",
                  "band_lower_offset_m", "band_upper_offset_m", "prob_at_central", "flood_total_central_m2"]
        fields += [f"flood_{v}_m2" for v in nucleo.BANDAS.values()]
        fields += [f"disc_{v}_m2" for v in nucleo.SITUACIONES.values()]
        for fld in fields:
            t.CreateField(ogr.FieldDefn(fld, ogr.OFTReal))
        for row in rows_:
            f = ogr.Feature(t.GetLayerDefn())
            for fld in fields:
                val = row.get(fld)
                if val is None:
                    f.SetFieldNull(fld)
                else:
                    f.SetField(fld, float(val))
            t.CreateFeature(f)

    def _metadata_table(self, gpkg, dem_layer, crs, parameters, context, scenarios, eight):
        vertical = crs.verticalCrs() if hasattr(crs, "verticalCrs") else None
        absolute = self.parameterAsEnum(parameters, self.RISE_TYPE, context) == 1
        pairs = [
            ("plugin", "Coastal Inundation Under Climate Change"),
            ("plugin_version", VERSION),
            ("author", AUTHOR),
            ("author_orcid", "https://orcid.org/0000-0003-3683-4456"),
            ("date", datetime.datetime.now().isoformat(timespec="seconds")),
            ("dem", dem_layer.source()),
            ("crs", crs.authid()),
            ("vertical_datum", vertical.description() if vertical and vertical.isValid() else "NOT DECLARED"),
            ("scenarios_m", "; ".join(str(s) for s in scenarios)),
            ("rise_type", "absolute" if absolute else "relative"),
            ("base_level_m", str(self.parameterAsDouble(parameters, self.BASE_LEVEL, context))),
            ("subsidence_m", str(self.parameterAsDouble(parameters, self.SUBS_VALUE, context))),
            ("subsidence_raster", str(parameters.get(self.SUBS_RASTER) or "")),
            ("connectivity", "8 neighbours" if eight else "4 neighbours"),
            ("nodata", ["barrier (water cannot pass)", "NoData connected to a sea point is sea",
                        "NoData connected to a sea point or touching the raster edge is sea"][
                self.parameterAsEnum(parameters, self.NODATA_MODE, context)]
             + "; sea NoData is not counted as flooded and stays NoData in the depth raster"),
            ("base_level_raster", str(parameters.get(self.BASE_RASTER) or "")),
            ("level_m", "null when a base level raster is used (the level varies by pixel)"),
            ("engine", "scipy.ndimage.label" if nucleo.HAY_SCIPY else "python BFS"),
            ("dem_rmse_m", str(self.parameterAsDouble(parameters, self.RMSE, context))),
            ("dem_bias_m", str(self.parameterAsDouble(parameters, self.DEM_BIAS, context))),
            ("dem_sigma_m", "sqrt(rmse^2 - bias^2); the DEM is corrected by subtracting the bias"),
            ("projection_uncertainty", "percentiles" if self.parameterAsEnum(parameters, self.PROJ_MODE, context) == 1
             else "symmetric sigma"),
            ("projection_sigma_m", str(self.parameterAsDouble(parameters, self.SIGMA_PROJ, context))),
            ("percentile_pair", ["17/83", "5/95"][self.parameterAsEnum(parameters, self.PCT_PAIR, context)]),
            ("percentiles_low_m", self.parameterAsString(parameters, self.P_LOW, context) or ""),
            ("percentiles_high_m", self.parameterAsString(parameters, self.P_HIGH, context) or ""),
            ("percentile_method", "Scenario values are the medians and give the central level. The projection is "
                                  "modelled as two half-normals joined at the median (50 % of the mass on each side, "
                                  "one sigma per side fitted to the given percentiles). This is not the classical "
                                  "two-piece split normal, whose junction is the mode: this form reproduces the given "
                                  "median and percentiles exactly, at the cost of a jump in the density at the median. "
                                  "It is "
                                  "added numerically to the DEM error N(0, dem_sigma). The lower and upper band levels "
                                  "are the quantiles 1-Phi(k) and Phi(k) of that sum. Beyond the given percentiles the "
                                  "tails are an extrapolation. prob_at_central in statistics is P(sum > median)."),
            ("k", str(self.parameterAsDouble(parameters, self.K, context))),
            ("uncertainty", "total sigma = sqrt(dem_sigma^2 + projection_sigma^2), errors assumed independent, "
                            "normal and unbiased after correction. Bands: lower = level - k*sigma, central = level, "
                            "upper = level + k*sigma (with percentiles, see percentile_method). Per-pixel probability of being "
                            "under water with k = 1.28: lower >= 90 %, central about 50-90 % (exact value at the "
                            "central level in statistics.prob_at_central), upper only 10-50 %. Ignores connectivity and spatial "
                            "correlation of the DEM error: indicative only. The projection sigma is symmetric; "
                            "skewed projections (longer upper tail) may make the upper band too narrow. Reference for DEM vertical uncertainty in "
                            "SLR mapping: Gesch (2009), J. Coastal Research SI 53: 49-58, doi:10.2112/SI53-006.1."),
            ("areas", "flood_* and disc_* are exclusive within each table, but the tables overlap: every "
                      "disc_connects_at_upper pixel is also counted in flood_upper. Do not add them together. "
                      "flood_total_central = lower + central."),
            ("limitations", "Static threshold model with connectivity. No erosion, dynamics, waves, "
                            "drainage or groundwater."),
        ]
        t = gpkg.CreateLayer("metadata", geom_type=ogr.wkbNone)
        t.CreateField(ogr.FieldDefn("key", ogr.OFTString))
        t.CreateField(ogr.FieldDefn("value", ogr.OFTString))
        for key, val in pairs:
            f = ogr.Feature(t.GetLayerDefn())
            f.SetField("key", key)
            f.SetField("value", val)
            t.CreateFeature(f)

    @staticmethod
    def _style_vector(gpkg_path, name, field, feedback):
        layer = QgsVectorLayer(f"{gpkg_path}|layername={name}", name, "ogr")
        if not layer.isValid():
            feedback.pushWarning(tr("Could not open {n} to save its style.", n=name))
            return
        if field == "band":
            colours = [("lower", "8,48,107,170", tr("Flooded at level − kσ")),
                       ("central", "33,113,181,130", tr("Flooded at central level")),
                       ("upper", "107,174,214,90", tr("Flooded only at level + kσ"))]
            outline = "8,48,107,200"
        else:
            colours = [("connects_at_upper", "217,72,1,160", tr("Connects at level + kσ")),
                       ("isolated", "253,141,60,120", tr("Isolated")),
                       ("low_only_at_upper", "253,208,162,100", tr("Low only at level + kσ"))]
            outline = "166,54,3,200"
        cats = []
        for value, colour, label in colours:
            sym = QgsFillSymbol.createSimple({"color": colour, "outline_color": outline, "outline_width": "0.1"})
            cats.append(QgsRendererCategory(value, sym, label))
        layer.setRenderer(QgsCategorizedSymbolRenderer(field, cats))
        if hasattr(layer, "saveStyleToDatabaseV2"):
            layer.saveStyleToDatabaseV2(name, tr("Plugin style"), True, "")
        else:
            layer.saveStyleToDatabase(name, tr("Plugin style"), True, "")

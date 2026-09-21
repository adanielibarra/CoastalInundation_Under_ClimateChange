"""Cálculos del plugin sin dependencias de QGIS (se pueden probar aparte)."""
from collections import deque

import numpy as np

try:
    from scipy import ndimage
    HAY_SCIPY = True
except ImportError:
    HAY_SCIPY = False


def parsear_escenarios(texto):
    """'0,5; 1; 2' -> [0.5, 1.0, 2.0]. Acepta coma o punto decimal."""
    valores = []
    for trozo in (texto or "").split(";"):
        t = trozo.strip().replace(",", ".")
        if not t:
            continue
        try:
            valores.append(float(t))
        except ValueError:
            raise ValueError("bad_value", trozo.strip())
    if not valores:
        raise ValueError("empty")
    return valores


def etiqueta_escenario(subida):
    """1.0 -> '1_00m' (para nombres de capa y archivo)."""
    txt = f"{abs(subida):.2f}".replace(".", "_") + "m"
    return ("minus" + txt) if subida < 0 else txt


def mascara_validos(dem, nodata):
    validos = np.isfinite(dem)
    if nodata is not None:
        validos &= dem != nodata
    return validos


def estimar_memoria_bytes(filas, cols):
    """Estimación gruesa: unos 30 bytes por píxel entre arrays y temporales."""
    return int(filas) * int(cols) * 30


def relleno_conectado(bajo, semillas, ocho_vecinos=False, cancelado=None,
                      usar_scipy=None, fuentes=None):
    """bajo: array bool 2D (píxel válido y por debajo del nivel).
    semillas: lista de (fila, col). Devuelve bool 2D con lo conectado a
    alguna semilla. NoData no deja pasar el agua (va como False en 'bajo')."""
    filas, cols = bajo.shape
    ok = [(f, c) for f, c in semillas
          if 0 <= f < filas and 0 <= c < cols and bajo[f, c]]
    hay_fuentes = fuentes is not None and bool((fuentes & bajo).any())
    if not ok and not hay_fuentes:
        return np.zeros((filas, cols), dtype=bool)
    if usar_scipy is None:
        usar_scipy = HAY_SCIPY
    if usar_scipy:
        estructura = ndimage.generate_binary_structure(2, 2 if ocho_vecinos else 1)
        etiquetas, _ = ndimage.label(bajo, structure=estructura)
        ids = [etiquetas[f, c] for f, c in ok]
        if hay_fuentes:
            ids += list(np.unique(etiquetas[fuentes & bajo]))
        ids = np.unique(ids)
        return np.isin(etiquetas, ids[ids > 0])
    if hay_fuentes:
        ok += [tuple(p) for p in np.argwhere(fuentes & bajo)]
    return _relleno_python(bajo, ok, ocho_vecinos, cancelado)


def _relleno_python(bajo, semillas, ocho_vecinos, cancelado):
    """Plan B sin scipy: recorrido en anchura. Lento en rasters grandes."""
    filas, cols = bajo.shape
    salida = np.zeros((filas, cols), dtype=bool)
    vecinos = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if ocho_vecinos:
        vecinos += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    cola = deque()
    for f, c in semillas:
        if not salida[f, c]:
            salida[f, c] = True
            cola.append((f, c))
    n = 0
    while cola:
        f, c = cola.popleft()
        n += 1
        if cancelado is not None and n % 500000 == 0 and cancelado():
            raise InterruptedError("Cancelado por el usuario")
        for df, dc in vecinos:
            nf, nc = f + df, c + dc
            if 0 <= nf < filas and 0 <= nc < cols and bajo[nf, nc] and not salida[nf, nc]:
                salida[nf, nc] = True
                cola.append((nf, nc))
    return salida


def calcular_escenario(dem_ef, validos, nivel, semillas, ocho_vecinos=False,
                       cancelado=None):
    """Devuelve (inundado, desconectado, profundidad).
    inundado: por debajo del nivel y conectado al mar.
    desconectado: por debajo del nivel pero sin conexión.
    profundidad: nivel - cota en lo inundado, NaN en el resto."""
    bajo = validos & (dem_ef < nivel)
    inundado = relleno_conectado(bajo, semillas, ocho_vecinos, cancelado)
    desconectado = bajo & ~inundado
    with np.errstate(invalid="ignore"):
        profundidad = np.where(inundado, nivel - dem_ef, np.nan).astype(np.float32)
    return inundado, desconectado, profundidad


# ------------------------------------------------------------ bandas (v0.2)
BANDAS = {1: "lower", 2: "central", 3: "upper"}
SITUACIONES = {1: "connects_at_upper", 2: "isolated", 3: "low_only_at_upper"}


def sigma_total(rmse_mdt, sigma_proy):
    """Suma en cuadratura. Supone errores independientes (simplificación)."""
    return float(np.hypot(rmse_mdt, sigma_proy))


def mar_nodata(validos, semillas, modo, ocho_vecinos=False):
    """NoData tratado como mar.
    modo 0: ninguno (NoData es barrera).
    modo 1: NoData conectado a algún punto de mar.
    modo 2: además, NoData que toca el borde del raster."""
    nod = ~validos
    if modo == 0 or not nod.any():
        return np.zeros(validos.shape, dtype=bool)
    sem = list(semillas)
    if modo == 2:
        filas, cols = nod.shape
        borde = [(0, c) for c in range(cols)] + [(filas - 1, c) for c in range(cols)]
        borde += [(f, 0) for f in range(filas)] + [(f, cols - 1) for f in range(filas)]
        sem += [p for p in borde if nod[p]]
    return relleno_conectado(nod, sem, ocho_vecinos)


def _nivel_en(nivel, f, c):
    return nivel[f, c] if np.ndim(nivel) else nivel


def semillas_utiles(semillas, validos, dem_ef, nivel, mar):
    """Puntos de mar que sirven: en NoData-mar, o en píxel válido por debajo del nivel."""
    return sum(1 for f, c in semillas
               if mar[f, c] or (validos[f, c] and dem_ef[f, c] < _nivel_en(nivel, f, c)))


def calcular_bandas(dem_ef, validos, nivel, delta, semillas, ocho_vecinos=False,
                    cancelado=None, mar=None, delta_alto=None):
    """nivel: escalar o array (nivel base variable). delta = k * sigma (banda baja);
    delta_alto: si se da, anchura de la banda alta (bandas asimétricas con percentiles).
    mar: array bool de NoData tratado como mar (el agua pasa por él, pero no cuenta como inundado).
    Devuelve (banda, situacion, profundidad_central, info).
    banda (uint8): 0 nada, 1 lower, 2 central, 3 upper (primera banda en que se moja).
    situacion (uint8): 0 nada, 1 connects_at_upper, 2 isolated, 3 low_only_at_upper.
    Con las mismas semillas y umbrales crecientes, lower ⊆ central ⊆ upper por construcción."""
    if mar is None:
        mar = np.zeros(dem_ef.shape, dtype=bool)

    def inundar(nv):
        bajo = validos & (dem_ef < nv)
        conectado = relleno_conectado(bajo | mar, semillas, ocho_vecinos, cancelado, fuentes=mar)
        return bajo, conectado & validos

    bajo_c, inu_c = inundar(nivel)
    with np.errstate(invalid="ignore"):
        prof = np.where(inu_c, nivel - dem_ef, np.nan).astype(np.float32)
    banda = np.zeros(dem_ef.shape, dtype=np.uint8)
    situ = np.zeros(dem_ef.shape, dtype=np.uint8)

    d_bajo = delta
    d_alto = delta if delta_alto is None else delta_alto
    if d_bajo <= 0 and d_alto <= 0:
        banda[inu_c] = 2
        situ[bajo_c & ~inu_c] = 2
        return banda, situ, prof, {"bandas": False}

    _, inu_s = inundar(nivel - d_bajo)
    bajo_p, inu_p = inundar(nivel + d_alto)
    banda[inu_p] = 3
    banda[inu_c] = 2
    banda[inu_s] = 1
    desc_c = bajo_c & ~inu_c
    situ[desc_c & inu_p] = 1
    situ[desc_c & ~inu_p] = 2
    situ[bajo_p & ~bajo_c & ~inu_p] = 3
    return banda, situ, prof, {"bandas": True, "seguro_vacio": not inu_s.any()}


def sigma_mdt(rmse, sesgo):
    """Desviación típica del error del MDT a partir de RMSE y sesgo: RMSE² = sesgo² + sd²."""
    if abs(sesgo) > rmse:
        raise ValueError("bias_gt_rmse")
    return float(np.sqrt(rmse ** 2 - sesgo ** 2))


# ------------------------------------------------ percentiles de la proyección (v0.5)
# z de la normal estándar para cada par de percentiles
PARES = {0: (17, 83, 0.9541652531461944), 1: (5, 95, 1.6448536269514722)}


def _erf(x):
    """Aproximación de Abramowitz y Stegun 7.1.26 (error máximo 1,5e-7). Evita depender de scipy."""
    x = np.asarray(x, dtype=float)
    sgn = np.sign(x)
    x = np.abs(x)
    t = 1.0 / (1.0 + 0.3275911 * x)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t
               + 0.254829592) * t * np.exp(-x * x)
    return sgn * y


def phi(x):
    """CDF de la normal estándar."""
    return 0.5 * (1.0 + _erf(np.asarray(x, dtype=float) / np.sqrt(2.0)))


_ZG = np.linspace(-9.0, 9.0, 400001)
_CG = phi(_ZG)


def phi_inv(p):
    """Inversa de la CDF normal por interpolación sobre una malla fina."""
    return np.interp(p, _CG, _ZG)


def bandas_percentiles(p_bajo, p50, p_alto, z, sigma_dem, k, n=20000):
    """Proyección como dos medias normales unidas en la mediana (50 % de la masa a cada lado, una σ por lado
    ajustada a los percentiles). No es la split normal clásica (unión en la moda): esta forma reproduce
    exactamente mediana y percentiles, con un salto de la densidad en la mediana. Más error del MDT N(0, sigma_dem).
    Devuelve (d_bajo, d_alto, prob_central):
      nivel banda baja = p50 - d_bajo  -> cuantil 1 - Φ(k) de la suma
      nivel banda alta = p50 + d_alto  -> cuantil Φ(k) de la suma
      prob_central = P(suma > p50): probabilidad de estar bajo el agua justo en la línea central."""
    if not (p_bajo <= p50 <= p_alto):
        raise ValueError("pct_order")
    s_l, s_r = (p50 - p_bajo) / z, (p_alto - p50) / z
    u = (np.arange(n) + 0.5) / n                      # muestreo por cuantiles, determinista
    zq = phi_inv(u)
    x = p50 + np.where(zq < 0, s_l, s_r) * zq         # cuantiles de las dos medias normales
    if sigma_dem > 0:
        F = lambda t: float(np.mean(phi((t - x) / sigma_dem)))
    else:
        F = lambda t: float(np.mean(x <= t))

    def cuantil(p):
        lo, hi = x[0] - 8 * sigma_dem - 1.0, x[-1] + 8 * sigma_dem + 1.0
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if F(mid) < p:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    pk = float(phi(k))
    q_bajo, q_alto = cuantil(1.0 - pk), cuantil(pk)
    prob_central = 1.0 - F(p50) if sigma_dem > 0 or s_l != s_r else 0.5
    return p50 - q_bajo, q_alto - p50, prob_central

import os
import numpy as np
import xarray as xr
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
from lifelines import CoxPHFitter
from typing import Any
from .statistics import compute_most_likely_terciles
from src.config.loader import get_periods_aggregation
from src.observation import Observation
from src.hindcast import Hindcast
from src.forecast import Forecast
from typing import TypedDict

class InputsDict(TypedDict):
    obs_total: np.ndarray
    obs_median: np.ndarray
    obs_tercinf: np.ndarray
    obs_tercsup: np.ndarray

    hcst_anomaly: np.ndarray
    fcst_anomaly: np.ndarray

    nlat: int
    nlon: int
    ntime: int

PREC_THRESHOLDS_MM = [
    10, 20, 40, 60, 80, 100, 150,
    200, 250, 300, 400, 500, 600
]

PREC_PERCENTILES = [
    0.2,
    0.5,
    0.8
]

# ============================================================
# INTERPOLAÇÃO E UTILITÁRIOS MATEMÁTICOS
# ============================================================

def _prepare_curve(
    vetorx: np.ndarray,
    prob: np.ndarray,
    alongar: bool = True,
    inverter: bool = True,
) -> tuple[np.ndarray, np.ndarray]:

    vetorx = np.asarray(vetorx, dtype=float)
    prob = np.asarray(prob, dtype=float)

    mask = np.isfinite(vetorx) & np.isfinite(prob)

    vetorx = vetorx[mask]
    prob = prob[mask]

    if vetorx.size == 0:
        return np.array([]), np.array([])

    order = np.argsort(vetorx)

    vetorx = vetorx[order]
    prob = prob[order]

    curva = 1 - prob if inverter else prob

    if alongar:

        xmin = vetorx.min()
        xmax = vetorx.max()

        delta = max(0.01 * abs(xmax - xmin), 1e-10)

        extremos = [0, 1] if inverter else [1, 0]

        curva = np.concatenate(
            ([extremos[0]], curva, [extremos[1]])
        )

        vetorx = np.concatenate(
            ([xmin - delta], vetorx, [xmax + delta])
        )

    return vetorx, curva

def interpolate_curve(
    vetorx: np.ndarray,
    prob: np.ndarray,
    target: float,
    *,
    inverse: bool = False,
    alongar: bool = True,
    use_cdf: bool = True,
    verbose: bool = False,
) -> float:
    """
    Interpola uma curva (vetorx, prob).

    Modos:
    ------
    inverse=False : x -> y
        Dado um valor de x, retorna a probabilidade correspondente.

    inverse=True : y -> x
        Dado um valor de y, retorna o valor correspondente de x.

    Parameters
    ----------
    vetorx : np.ndarray
        Eixo x da curva.

    prob : np.ndarray
        Eixo y da curva (survival ou CDF).

    target : float
        Valor alvo da interpolação.

    inverse : bool
        False: x -> y
        True: y -> x

    alongar : bool
        Adiciona bordas artificiais à curva.

    use_cdf : bool
        Converte survival -> CDF (1 - prob).

    Returns
    -------
    float
    """

    vetorx = np.asarray(vetorx, dtype=float)
    prob = np.asarray(prob, dtype=float)

    mask = (
        np.isfinite(vetorx)
        & np.isfinite(prob)
    )

    vetorx = vetorx[mask]
    prob = prob[mask]

    if vetorx.size == 0:
        return np.nan

    order = np.argsort(vetorx)

    vetorx = vetorx[order]
    prob = prob[order]

    curva = 1 - prob if use_cdf else prob

    if alongar:

        xmin = vetorx.min()
        xmax = vetorx.max()

        delta = max(
            0.01 * abs(xmax - xmin),
            1e-10
        )

        extremos = (
            [0, 1]
            if use_cdf
            else [1, 0]
        )

        curva = np.concatenate(
            ([extremos[0]], curva, [extremos[1]])
        )

        vetorx = np.concatenate(
            ([xmin - delta], vetorx, [xmax + delta])
        )

    if inverse:

        mask = np.concatenate(([True], np.diff(curva) != 0))

        curva = curva[mask]
        vetorx = vetorx[mask]

        if curva.size > 1 and curva[0] > curva[-1]:
            curva = curva[::-1]
            vetorx = vetorx[::-1]

        if curva.size == 0:
            return np.nan

        target = np.clip(
            target,
            curva.min(),
            curva.max()
        )

        return float(
            np.interp(
                target,
                curva,
                vetorx
            )
        )

    target = np.clip(
        target,
        vetorx.min(),
        vetorx.max()
    )

    return float(
        np.clip(
            np.interp(
                target,
                vetorx,
                curva
            ),
            0,
            1
        )
    )

def pad_to_max(arr, max_len):
    out = np.full(max_len, np.nan)
    n = min(len(arr), max_len)
    out[:n] = arr[:n]
    return out        

def compute_precipitation_products(
                varx_clim: list[float],
                proby_fcstcox: list[float]     
):

        prob_exceedance = [
            interpolate_curve(
                varx_clim,
                proby_fcstcox,
                t,
                use_cdf = False
            )
            for t in PREC_THRESHOLDS_MM
        ]

        percentile_mm = [
            interpolate_curve(
                varx_clim,
                proby_fcstcox,
                p,
                inverse = True,
                use_cdf = True
            )
            for p in PREC_PERCENTILES
        ]

        return prob_exceedance, percentile_mm

# ============================================================
# EXECUÇÃO DO MODELO DE COX EM UM PONTO
# ============================================================

def _compute_cox_gridpoint(
    obs_pt: list[float],
    anomhcst: list[float],
    fcst_pt: float,
    obs_median_pt: float,
    obs_tercinf_pt: float, 
    obs_tercsup_pt: float,
    compute_prec_products: bool = False
) -> dict[str, Any]:

    present = np.ones_like(obs_pt)

    df = pd.DataFrame({"obs": obs_pt, "anomhcst": anomhcst, "present": present})
    
    MAX_EVENTS = len(obs_pt)

    try:

        cox_model = CoxPHFitter()

        cox_model.fit(
            df, 
            duration_col="obs", 
            event_col="present"
        )

        coef = cox_model.params_["anomhcst"]
        basePEX = cox_model.baseline_survival_
        varx_clim = basePEX.index.values
        proby_clim = basePEX.values.flatten()    

    except Exception:

        coef = 0.0

        basePEX = pd.Series(
            np.linspace(1, 0, len(df)), 
            index=np.sort(df["obs"])
        )

        varx_clim = basePEX.index.values
        proby_clim = basePEX.values.flatten()
    
    exp_term = np.exp(coef * fcst_pt)
    proby_fcstcox = proby_clim ** exp_term

    # Estatísticas da distribuição prevista
    median_fcst = interpolate_curve(
        varx_clim,
        proby_fcstcox,
        0.5,
        inverse=True,
        use_cdf=False,
    )

    # Curva de sobrevivência:
    # Q1 -> P(X > x)=0.75
    # Q3 -> P(X > x)=0.25

    quartil_1 = interpolate_curve(
        varx_clim,
        proby_fcstcox,
        0.75,
        inverse=True,
        use_cdf=False,
    )

    quartil_3 = interpolate_curve(
        varx_clim,
        proby_fcstcox,
        0.25,
        inverse=True,
        use_cdf=False,
    )

    iqr = quartil_3 - quartil_1

    # Probabilidades climatológicas
    above_median = interpolate_curve(
        varx_clim,
        proby_fcstcox,
        obs_median_pt,
        use_cdf=False,
    )

    above_tinf = interpolate_curve(
        varx_clim,
        proby_fcstcox,
        obs_tercinf_pt,
        use_cdf=False,
    )

    above_tsup = interpolate_curve(
        varx_clim,
        proby_fcstcox,
        obs_tercsup_pt,
        use_cdf=False,
    )

    below_tinf = 1 - above_tinf

    below_tsup = 1 - above_tsup

    prob_central = below_tsup - below_tinf

    # Produtos de precipitação
    if compute_prec_products:

        prob_exceedance,  percentile_mm = compute_precipitation_products(
            varx_clim, 
            proby_fcstcox
        )

    varx_pad = pad_to_max(
        varx_clim, 
        MAX_EVENTS
    )

    proby_clim_pad = pad_to_max(
        proby_clim, 
        MAX_EVENTS
    )

    proby_fcst_pad = pad_to_max(
        proby_fcstcox, 
        MAX_EVENTS
    )      

    results = {
        
        "varx_pad": varx_pad,

        "proby_clim_pad": proby_clim_pad,

        "proby_fcst_pad": proby_fcst_pad,

        "coef_beta": coef,

        "median_fcst": median_fcst,

        "iqr": iqr,

        "above_median": above_median,

        "above_tinf": above_tinf,

        "above_tsup": above_tsup,

        "below_tinf": below_tinf,

        "below_tsup": below_tsup,

        "prob_central": prob_central
    }

    if compute_prec_products:
        results["percentile_mm"] = percentile_mm
        results["prob_exceedance"] = prob_exceedance

    return results

# ============================================================
# PROCESSAMENTO ESPACIAL
# ============================================================

def process_gridpoint(
    ilat: int,
    ilon: int,
    shared_data: InputsDict,
    compute_prec_products: bool = False
) -> dict[str, Any]:

    obs_pt = shared_data["obs_total"][:, ilat, ilon]

    obs_median_pt = shared_data["obs_median"][ilat, ilon]

    obs_tercinf_pt = shared_data["obs_tercinf"][ilat, ilon]

    obs_tercsup_pt = shared_data["obs_tercsup"][ilat, ilon]

    anomhcst = shared_data["hcst_anomaly"][:, ilat, ilon]

    fcst_pt = shared_data["fcst_anomaly"][ilat, ilon]

    results = _compute_cox_gridpoint(
        obs_pt,
        anomhcst,
        fcst_pt,
        obs_median_pt,
        obs_tercinf_pt,
        obs_tercsup_pt,
        compute_prec_products
    )

    return results

def process_latitude(
    ilat: int,
    shared_data: InputsDict,
    compute_prec_products: bool = False
) -> tuple[int, list[tuple[int, dict[str, Any]]]]:

    nlon = shared_data["nlon"]

    results_lat = []

    for ilon in range(nlon):

        results = process_gridpoint(
            ilat,
            ilon,
            shared_data,
            compute_prec_products
        ) 

        results_lat.append((ilon, results))      

    return ilat, results_lat 

# ============================================================
# ESTRUTURAS DE ENTRADA E SAÍDA
# ============================================================

def build_inputs(
    obs_stats: dict[str, xr.DataArray], 
    hcst_stats: dict[str, xr.DataArray], 
    realtime_forecast: xr.DataArray        
) -> dict[str, Any]:

        rename_dims = {
            dim: name
            for dim, name in {"Y": "lat", "X": "lon"}.items()
            if dim in realtime_forecast.dims
        }

        if rename_dims:
            realtime_forecast = realtime_forecast.rename(rename_dims)

        forecast_anomaly = realtime_forecast - hcst_stats["mean"]
        
        obs_np = obs_stats["total"].values
        obs_median_np = obs_stats["median"].values
        obs_tercinf_np = obs_stats["tinf"].values
        obs_tercsup_np = obs_stats["tsup"].values
        hcst_np = hcst_stats["anom"].values
        fcst_np = forecast_anomaly.values

        nlat = forecast_anomaly.sizes["lat"]
        nlon = forecast_anomaly.sizes["lon"]
        ntime = obs_stats["total"].shape[0]
        
        return {
            "obs_total": obs_np,
            "obs_median": obs_median_np,
            "obs_tercinf": obs_tercinf_np,
            "obs_tercsup": obs_tercsup_np,
            "hcst_anomaly": hcst_np,
            "fcst_anomaly": fcst_np,
            "nlat": nlat,
            "nlon": nlon,
            "ntime": ntime
        }

def initialize_outputs(
        ntime: int,
        nlat: int, 
        nlon: int,
        compute_prec_products: bool = False
) -> dict[str, np.ndarray]:
    
    outputs = {
        "varx": np.full((ntime, nlat, nlon), np.nan),

        "proby_clim": np.full((ntime, nlat, nlon), np.nan),

        "proby_fcst": np.full((ntime, nlat, nlon), np.nan),

        "coef_beta": np.full((nlat, nlon), np.nan),

        "total": np.full((nlat, nlon), np.nan),

        "anomaly": np.full((nlat, nlon), np.nan),

        "iqr": np.full((nlat, nlon), np.nan),

        "above_median": np.full((nlat, nlon), np.nan),

        "above_tinf": np.full((nlat, nlon), np.nan),

        "above_tsup": np.full((nlat, nlon), np.nan),

        "below_tinf": np.full((nlat, nlon), np.nan),

        "below_tsup": np.full((nlat, nlon), np.nan),

        "prob_central": np.full((nlat, nlon), np.nan)
    }    

    if compute_prec_products:

        for p in PREC_PERCENTILES:
            outputs[f"percent{int(p*100)}"] = np.full(
                (nlat, nlon),
                np.nan
            )

        for t in PREC_THRESHOLDS_MM:
            outputs[f"prob{t}mm"] = np.full(
                (nlat, nlon),
                np.nan
            )

    return outputs

def fill_outputs(
        outputs: dict,
        results: dict,
        ilat: int,
        ilon: int,
        obs_median,
        compute_prec_products: bool = False
) -> None:

    outputs["varx"][:, ilat, ilon] = results["varx_pad"]

    outputs["proby_clim"][:, ilat, ilon] = results["proby_clim_pad"]

    outputs["proby_fcst"][:, ilat, ilon] = results["proby_fcst_pad"]

    outputs["coef_beta"][ilat, ilon] = results["coef_beta"]

    outputs["total"][ilat, ilon] = results["median_fcst"]

    outputs["anomaly"][ilat, ilon] = (
        results["median_fcst"] - obs_median[ilat, ilon]
    )

    outputs["iqr"][ilat, ilon] = results["iqr"]

    outputs["above_median"][ilat, ilon] = results["above_median"]

    outputs["above_tinf"][ilat, ilon] = results["above_tinf"]

    outputs["above_tsup"][ilat, ilon] = results["above_tsup"]

    outputs["below_tinf"][ilat, ilon] = results["below_tinf"]

    outputs["below_tsup"][ilat, ilon] = results["below_tsup"]

    outputs["prob_central"][ilat, ilon] = (
        (1 - results["below_tinf"] - results["above_tsup"]) 
    )

    if compute_prec_products:

        for i, p in enumerate(PREC_PERCENTILES):
            outputs[f"percent{int(p*100)}"][ilat, ilon] = (
                results["percentile_mm"][i]
            )

        for i, t in enumerate(PREC_THRESHOLDS_MM):
            outputs[f"prob{t}mm"][ilat, ilon] = (
                results["prob_exceedance"][i]
            )
    
def convert_outputs_to_xarray(
    outputs,
    template
):
    converted = {}

    for name, data in outputs.items():

        if data.ndim == 2:

            converted[name] = xr.DataArray(
                data,
                dims=("lat", "lon"),
                coords={
                    "lat": template.lat,
                    "lon": template.lon,
                },
            )

        elif name in ["varx", "proby_clim", "proby_fcst"]:

            converted[name] = xr.DataArray(
                data,
                dims=("event", "lat", "lon"),
                coords={
                    "event": np.arange(data.shape[0]),
                    "lat": template.lat,
                    "lon": template.lon,
                },
            )

    return converted

# ============================================================
# ORQUESTRADORES
# ============================================================

def compute_calibration_period(
    obs_stats: dict[str, xr.DataArray], 
    hcst_stats: dict[str, xr.DataArray], 
    realtime_forecast: xr.DataArray,
    compute_prec_products: bool = False,
    executor: ProcessPoolExecutor | None = None,
) -> dict[str, xr.DataArray]:
    ''' Calibração das previsões em tempo-real através do método de regressão linear'''

    inputs = build_inputs(
        obs_stats,
        hcst_stats,
        realtime_forecast
    )

    shared_data = inputs

    outputs = initialize_outputs(
        inputs["ntime"],
        inputs["nlat"],
        inputs["nlon"],
        compute_prec_products
    )                        

    if executor is None:
        max_workers = max(1, (os.cpu_count() or 1) // 2)

        with ProcessPoolExecutor(max_workers=max_workers) as local_executor:
            fill_outputs_from_executor(
                local_executor,
                outputs,
                shared_data,
                compute_prec_products,
            )

    else:
        fill_outputs_from_executor(
            executor,
            outputs,
            shared_data,
            compute_prec_products,
        )

    outputs = convert_outputs_to_xarray(
        outputs,
        obs_stats["median"]
    )

    outputs["mlterciles"] = compute_most_likely_terciles(
        outputs["below_tinf"],
        outputs["prob_central"],
        outputs["above_tsup"]
    )

    return outputs
 

def fill_outputs_from_executor(
    executor: ProcessPoolExecutor,
    outputs: dict,
    shared_data: InputsDict,
    compute_prec_products: bool = False,
) -> None:

    futures = {
        executor.submit(
            process_latitude,
            ilat,
            shared_data,
            compute_prec_products,
        ): ilat
        for ilat in range(shared_data["nlat"])
    }

    for future in as_completed(futures):

        try:
            ilat, results_lat = future.result()

            for ilon, results in results_lat:
                fill_outputs(
                    outputs,
                    results,
                    ilat,
                    ilon,
                    shared_data["obs_median"],
                    compute_prec_products,
                )

        except Exception as e:
            ilat = futures[future]
            print(f"Erro na latitude {ilat}: {e}")
            raise


# ============================================================
# API PÚBLICA
# ============================================================

def get_cox_calibration_results(
        obs_statistics: dict[str, dict[str, xr.DataArray]],
        hcst_statistics: dict[str, dict[str, xr.DataArray]],
        realtime_forecast: dict[str, xr.DataArray],
        compute_prec_products: bool = False,
        executor: ProcessPoolExecutor | None = None,
) -> dict[str, dict[str, xr.DataArray]]:
    
    periods = get_periods_aggregation()

    results: dict[str, dict[str, xr.DataArray]] = {}

    for period in periods:

        results[period] = compute_calibration_period(
            obs_statistics[period],
            hcst_statistics[period],
            realtime_forecast[period],
            compute_prec_products,
            executor,
        )

    return results


# results = {
#     "anomaly_fcst": outputs["anomaly_fcst"],
#     "median_fcst": outputs["median_fcst"],
#     "above_median": outputs["above_median"],
#     "above_tinf": outputs["above_tinf"],
#     "above_tsup": outputs["above_tsup"],       
#     "below_tinf": outputs["below_tinf"],
#     "below_tsup": outputs["below_tsup"],  
#     "prob_central": outputs["prob_central"], 
#     "most_likely_terciles": outputs["most_likely_terciles"],
#     "varx": outputs["varx"],  
#     "proby_clim": outputs["proby_clim"],
#     "proby_fcst": outputs["proby_fcst"],
#     "iqr": outputs["iqr"],
#     "coef_beta": outputs["coef_beta"],
# }  

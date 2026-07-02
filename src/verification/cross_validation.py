import xarray as xr

from src.calibration.cox import get_cox_calibration_results
from src.calibration.linear_regression import get_linear_regression_calibr_results
from src.config.loader import get_climatology_period, get_periods_aggregation
from src.hindcast import Hindcast
from src.observation import Observation


def get_cross_validation_years(base: str) -> list[int]:
    start_year, end_year = get_climatology_period(base)
    return list(range(start_year, end_year + 1))


def run_cross_validation(
    base: str,
    model: str,
    var: str,
    type_calibration: str,
    month_hcst: int,
    models_available: list[str],
) -> dict[str, dict[str, dict[str, xr.DataArray]]]:
    """
    Gera produtos de verificação por leave-one-year-out.

    O hindcast do ano removido é usado como forecast-alvo, mantendo o
    mesmo contrato das rotinas de calibração do realtime.
    """

    years = get_cross_validation_years(base)
    periods = get_periods_aggregation()

    obs = Observation(
        base,
        var,
        month_hcst,
    )

    hindcast = Hindcast(
        base,
        var,
        month_hcst,
        models_available,
    )

    obs_all_years = obs.calculate_periods_all_years()

    results_by_year = []
    obs_by_year = []

    for target_year in years:

        obs_statistics = obs.compute_statistics(
            exclude_year=target_year
        )

        hcst_statistics = hindcast.compute_statistics(
            model,
            exclude_year=target_year
        )

        hcst_target = hindcast.get_hindcast_target(
            model,
            target_year
        )

        if type_calibration == "regr":
            results = get_linear_regression_calibr_results(
                obs_statistics,
                hcst_statistics,
                hcst_target,
            )

        elif type_calibration == "cox":
            results = get_cox_calibration_results(
                obs_statistics,
                hcst_statistics,
                hcst_target,
                compute_prec_products=(var == "prec"),
            )

        elif type_calibration == "nocalib":
            results = compute_nocalib_cross_validation_year(
                hindcast,
                model,
                target_year,
                obs_statistics,
                hcst_statistics,
            )

        else:
            raise ValueError(
                f"Calibração desconhecida: {type_calibration}"
            )

        results_by_year.append(
            add_year_dimension(results, target_year)
        )

        obs_by_year.append(
            add_year_dimension(
                build_observation_reference(
                    obs_all_years,
                    obs_statistics,
                    target_year,
                ),
                target_year,
            )
        )

    return {
        "forecast": concat_year_results(
            results_by_year,
            periods,
        ),
        "obs": concat_year_results(
            obs_by_year,
            periods,
        ),
    }


def compute_nocalib_cross_validation_year(
    hindcast: Hindcast,
    model: str,
    target_year: int,
    obs_statistics: dict[str, dict[str, xr.DataArray]],
    hcst_statistics: dict[str, dict[str, xr.DataArray]],
) -> dict[str, dict[str, xr.DataArray]]:

    if model == "multimodel":
        return compute_nocalib_multimodel_year(
            hindcast,
            target_year,
            obs_statistics,
            hcst_statistics,
        )

    return compute_nocalib_model_year(
        hindcast,
        model,
        target_year,
        obs_statistics,
        hcst_statistics,
    )


def compute_nocalib_multimodel_year(
    hindcast: Hindcast,
    target_year: int,
    obs_statistics: dict[str, dict[str, xr.DataArray]],
    hcst_statistics: dict[str, dict[str, xr.DataArray]],
) -> dict[str, dict[str, xr.DataArray]]:

    member_results = [
        compute_nocalib_model_year(
            hindcast,
            model,
            target_year,
            obs_statistics,
            hcst_statistics,
        )
        for model in hindcast.models_available
    ]

    target = hindcast.get_hindcast_target(
        "multimodel",
        target_year,
    )

    results = {}

    for period in get_periods_aggregation():
        probs = {
            product: xr.concat(
                [
                    member_result[period][product]
                    for member_result in member_results
                ],
                dim="model",
            ).mean("model", skipna=True)
            for product in ["above_mean", "below_tinf", "above_tsup"]
        }

        anomaly = target[period] - hcst_statistics[period]["mean"]

        results[period] = {
            "total": target[period],
            "anomaly": anomaly,
            **probs,
        }

    return results


def compute_nocalib_model_year(
    hindcast: Hindcast,
    model: str,
    target_year: int,
    obs_statistics: dict[str, dict[str, xr.DataArray]],
    hcst_statistics: dict[str, dict[str, xr.DataArray]],
) -> dict[str, dict[str, xr.DataArray]]:

    members = hindcast.load_years_climatology_members(model)
    target = hindcast.get_hindcast_target(model, target_year)

    results = {}

    for period, da in members.items():

        climatology_members = da.drop_sel(
            year=target_year,
            errors="ignore",
        )

        target_members = da.sel(year=target_year)

        mean_threshold = climatology_members.mean(
            dim=("year", "member"),
            skipna=True,
        )

        tinf_threshold = climatology_members.quantile(
            0.33,
            dim=("year", "member"),
            skipna=True,
        ).drop_vars("quantile", errors="ignore")

        tsup_threshold = climatology_members.quantile(
            0.66,
            dim=("year", "member"),
            skipna=True,
        ).drop_vars("quantile", errors="ignore")

        above_mean = (
            target_members >= mean_threshold
        ).mean("member")

        below_tinf = (
            target_members <= tinf_threshold
        ).mean("member")

        above_tsup = (
            target_members >= tsup_threshold
        ).mean("member")

        anomaly = target[period] - hcst_statistics[period]["mean"]

        results[period] = {
            "total": target[period],
            "anomaly": anomaly,
            "above_mean": above_mean,
            "below_tinf": below_tinf,
            "above_tsup": above_tsup,
        }

    return results


def build_observation_reference(
    obs_all_years: dict[str, xr.DataArray],
    obs_statistics: dict[str, dict[str, xr.DataArray]],
    target_year: int,
) -> dict[str, dict[str, xr.DataArray]]:

    reference = {}

    for period, da in obs_all_years.items():

        total = da.sel(year=target_year)
        mean = obs_statistics[period]["mean"]
        median = obs_statistics[period]["median"]

        reference[period] = {
            "total": total,
            "anomaly": total - mean,
            "mean": mean,
            "median": median,
            "tinf": obs_statistics[period]["tinf"],
            "tsup": obs_statistics[period]["tsup"],
        }

    return reference


def add_year_dimension(
    results: dict[str, dict[str, xr.DataArray]],
    year: int,
) -> dict[str, dict[str, xr.DataArray]]:

    return {
        period: {
            product: da.expand_dims(year=[year])
            for product, da in period_results.items()
        }
        for period, period_results in results.items()
    }


def concat_year_results(
    results_by_year: list[dict[str, dict[str, xr.DataArray]]],
    periods: list[str],
) -> dict[str, dict[str, xr.DataArray]]:

    combined = {}

    for period in periods:

        product_names = results_by_year[0][period].keys()

        combined[period] = {
            product: xr.concat(
                [
                    year_results[period][product]
                    for year_results in results_by_year
                ],
                dim="year",
            )
            for product in product_names
        }

    return combined

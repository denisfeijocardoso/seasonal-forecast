import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

import xarray as xr

from src.calibration.cox import get_cox_calibration_results
from src.calibration.linear_regression import (
    get_linear_regression_verification_results,
)
from src.config.loader import get_climatology_period, get_periods_aggregation
from src.hindcast import Hindcast
from src.observation import Observation


@dataclass
class CrossValidationContext:
    base: str
    model: str
    var: str
    month_hcst: int
    models_available: list[str]
    years: list[int]
    periods: list[str]
    obs_all_years: dict[str, xr.DataArray]
    hcst_all_years: dict[str, xr.DataArray]
    regr_correlations: dict[str, xr.DataArray]
    nocalib_members: dict[str, dict[str, xr.DataArray]]


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

    context = build_cross_validation_context(
        base=base,
        model=model,
        var=var,
        month_hcst=month_hcst,
        models_available=models_available,
        include_nocalib_members=(type_calibration == "nocalib"),
        include_regr_correlations=(type_calibration == "regr"),
    )

    return run_cross_validation_for_calibration(
        context,
        type_calibration,
    )


def build_cross_validation_context(
    base: str,
    model: str,
    var: str,
    month_hcst: int,
    models_available: list[str],
    include_nocalib_members: bool = False,
    include_regr_correlations: bool = False,
) -> CrossValidationContext:

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
    hcst_all_years = hindcast.get_hindcast(model)
    regr_correlations = (
        compute_leave_one_out_correlations(
            obs_all_years,
            hcst_all_years,
        )
        if include_regr_correlations
        else {}
    )
    nocalib_members = (
        load_nocalib_members(
            hindcast,
            model,
        )
        if include_nocalib_members
        else {}
    )

    return CrossValidationContext(
        base=base,
        model=model,
        var=var,
        month_hcst=month_hcst,
        models_available=models_available,
        years=years,
        periods=periods,
        obs_all_years=obs_all_years,
        hcst_all_years=hcst_all_years,
        regr_correlations=regr_correlations,
        nocalib_members=nocalib_members,
    )


def run_cross_validation_for_calibration(
    context: CrossValidationContext,
    type_calibration: str,
) -> dict[str, dict[str, dict[str, xr.DataArray]]]:

    if type_calibration == "cox":
        max_workers = max(1, (os.cpu_count() or 1) // 2)

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            return run_cross_validation_for_calibration_loop(
                context,
                type_calibration,
                executor,
            )

    return run_cross_validation_for_calibration_loop(
        context,
        type_calibration,
    )


def run_cross_validation_for_calibration_loop(
    context: CrossValidationContext,
    type_calibration: str,
    cox_executor: ProcessPoolExecutor | None = None,
) -> dict[str, dict[str, dict[str, xr.DataArray]]]:

    results_by_year = []
    obs_by_year = []

    for target_year in context.years:

        obs_statistics = compute_obs_statistics(
            context.obs_all_years,
            target_year,
        )

        hcst_statistics = compute_hcst_statistics(
            context.hcst_all_years,
            target_year,
        )

        hcst_target = select_target_year(
            context.hcst_all_years,
            target_year,
        )

        if type_calibration == "regr":
            correlations = select_target_year(
                context.regr_correlations,
                target_year,
            ) if context.regr_correlations else None

            results = get_linear_regression_verification_results(
                obs_statistics,
                hcst_statistics,
                hcst_target,
                correlations,
            )

        elif type_calibration == "cox":
            results = get_cox_calibration_results(
                obs_statistics,
                hcst_statistics,
                hcst_target,
                compute_prec_products=(context.var == "prec"),
                executor=cox_executor,
            )

        elif type_calibration == "nocalib":
            if not context.nocalib_members:
                raise ValueError(
                    "Membros do hindcast nao carregados para nocalib."
                )

            results = compute_nocalib_cross_validation_year(
                context.model,
                target_year,
                hcst_statistics,
                hcst_target,
                context.nocalib_members,
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
                    context.obs_all_years,
                    obs_statistics,
                    target_year,
                ),
                target_year,
            )
        )

    return {
        "forecast": concat_year_results(
            results_by_year,
            context.periods,
        ),
        "obs": concat_year_results(
            obs_by_year,
            context.periods,
        ),
    }


def compute_obs_statistics(
    obs_all_years: dict[str, xr.DataArray],
    exclude_year: int,
) -> dict[str, dict[str, xr.DataArray]]:

    obs_statistics = {}

    for period, da in obs_all_years.items():

        climatology = da.drop_sel(
            year=exclude_year,
            errors="ignore",
        )

        mean = climatology.mean("year")
        q1 = climatology.quantile(0.25, "year")
        q3 = climatology.quantile(0.75, "year")

        obs_statistics[period] = {
            "total": climatology,
            "mean": mean,
            "median": climatology.median("year"),
            "std": climatology.std("year"),
            "tinf": climatology.quantile(0.33, "year"),
            "tsup": climatology.quantile(0.66, "year"),
            "iqr": q3 - q1,
            "anom": climatology - mean,
        }

    return obs_statistics


def compute_hcst_statistics(
    hcst_all_years: dict[str, xr.DataArray],
    exclude_year: int,
) -> dict[str, dict[str, xr.DataArray]]:

    hcst_statistics = {}

    for period, da in hcst_all_years.items():

        climatology = da.drop_sel(
            year=exclude_year,
            errors="ignore",
        )

        mean = climatology.mean("year")

        hcst_statistics[period] = {
            "mean": mean,
            "std": climatology.std("year"),
            "anom": climatology - mean,
        }

    return hcst_statistics


def compute_leave_one_out_correlations(
    obs_all_years: dict[str, xr.DataArray],
    hcst_all_years: dict[str, xr.DataArray],
) -> dict[str, xr.DataArray]:

    return {
        period: compute_leave_one_out_correlation_period(
            obs_all_years[period],
            hcst_all_years[period],
        )
        for period in obs_all_years
    }


def compute_leave_one_out_correlation_period(
    obs: xr.DataArray,
    hcst: xr.DataArray,
) -> xr.DataArray:

    obs, hcst = xr.align(
        obs,
        hcst,
        join="inner",
    )

    valid = obs.notnull() & hcst.notnull()
    count = valid.sum("year")

    obs_valid = obs.where(valid)
    hcst_valid = hcst.where(valid)

    sum_obs = obs_valid.sum("year", skipna=True)
    sum_hcst = hcst_valid.sum("year", skipna=True)
    sum_obs2 = (obs_valid ** 2).sum("year", skipna=True)
    sum_hcst2 = (hcst_valid ** 2).sum("year", skipna=True)
    sum_cross = (obs_valid * hcst_valid).sum("year", skipna=True)

    valid_year = valid.astype(int)
    count_loo = count - valid_year

    obs_fill = obs_valid.fillna(0)
    hcst_fill = hcst_valid.fillna(0)

    sum_obs_loo = sum_obs - obs_fill
    sum_hcst_loo = sum_hcst - hcst_fill
    sum_obs2_loo = sum_obs2 - obs_fill ** 2
    sum_hcst2_loo = sum_hcst2 - hcst_fill ** 2
    sum_cross_loo = sum_cross - obs_fill * hcst_fill

    covariance = sum_cross_loo - (
        sum_obs_loo * sum_hcst_loo / count_loo
    )
    variance_obs = sum_obs2_loo - (
        sum_obs_loo ** 2 / count_loo
    )
    variance_hcst = sum_hcst2_loo - (
        sum_hcst_loo ** 2 / count_loo
    )

    correlation = covariance / (variance_obs * variance_hcst) ** 0.5

    return (
        correlation
        .where(
            (count_loo >= 2)
            & (variance_obs > 0)
            & (variance_hcst > 0)
        )
        .fillna(0)
        .clip(min=0)
    )


def select_target_year(
    all_years: dict[str, xr.DataArray],
    target_year: int,
) -> dict[str, xr.DataArray]:

    return {
        period: da.sel(year=target_year)
        for period, da in all_years.items()
    }


def load_nocalib_members(
    hindcast: Hindcast,
    model: str,
) -> dict[str, dict[str, xr.DataArray]]:

    models = (
        hindcast.models_available
        if model == "multimodel"
        else [model]
    )

    return {
        mdl: hindcast.load_years_climatology_members(mdl)
        for mdl in models
    }


def compute_nocalib_cross_validation_year(
    model: str,
    target_year: int,
    hcst_statistics: dict[str, dict[str, xr.DataArray]],
    target: dict[str, xr.DataArray],
    members_by_model: dict[str, dict[str, xr.DataArray]],
) -> dict[str, dict[str, xr.DataArray]]:

    if model == "multimodel":
        return compute_nocalib_multimodel_year(
            target_year,
            hcst_statistics,
            target,
            members_by_model,
        )

    return compute_nocalib_model_year(
        members_by_model[model],
        target,
        target_year,
        hcst_statistics,
    )


def compute_nocalib_multimodel_year(
    target_year: int,
    hcst_statistics: dict[str, dict[str, xr.DataArray]],
    target: dict[str, xr.DataArray],
    members_by_model: dict[str, dict[str, xr.DataArray]],
) -> dict[str, dict[str, xr.DataArray]]:

    member_results = [
        compute_nocalib_model_year(
            members,
            select_target_year(members, target_year),
            target_year,
            hcst_statistics,
        )
        for members in members_by_model.values()
    ]

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
    members: dict[str, xr.DataArray],
    target: dict[str, xr.DataArray],
    target_year: int,
    hcst_statistics: dict[str, dict[str, xr.DataArray]],
) -> dict[str, dict[str, xr.DataArray]]:

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

from src.data.interpolation_data import interpolation_forecast_model, interpolation_hindcast_model

def run_interpolation_forecast_models(
    base: str,
    models: list[str],
    var: str,
    year_fcst: int,
    month_fcst: int
):
    for model in models:

        interpolation_forecast_model(
            base,
            model,
            var,
            year_fcst,
            month_fcst
        )

def run_interpolation_hindcast_models(
    base: str,
    models: list[str],
    var: str,
    month_hcst: int
):
    for model in models:

        interpolation_hindcast_model(
            base,
            model,
            var,
            month_hcst
        )

from src.config.loader import PARAMETERS_RUN


def validate_month(month: int) -> None:
    if month < 1 or month > 12:
        raise ValueError("--month precisa estar entre 1 e 12.")


def select_variables(var: str | None) -> list[str]:
    if var is None:
        return list(PARAMETERS_RUN["variables"])

    if var not in PARAMETERS_RUN["variables"]:
        raise ValueError(f"Variavel invalida: {var}")

    return [var]


def select_calibrations(calibration: str) -> list[str]:
    if calibration == "all":
        return list(PARAMETERS_RUN["calibrations"])

    if calibration not in PARAMETERS_RUN["calibrations"]:
        raise ValueError(f"Calibracao invalida: {calibration}")

    return [calibration]

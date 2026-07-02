from pathlib import Path
from src.config.config_models import build_model_dir_name, get_multimodel_version
from src.config.paths import PATH_FIG, PATH_POSPROC

def build_output_path(
        base: str,
        model: str,
        type_calibration: str,
        year_fcst: int,
        month_fcst: int,
        is_path_fig: bool = False,
        is_verification: bool= False
) -> Path:
    
    multimodel_version = get_multimodel_version(base)

    name_model_dir = build_model_dir_name(model)

    if is_path_fig:
        root_path = PATH_FIG
    else:
        root_path = PATH_POSPROC

    if is_verification:
        type_product = "verification"
    else:
        type_product = "forecast"

    out_path =  ( 
        root_path /
        base /
        f"{multimodel_version}" /
        type_product /
        type_calibration /
        name_model_dir /
        str(year_fcst) /
        f"{year_fcst}{month_fcst:02d}0100"
    )

    return  out_path

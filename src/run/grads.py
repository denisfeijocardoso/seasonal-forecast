import subprocess
import logging
from datetime import datetime
from src.config.config_models import build_model_title, build_model_dir_name, get_multimodel_version
from src.config.paths import PATH_GRADS

logger = logging.getLogger(__name__)

def generate_maps():
    pass

def run_grads_maps_realtime(
        base: str,
        model: str,
        var: str,
        type_calibration: str,
        year_fcst: int, 
        month_fcst: int
):

    #------------------------------#
    # Define os argumentos usados  #
    # para rodar os scripts grads  #
    #------------------------------#

    model_dir = build_model_dir_name(model)
    model_title = build_model_title(model)

    grads_script_model = (
        PATH_GRADS /
        "fcst_maps_seasonal_models.gs"
    )

    grads_script_multimodel = (
        PATH_GRADS /
        "fcst_maps_seasonal_multimodel.gs"
    )

    version_multimodel = get_multimodel_version(base)

    if model != "multimodel":
        logger.info("Gerando os mapas do modelo:", model_title)
    else:
        logger.info(f"Gerando os mapas do Multimodelo: {base.upper()}")

    fcst_date = f"{year_fcst}{month_fcst:02d}0100"

    #-----------------------------------------#
    #    Rodar Scripts Grads que geram        #
    # os mapas da previsão sazonal calibrada  #
    #-----------------------------------------# 
    if model == "multimodel":
        grads_cmd = (
            f"run {grads_script_multimodel} "
            f"{fcst_date} {version_multimodel} {base} {var} {type_calibration}"
        )

    else:
        grads_cmd = (
            f"run {grads_script_model} "
            f"{fcst_date} {model_dir} {model_title} {version_multimodel} {base} {var} {type_calibration}"
        )

    # Abre o GrADS
    process = subprocess.Popen(
        ["grads", "-lbc"],
        stdin=subprocess.PIPE,
        text=True
    )

    # Envia comandos: run + quit
    stdout, stderr = process.communicate(
        grads_cmd + "\nquit\n"
    )

    # Debug opcional
    print("STDOUT:\n", stdout)
    print("STDERR:\n", stderr)

def run_grads_maps_verification(
        base: str,
        model: str,
        var: str,
        type_calibration: str,
        year_hcst: int, 
        month_hcst: int
):

    #------------------------------#
    # Define os argumentos usados  #
    # para rodar os scripts grads  #
    #------------------------------#

    model_dir = build_model_dir_name(model)
    model_title = build_model_title(model)


    grads_script_model = (
        PATH_GRADS /
        "verif_maps_seasonal_models.gs"
    )

    grads_script_multimodel = (
        PATH_GRADS /
        "verif_maps_seasonal_multimodel.gs"
    )

    version_multimodel = get_multimodel_version(base)

    if model != "multimodel":
        logger.info("Gerando os mapas do modelo:", model_title)
    else:
        logger.info(f"Gerando os mapas do Multimodelo: {base.upper()}")

    fcst_date = f"{year_hcst}{month_hcst:02d}0100"

    month_name = datetime(
        2000, 
        month_hcst, 
        1
    ).strftime('%b').upper()

    #-----------------------------------------#
    #    Rodar Scripts Grads que geram        #
    # os mapas da previsão sazonal calibrada  #
    #-----------------------------------------# 
    if model == "multimodel":
        grads_cmd = (
            f"run {grads_script_multimodel} "
            f"{fcst_date} {month_name} {version_multimodel} {base} {var} {type_calibration}"
        )
    else:
        grads_cmd = (
            f"run {grads_script_model} "
            f"{fcst_date} {month_name} {model_dir} {model_title} {version_multimodel} {base} {var} {type_calibration}"
        )

    # Abre o GrADS
    process = subprocess.Popen(
        ["grads", "-lbc"],
        stdin=subprocess.PIPE,
        text=True
    )

    # Envia comandos: run + quit
    stdout, stderr = process.communicate(
        grads_cmd + "\nquit\n"
    )

    # Debug opcional
    print("STDOUT:\n", stdout)
    print("STDERR:\n", stderr)
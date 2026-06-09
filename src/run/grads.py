import subprocess
from src.config.config_models import ConfigModelos

def generate_maps():
    pass

def run_grads_maps_seasonal(year_fcst, month_fcst, base, model, var, calib):

    #------------------------------#
    # Define os argumentos usados  #
    # para rodar os scripts grads  #
    #------------------------------#

    if base == "copernicus":
        model_dir = ConfigModelos.get_model_dir_c3s(model)
        model_title = ConfigModelos.get_model_title_c3s(model)

    elif base == "nmme":
        model_dir = ConfigModelos.get_model_dir_nmme(model)
        model_title = ConfigModelos.get_model_title_nmme(model)

    grads_script_model = "/scripts/clima/denis/seasonal/src/maps/fcst_maps_seasonal_models.gs"
    grads_script_multimodel = "/scripts/clima/denis/seasonal/src/maps/fcst_maps_seasonal_multimodel.gs"

    version_multimodel = ConfigModelos.get_multimodel_version(base)

    if model != "multimodel":
        print("Nome do diretorio do modelo:", model_dir)
        print("Nome do modelo no título dos mapas:", model_title)
    else:
        print(f"Gerando os mapas do Multimodelo {base.upper()}")

    month = f"{month_fcst:02d}"
    fcst_date = f"{year_fcst}{month}0100"

    #-----------------------------------------#
    #    Rodar Scripts Grads que geram        #
    # os mapas da previsão sazonal calibrada  #
    #-----------------------------------------# 
    if model == "multimodel":
        grads_cmd = (
            f"run {grads_script_multimodel} "
            f"{fcst_date} {version_multimodel} {base} {var} {calib}"
        )
    else:
        grads_cmd = (
            f"run {grads_script_model} "
            f"{fcst_date} {model_dir} {model_title} {version_multimodel} {base} {var} {calib}"
        )

    print("Comando GrADS:")
    print(grads_cmd)

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

    # #-----------------------------------------#
    # #    Rodar Scripts Grads que geram        #
    # # os mapas da previsão sazonal calibrada  #
    # #-----------------------------------------# 
    # if model == "multimodel":
    #     cmd = f"grads -blc 'run {grads_script_multimodel} {fcst_date} {version_multimodel} {base} {var} {calib}'"
    #     print(cmd)
    # else:
    #     cmd = f'grads -blc "run {grads_script_model} {fcst_date} {model_dir} {model_title} {version_multimodel} {base} {var} {calib}"'


def run_grads_maps_seasonal_verification(year_fcst, month_fcst, base, model, var, calib):

    #------------------------------#
    # Define os argumentos usados  #
    # para rodar os scripts grads  #
    #------------------------------#

    if base == "copernicus":
        model_dir = ConfigModelos.get_model_dir_c3s(model)
        model_title = ConfigModelos.get_model_title_c3s(model)

    elif base == "nmme":
        model_dir = ConfigModelos.get_model_dir_nmme(model)
        model_title = ConfigModelos.get_model_title_nmme(model)

    grads_script_model = "/scripts/clima/denis/seasonal/src/maps/verif_maps_seasonal_models.gs"
    grads_script_multimodel = "/scripts/clima/denis/seasonal/src/maps/verif_maps_seasonal_multimodel.gs"

    version_multimodel = ConfigModelos.get_multimodel_version(base)

    if model != "multimodel":
        print("Nome do diretorio do modelo:", model_dir)
        print("Nome do modelo no título dos mapas:", model_title)
    else:
        print(f"Gerando os mapas de verificação do Multimodelo {base.upper()}")

    month = f"{month_fcst:02d}"
    fcst_date = f"{year_fcst}{month}0100"
    month_name = datetime(2000, month_fcst, 1).strftime('%b').upper()
    #grads -lbc "run verif_maps_seasonal_models.gs 2025020100 FEB canesm5 CanESM5 v1 nmme prec nocalib"

    #-----------------------------------------#
    #    Rodar Scripts Grads que geram        #
    # os mapas da previsão sazonal calibrada  #
    #-----------------------------------------# 
    if model == "multimodel":
        grads_cmd = (
            f"run {grads_script_multimodel} "
            f"{fcst_date} {month_name} {version_multimodel} {base} {var} {calib}"
        )
    else:
        grads_cmd = (
            f"run {grads_script_model} "
            f"{fcst_date} {month_name} {model_dir} {model_title} {version_multimodel} {base} {var} {calib}"
        )

    print("Comando GrADS:")
    print(grads_cmd)

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

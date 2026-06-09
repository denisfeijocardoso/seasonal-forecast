import os
import time
import glob
import subprocess
import argparse
from src.utils.seasonal_forecast_utils import  Run
from src.curves.plot_curves_seasonal import  Curves
from src.config.config_models import ConfigModelos
from src.config.config_path import path_hcst, path_fcst, path_obs
from src.calibration.calibr_fcst_seasonal import Calibration

#============#
# ARGUMENTOS #
#============#
parser = argparse.ArgumentParser(description="Rodar geração dos produtos de Previsão Sazonal")
parser.add_argument("--year", type=int, required=True)
parser.add_argument("--month", type=int, required=True)

args = parser.parse_args()

year_fcst = args.year
month_fcst = args.month
month_str = f"{month_fcst:02d}"

#================================================#
# Executa o processo que baixa, interpola e gera #
# as previsões sazonais calibradas em tempo-real #
#   para o multimodelo e modelos individuais     #
#================================================#
varis = ["prec", "t2mt"]
bases = ["nmme", "copernicus"]
calibs = ["regr","cox","nocalib"]

inicio = time.time()  # <<< Início da contagem

##=============================================================##
##GERAÇÃO DOS ARQUIVOS NETCDF DAS PREVISÕES SAZONAIS CALIBRADAS##
##=============================================================##
for base in bases:
    for var in varis:
        Run.run_realtime_seasonal(year_fcst, month_fcst, base, var)

#===================================================#
#CRIAÇÃO DOS MAPAS DAS PREVISÕES SAZONAIS CALIBRADAS#
#===================================================#

for base in bases:

    version_multimodel = ConfigModelos.get_multimodel_version(base)

    for var in varis:   
    
        #------CHECA QUAIS MODELOS ESTÃO DISPONÍVES (SE OS ARQUIVOS FORAM BAIXADOS)-----#
        models_available = Calibration.check_models(base, path_fcst, year_fcst, month_fcst, var)
#        models_to_run = ["multimodel"] + models_available    
        models_to_run = models_available   

        print(f"Modelos disponíveis (forecast): {models_available}")

        #-----RODA OS SCRIPTS GRADS------#
        for model in models_to_run:

            if model != "multimodel":
                if base == "copernicus":
                    name_model_dir = ConfigModelos.get_model_dir_c3s(model)

                elif base == "nmme":
                    name_model_dir = ConfigModelos.get_model_dir_nmme(model)
            else:
                name_model_dir = "multimodel"

            for calib in calibs:

                path_fcst_nc = (
                    f"/dados/mmclima/multimodelo/seasonal/posproc/{base}/"
                    f"{version_multimodel}/forecast/{calib}/{name_model_dir}/"
                    f"{year_fcst}/{year_fcst}{month_str}0100/")

                pattern_files = os.path.join(path_fcst_nc,
                    f"fcst_{var}*{name_model_dir}*{calib}_{year_fcst}{month_str}0100.nc")

                print(f"fcst_{var}*{name_model_dir}*{calib}_{year_fcst}{month_str}0100.nc")

                files = glob.glob(pattern_files)

                if files:
                    Run.run_grads_maps_seasonal(year_fcst, month_fcst, base, model, var, calib)
                else:
                    print(f"Arquivos NetCDF das previsões sazonais ({name_model_dir} - {var} - {calib}) não foram gerados.")

#================================================================#
#CRIAÇÃO DAS CURVAS DE DISTRIBUIÇÃO PARA CADA PONTO SOBRE O GLOBO#
#================================================================#
calibs = ["regr","cox"]

fcst_date = f"{year_fcst}{month_str}01"

for base in bases:

    for calib in calibs:   

        Curves.create_curves(fcst_date, base, "multimodel", calib)   


fim = time.time()  # <<< Fim da contagem
print(f"Tempo total: {(fim - inicio)/60:.2f} minutos")





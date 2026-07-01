import argparse
import logging
from .realtime import run_realtime_forecast
from .download import run_download_realtime_models
from .interpolation import run_interpolation_forecast_models
from src.io.netcdf_writer import write_results_netcdf
from src.config.config_models import check_models, get_list_models
from src.config.loader import PARAMETERS_RUN, MODELS_CONFIG
from src.config.config_logging import setup_logging



# --------------------------------------------
# Argumentos (recebidos na execução do módulo)
# --------------------------------------------

parser = argparse.ArgumentParser(description="Rodar geração das previsões sazonais em tempo-real.")
parser.add_argument("--year", type=int, required=True)
parser.add_argument("--month", type=int, required=True)

args = parser.parse_args()

year_fcst = args.year
month_fcst = args.month

# --------------------
# Configuração do Log
# --------------------

setup_logging(
    year_fcst,
    month_fcst
)

logger = logging.getLogger(__name__)

logger.info(
    "Processando previsão de %d/%d", 
    year_fcst, 
    month_fcst
)

# -------------
# Parâmetros
# -------------

data_bases = PARAMETERS_RUN["bases"]
variables = PARAMETERS_RUN["variables"]
types_calibration = PARAMETERS_RUN["calibrations"]
model_target = "cfs"
var = variables[0]
base = "nmme"

# ------------------------------------
# Download das previsões em tempo-real
# ------------------------------------
models = list(get_list_models(base))

no_download_models = {"cansips", "bam", "echam"}

models_to_download = [
    model
    for model in models
    if model not in no_download_models
]

run_download_realtime_models(
    base,
    models_to_download,
    var,
    year_fcst,
    month_fcst
)


# --------------------------------------
# Checa quais modelos estão disponíveis
# --------------------------------------

models_available = check_models(
    base,
    var,
    year_fcst,
    month_fcst
)

print("Modelos disponíveis: ", models_available)

# -----------------------------------------------
# Interpola os arquivos baixados p/ grade do GPCP
# -----------------------------------------------

run_interpolation_forecast_models(
    base,
    models_available,
    var,
    year_fcst,
    month_fcst
)


# ---------------------------------
# Executa a geração dos resultados
# --------------------------------

results = run_realtime_forecast(
    base,
    model_target,
    var,
    year_fcst, 
    month_fcst,
    models_available
)


results_cox = results["cox"]

results_regr = results["regr"]

results_nocalib = results["nocalib"]

# -----------------------------
# Escreve os arquivos NetCDF
# ----------------------------

write_results_netcdf(
    results_cox,
    base,
    model_target,
    var,
    "cox",
    year_fcst,
    month_fcst
)

write_results_netcdf(
    results_regr,
    base,
    model_target,
    var,
    "regr",
    year_fcst,
    month_fcst
)

write_results_netcdf(
    results_nocalib,
    base,
    model_target,
    var,
    "nocalib",
    year_fcst,
    month_fcst
)

# list_models = MODELS_CONFIG["bases"][base]["models"]

# for model in list_models:



# #================================================#
# # Executa o processo que baixa, interpola e gera #
# # as previsões sazonais calibradas em tempo-real #
# #   para o multimodelo e modelos individuais     #
# #================================================#
# varis = ["prec", "t2mt"]
# bases = ["nmme", "copernicus"]
# calibs = ["regr","cox","nocalib"]

# inicio = time.time()  # <<< Início da contagem

# ##=============================================================##
# ##GERAÇÃO DOS ARQUIVOS NETCDF DAS PREVISÕES SAZONAIS CALIBRADAS##
# ##=============================================================##
# for base in bases:
#     for var in varis:
#         Run.run_realtime_seasonal(year_fcst, month_fcst, base, var)

# #===================================================#
# #CRIAÇÃO DOS MAPAS DAS PREVISÕES SAZONAIS CALIBRADAS#
# #===================================================#

# for base in bases:

#     version_multimodel = ConfigModelos.get_multimodel_version(base)

#     for var in varis:   
    
#         #------CHECA QUAIS MODELOS ESTÃO DISPONÍVES (SE OS ARQUIVOS FORAM BAIXADOS)-----#
#         models_available = Calibration.check_models(base, path_fcst, year_fcst, month_fcst, var)
# #        models_to_run = ["multimodel"] + models_available    
#         models_to_run = models_available   

#         print(f"Modelos disponíveis (forecast): {models_available}")

#         #-----RODA OS SCRIPTS GRADS------#
#         for model in models_to_run:

#             if model != "multimodel":
#                 if base == "copernicus":
#                     name_model_dir = ConfigModelos.get_model_dir_c3s(model)

#                 elif base == "nmme":
#                     name_model_dir = ConfigModelos.get_model_dir_nmme(model)
#             else:
#                 name_model_dir = "multimodel"

#             for calib in calibs:

#                 path_fcst_nc = (
#                     f"/dados/mmclima/multimodelo/seasonal/posproc/{base}/"
#                     f"{version_multimodel}/forecast/{calib}/{name_model_dir}/"
#                     f"{year_fcst}/{year_fcst}{month_str}0100/")

#                 pattern_files = os.path.join(path_fcst_nc,
#                     f"fcst_{var}*{name_model_dir}*{calib}_{year_fcst}{month_str}0100.nc")

#                 print(f"fcst_{var}*{name_model_dir}*{calib}_{year_fcst}{month_str}0100.nc")

#                 files = glob.glob(pattern_files)

#                 if files:
#                     Run.run_grads_maps_seasonal(year_fcst, month_fcst, base, model, var, calib)
#                 else:
#                     print(f"Arquivos NetCDF das previsões sazonais ({name_model_dir} - {var} - {calib}) não foram gerados.")

# #================================================================#
# #CRIAÇÃO DAS CURVAS DE DISTRIBUIÇÃO PARA CADA PONTO SOBRE O GLOBO#
# #================================================================#
# calibs = ["regr","cox"]

# fcst_date = f"{year_fcst}{month_str}01"

# for base in bases:

#     for calib in calibs:   

#         Curves.create_curves(fcst_date, base, "multimodel", calib)   


# fim = time.time()  # <<< Fim da contagem
# print(f"Tempo total: {(fim - inicio)/60:.2f} minutos")





import os
import time
import glob
import subprocess
import argparse
import yaml
import src.run.seasonal_forecast_utils as run
from src.config.config_models_seasonal import ConfigModelos
from src.config.config_dir_seasonal import path_hcst, path_fcst, path_obs
from src.verification.calibr_verif_seasonal import Calibration
from src.verification.obs_verif_seasonal import Observation

#python3 -m src.run.run_seasonal_verification --year 2026 --month 1 --base "nmme"

def parse_args():
    """Parse dos argumentos da linha de comando."""
    parser = argparse.ArgumentParser(
        description="Rodar verificação da previsão sazonal"
    )
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--base", type=str, required=True)

    return parser.parse_args()


def run_hindcast(bases):
    """Executa o loop de hindcast."""
    for base in bases:
        print(f"Rodando base: {base}")
        models = get_models(base)

        for model in models:
            print(f"  Modelo: {model}")
            # aqui entra sua lógica real
            # run.alguma_funcao(...)

    for base_name, base_data in bases.items():
        print(base_name)
        
        models = base_data["models"]

        for model in models:
            for var in variables:
                for calib in calibs:
                    print(base_name, model, var, calib)

def main():
    args = parse_args()

    year_fcst = args.year
    month_fcst = args.month
    month_str = f"{month_fcst:02d}"

    with open("/scripts/clima/denis/seasonal/src/config/config_parameters.yaml") as f:
        config = yaml.safe_load(f)

    variables = config["variables"]
    calibs = config["calibrations"]
    bases = config["bases"]

    inicio = time.time()

    #run_hindcast(bases)

    fim = time.time()
    print(f"Tempo total: {fim - inicio:.2f} segundos")

#


varis = ["prec", "t2mt"]
bases = ["nmme"] #"copernicus"
calibs = ["nocalib"] #"regr","cox",

inicio = time.time()  # <<< Início da contagem

base_models = {
    "nmme": [
        "multimodel","canesm5", "ccsm4", "cesm1", "cfsv2",
        "gem52nemo", "geos5v2", "spear","bam12"
    ],
    "copernicus": [
        "multimodel","ecmwf", "ukmo","meteo_france","dwd",
        "cmcc","ncep","jma","eccc4","eccc5","bom","bam12"
    ]
}

def run_pipeline(base, model, var, month_fcst, type_calibration):
    if type_calibration == "regr":
        return run_regr(...)
    elif type_calibration == "cox":
        return run_cox(...)
    elif type_calibration == "nocalib":
        return run_nocalib(...)

def compute_metrics_calib(obs_anomaly, obs_total,
    fcst_calib_anomaly, fcst_calib_med,
    prob_below_med, prob_below_inf, prob_above_sup,
    binobsmed, binobsinf, binobssup):
    """Calcula as métricas de verificação (método calibração Regressão)"""

    return {
        "cor": Calibration.corr_verif(obs_anomaly, fcst_calib_anomaly),

        "auroc_mean": Calibration.area_roc(binobsmed, prob_below_med),
        "auroc_inf": Calibration.area_roc(binobsinf, prob_below_inf),
        "auroc_sup": Calibration.area_roc(binobssup, prob_above_sup),

        "msss": Calibration.msss_skill(fcst_calib_anomaly, obs_anomaly),

        "bias": Calibration.compute_bias(fcst_calib_med, obs_total),

        "fase_amp": Calibration.msss_fase_amplitude(fcst_calib_anomaly, obs_anomaly)
    }

def save_netcdf_calib(base, calib, year_fcst, month_fcst, model, var, metrics, probs, bins):
    """Salva os campos com as métricas de verificação em arquivos NetCDF"""
    Calibration.write_netcdf_model_calibrated(
        base, year_fcst, month_fcst, model,
        var, calib,

        metrics["cor"],

        probs["mean"], probs["inf"], probs["sup"],
        bins["mean"], bins["inf"], bins["sup"],

        metrics["auroc_mean"],
        metrics["auroc_inf"],
        metrics["auroc_sup"],

        metrics["msss"],
        metrics["fase_amp"][0],
        metrics["fase_amp"][1],
        metrics["bias"]
    )

def run_calib(path_fcst, path_hcst, path_obs, base, calib, year_fcst, month_fcst, model, var):
    """Executa o método de calibração escolhido (geração das previsões)"""

    CALIBRATION_METHODS = {
        "regr": Calibration.regression_calibration_model,
        "cox": Calibration.calibration_cox_model
    }

    try:
        func = CALIBRATION_METHODS[calib]
    except KeyError:
        raise ValueError(f"Calibração desconhecida: {calib}")
    
    results = func(
        path_fcst, path_hcst, path_obs,
        base, year_fcst, month_fcst, model, var
    )

    (obs_anomaly, obs_total,
     fcst_calib_anomaly, fcst_calib_med,
     prob_med, prob_inf, prob_sup,
     bin_med, bin_inf, bin_sup) = results

    metrics = compute_metrics_calib(obs_anomaly, obs_total,
    fcst_calib_anomaly, fcst_calib_med,
    prob_med, prob_inf, prob_sup,
    bin_med, bin_inf, bin_sup)

    probs = {
        "mean": prob_med,
        "inf": prob_inf,
        "sup": prob_sup,
        }

    bins = {
        "mean": bin_med,
        "inf": bin_inf,
        "sup": bin_sup,
        }
    
    save_netcdf_calib(base, calib, year_fcst, month_fcst, model, var, metrics, probs, bins)

args = parse_args()

base = args.base
year_fcst = args.year
month_fcst = args.month
month_str = f"{month_fcst:02d}"

obs = Observation(path_obs)
statistcs = obs.mean_std_anom_obs(base, month_fcst, "prec") 
print()
quit()
orderd_periods = list(statistics.items())[0]
quit()

def obs_stats(path_obs,base,month_fcst,var):
    """ Escreve as estatítiscas das observações necessárias para gerar o não-calibrado """
    obs = Observation(path_obs)
    statistcs = obs.mean_std_anom_obs(base, month_fcst, var) 
    orderd_periods = list(statistcs.keys())

    obs_total = np.stack([statistcs[p]['total'] for p in statistcs.keys()])

    obs_total = np.stack([statistcs[p]['total'] for p in ordered_periods], axis=1)
    obs_anomaly = np.stack([statistcs[p]['anomaly'] for p in ordered_periods], axis=1)
    obs_mean = np.stack([statistcs[p]['mean'] for p in ordered_periods], axis=1)
    obs_tercinf = np.stack([statistcs[p]['tercilinf'] for p in ordered_periods], axis=1)
    obs_tercsup = np.stack([statistcs[p]['tercilsup'] for p in ordered_periods], axis=1)

    anom = {k: v['anomaly'] for k, v in statistcs.items() if 'anomaly' in v}
    mean = {k: v['mean'] for k, v in statistcs.items() if 'mean' in v} 
    tercil_inf = {k: v['tercilinf'] for k, v in statistcs.items() if 'tercilinf' in v}    
    tercil_sup = {k: v['tercilsup'] for k, v in statistcs.items() if 'tercilsup' in v}   
    total = {k: v['total'] for k, v in statistcs.items() if 'total' in v}   

    #Transformar em array
    ordered_periods = list(anom.keys()) 
    obs_total = np.stack([total[p] for p in ordered_periods], axis=1)
    obs_anomaly = np.stack([anom[p] for p in ordered_periods], axis=1)
    obs_mean = np.stack([mean[p] for p in ordered_periods], axis=1)
    obs_tercinf = np.stack([tercil_inf[p] for p in ordered_periods], axis=1)
    obs_tercsup = np.stack([tercil_sup[p] for p in ordered_periods], axis=1)    

    # --- Binários ---
    binobsinf = (obs_total <= obs_tercinf).astype(int)
    binobssup = (obs_total >= obs_tercsup).astype(int)
    binobsmed = (obs_total <= obs_mean).astype(int)

    statsobs = {
        "obs_total": obs_total,
        "obs_anomaly": obs_anomaly,
        "obs_mean": obs_mean,
        "obs_tercinf": obs_tercinf,
        "obs_tercsup": obs_tercsup,
        "binobsinf": binobsinf,
        "binobssup": binobssup,
        "binobsmed":binobsmed
    }


def run_nocalib(path_fcst, path_hcst, path_obs, base, calib, year_fcst, month_fcst, model, var):
    """Executa o método de calibração escolhido (geração das previsões)"""

    CALIBRATION_METHODS = {
        "regr": Calibration.regression_calibration_model,
        "cox": Calibration.calibration_cox_model
    }

    try:
        func = CALIBRATION_METHODS[calib]
    except KeyError:
        raise ValueError(f"Calibração desconhecida: {calib}")
    
    results = func(
        path_fcst, path_hcst, path_obs,
        base, year_fcst, month_fcst, model, var
    )

    (obs_anomaly, obs_total,
     fcst_calib_anomaly, fcst_calib_med,
     prob_med, prob_inf, prob_sup,
     bin_med, bin_inf, bin_sup) = results

    metrics = compute_metrics_calib(obs_anomaly, obs_total,
    fcst_calib_anomaly, fcst_calib_med,
    prob_med, prob_inf, prob_sup,
    bin_med, bin_inf, bin_sup)

    probs = {
        "mean": prob_med,
        "inf": prob_inf,
        "sup": prob_sup,
        }

    bins = {
        "mean": bin_med,
        "inf": bin_inf,
        "sup": bin_sup,
        }
    
    save_netcdf_calib(base, calib, year_fcst, month_fcst, model, var, metrics, probs, bins)

# ####################
# # --- Hindcast --- #
# ####################
# for base in bases:

#     models = base_models[base]

#     for var in varis:
#         for type_calibration in type_calibrations:
#             for model in models:
#                 for month_fcst in months:
#                     print(type_calibration)
#                     print(month_fcst)  
#                     print(model)
#                     print(var)
                    
#                     # if type_calibration == "regr": 
#                     #     #Gera a previsão calibrada (método da Regressão)
#                     #     (obs_anomaly, obs_total, fcst_calib_anomaly, fcst_calib_mean, prob_below_mean, prob_below_inf, 
#                     #     prob_above_sup, binobsmed, binobsinf, binobssup) = Calibration.regression_calibration_model(path_fcst, path_hcst, path_obs, base, year_fcst, month_fcst, model, var)

#                     #     #Area sob a curva ROC
#                     #     auroc_below_mean = Calibration.area_roc(binobsmed, prob_below_mean)
#                     #     auroc_below_inf = Calibration.area_roc(binobsinf, prob_below_inf)
#                     #     auroc_above_sup = Calibration.area_roc(binobssup, prob_above_sup)

#                     #     #Correlação
#                     #     cor_anom_verif = Calibration.corr_verif(obs_anomaly, fcst_calib_anomaly)

#                     #     #Índice de destreza do Erro Quadrático Médio e Fase/Amplitude
#                     #     msss_skill = Calibration.msss_skill(fcst_calib_anomaly, obs_anomaly)
#                     #     bias = Calibration.compute_bias(fcst_calib_mean, obs_total)
#                     #     msss_fase, msss_amplitude = Calibration.msss_fase_amplitude(fcst_calib_anomaly, obs_anomaly)

#                     #     Calibration.write_netcdf_model_calibrated(base, year_fcst, month_fcst, model,
#                     #     var, type_calibration, cor_anom_verif, prob_below_mean, prob_below_inf, 
#                     #     prob_above_sup, binobsmed, binobsinf, binobssup, auroc_below_mean, auroc_below_inf, auroc_above_sup,
#                     #     msss_skill, msss_fase, msss_amplitude, bias)

#                     # elif type_calibration == "cox":
#                     #     #Gera a previsão calibrada (método COX)
#                     #     (obs_anomaly, obs_total, mediana_fcst_cox, anomalia_fcst_cox, probexc_mediana, prob_below_inf, 
#                     #     prob_above_sup, binobsmediana, binobsinf, binobssup) = Calibration.calibration_cox_model(path_fcst, path_hcst, path_obs, base, year_fcst, month_fcst, model, var)

#                     #     #Area sob a curva ROC
#                     #     auroc_below_mean = Calibration.area_roc(binobsmediana, probexc_mediana)
#                     #     auroc_below_inf = Calibration.area_roc(binobsinf, prob_below_inf)
#                     #     auroc_above_sup = Calibration.area_roc(binobssup, prob_above_sup)

#                     #     #Correlação
#                     #     cor_anom_verif = Calibration.corr_verif(obs_anomaly, anomalia_fcst_cox)
#                     #     #cor_total_verif = Calibration.corr_verif(obs_total, mediana_fcst_cox)

#                     #     #Índice de destreza do Erro Quadrático Médio e Fase/Amplitude
#                     #     msss_skill = Calibration.msss_skill(anomalia_fcst_cox, obs_anomaly)
#                     #     bias = Calibration.compute_bias(mediana_fcst_cox, obs_total)
#                     #     msss_fase, msss_amplitude = Calibration.msss_fase_amplitude(anomalia_fcst_cox, obs_anomaly)

#                     #     Calibration.write_netcdf_model_calibrated(base, year_fcst, month_fcst, model,
#                     #     var, type_calibration, cor_anom_verif, probexc_mediana, prob_below_inf, 
#                     #     prob_above_sup, binobsmediana, binobsinf, binobssup, auroc_below_mean, auroc_below_inf, auroc_above_sup,
#                     #     msss_skill, msss_fase, msss_amplitude, bias)

# base_models = {
#     "nmme": [
#         "multimodel","canesm5", "ccsm4", "cesm1", "cfsv2",
#         "gem52nemo", "geos5v2", "spear","bam12"
#     ],
#     "copernicus": [
#         "multimodel","ecmwf", "ukmo","meteo_france","dwd",
#         "cmcc","ncep","jma","eccc4","eccc5","bom","bam12"
#     ]
# }

#                     elif type_calibration == "nocalib":

#                         #OBSERVATION
#                         obs = Observation(path_obs)
#                         statistcs = obs.mean_std_anom_obs(base, month_fcst, var) 
#                         anom = {k: v['anomaly'] for k, v in statistcs.items() if 'anomaly' in v}
#                         std = {k: v['std'] for k, v in statistcs.items() if 'std' in v}
#                         mean = {k: v['mean'] for k, v in statistcs.items() if 'mean' in v} 
#                         mediana =  {k: v['mediana'] for k, v in statistcs.items() if 'mediana' in v}   
#                         tercil_inf = {k: v['tercilinf'] for k, v in statistcs.items() if 'tercilinf' in v}    
#                         tercil_sup = {k: v['tercilsup'] for k, v in statistcs.items() if 'tercilsup' in v}   
#                         total = {k: v['total'] for k, v in statistcs.items() if 'total' in v}   

#                         #Transformar em array
#                         ordered_periods = list(anom.keys()) 
#                         obs_total = np.stack([total[p] for p in ordered_periods], axis=1)
#                         obs_anomaly = np.stack([anom[p] for p in ordered_periods], axis=1)
#                         obs_mean = np.stack([mean[p] for p in ordered_periods], axis=1)
#                         obs_mediana = np.stack([mediana[p] for p in ordered_periods], axis=1)        
#                         obs_tercinf = np.stack([tercil_inf[p] for p in ordered_periods], axis=1)
#                         obs_tercsup = np.stack([tercil_sup[p] for p in ordered_periods], axis=1)    
        
#                         # --- Binários ---
#                         binobsinf = (obs_total <= obs_tercinf).astype(int)
#                         binobssup = (obs_total >= obs_tercsup).astype(int)
#                         binobsmed = (obs_total <= obs_mean).astype(int)

#                         #VERIFICAÇÃO NÃO-CALIBRADA MULTIMODELO
#                         if model == "multimodel":
#                             models_available = models

#                             # model_names = [model if base == "nmme" else ConfigModelos.get_model_dir(model)
#                             # for model in models_available]

#                             prob_tinf_results, prob_tsup_results, prob_mean_results = [], [], []

#                             for mdl in models_available:    
#                                 print(f"Cálculo Prob. Multimodelo - processando: {mdl}")
#                                 name_model = mdl if base == "nmme" else ConfigModelos.get_model_dir(mdl)
#                                 (prob_below_inf, prob_above_sup, 
#                                 prob_below_mean) = Calibration.nocalibration_model(base, month_fcst, mdl, 
#                                                                     var, year_fcst, path_fcst, path_hcst)
#                                 prob_tinf_results.append(prob_below_inf)
#                                 prob_tsup_results.append(prob_above_sup)
#                                 prob_mean_results.append(prob_below_mean)

#                             # Média multi-modelo das probabilidades 
#                             multimodel_ptinf = np.nanmean(prob_tinf_results, axis=0)
#                             multimodel_ptsup = np.nanmean(prob_tsup_results, axis=0)
#                             multimodel_pmean = np.nanmean(prob_mean_results, axis=0)                                                                                                           
                            
#                             hindcast = Hindcast(path_fcst, path_hcst) 
#                             hcst_total_ensmean, _, _, hcst_anomaly = hindcast.mean_std_anom_hindcast(base, 
#                                                                         year_fcst, month_fcst, model, var)     

#                             #Correlações e índices de destreza
#                             cor_anom_verif = Calibration.corr_verif(obs_anomaly, hcst_anomaly)
#                             auroc_below_mean = Calibration.area_roc(binobsmed, multimodel_pmean)
#                             auroc_below_inf = Calibration.area_roc(binobsinf, multimodel_ptinf)
#                             auroc_above_sup = Calibration.area_roc(binobssup, multimodel_ptsup)
#                             msss_skill = Calibration.msss_skill(hcst_anomaly, obs_anomaly)
#                             bias = Calibration.compute_bias(hcst_total_ensmean, obs_total)
#                             msss_fase, msss_amplitude = Calibration.msss_fase_amplitude(hcst_anomaly, obs_anomaly)

#                             #Escrever os arquivos NetCDF
#                             Calibration.write_netcdf_model_nocalibrated(base, year_fcst, month_fcst, model,
#                             var, cor_anom_verif, prob_below_mean, prob_below_inf, prob_above_sup,
#                             binobsmed, binobsinf, binobssup, auroc_below_mean, auroc_below_inf, auroc_above_sup,
#                             msss_skill, msss_fase, msss_amplitude, bias)

#                         #VERIFICAÇÃO NÃO-CALIBRADA MODELOS SEPARADOS
#                         else:
#                             name_model = model if base == "nmme" else ConfigModelos.get_model_dir(model)

#                             (prob_below_inf, prob_above_sup, 
#                             prob_below_mean) = Calibration.nocalibration_model(base, month_fcst, model, 
#                                                                     var, year_fcst, path_fcst, path_hcst)

#                             hindcast = Hindcast(path_fcst, path_hcst) 
#                             hcst_total_ensmean, _, _, hcst_anomaly = hindcast.mean_std_anom_hindcast(base, 
#                                                                         year_fcst, month_fcst, model, var)     

#                             #Correlações e índices de destreza
#                             cor_anom_verif = Calibration.corr_verif(obs_anomaly, hcst_anomaly)
#                             auroc_below_mean = Calibration.area_roc(binobsmed, prob_below_mean)
#                             auroc_below_inf = Calibration.area_roc(binobsinf, prob_below_inf)
#                             auroc_above_sup = Calibration.area_roc(binobssup, prob_above_sup)
#                             msss_skill = Calibration.msss_skill(hcst_anomaly, obs_anomaly)
#                             bias = Calibration.compute_bias(hcst_total_ensmean, obs_total)
#                             msss_fase, msss_amplitude = Calibration.msss_fase_amplitude(hcst_anomaly, obs_anomaly)

#                             #Escrever os arquivos NetCDF
#                             Calibration.write_netcdf_model_nocalibrated(base, year_fcst, month_fcst, model,
#                             var, cor_anom_verif, prob_below_mean, prob_below_inf, prob_above_sup,
#                             binobsmed, binobsinf, binobssup, auroc_below_mean, auroc_below_inf, auroc_above_sup,
#                             msss_skill, msss_fase, msss_amplitude, bias)



# #====================================================================#
# #CRIAÇÃO DOS MAPAS DAS VERIFICAÇÕES DAS PREVISÕES SAZONAIS CALIBRADAS#
# #====================================================================#

# for base in bases:

#     version_multimodel = ConfigModelos.get_multimodel_version(base)

#     for var in varis:   

#         #-----RODA OS SCRIPTS GRADS------#
#         for model in models:

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
#                     f"{version_multimodel}/verification/{calib}/{name_model_dir}/"
#                     )

#                 pattern_files = os.path.join(path_fcst_nc,
#                     f"{var}*{name_model_dir}*{calib}_{year_fcst}{month_str}0100.nc")

#                 print(f"{var}*{name_model_dir}*{calib}_{year_fcst}{month_str}0100.nc")

#                 files = glob.glob(pattern_files)

#                 if files:
#                     run.run_grads_maps_seasonal_verification(year_fcst, month_fcst, base, model, var, calib)
#                 else:
#                     print(f"Arquivos NetCDF das previsões sazonais ({name_model_dir} - {var} - {calib}) não foram gerados.")

# #==============================================================================#
# #CRIAÇÃO DOS DIAGRAMAS ROC/CONFIABILIDADE DE VERIFICAÇÃO DAS PREVISÕES SAZONAIS#
# #==============================================================================#

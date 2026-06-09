import os
import pandas as pd
import numpy as np
import xarray as xr
import scipy.stats as stats
import netCDF4 as nc
import calendar
from scipy.stats import kstest
from datetime import date, datetime,timedelta
from dateutil.relativedelta import *
from src.forecast.forecast_seasonal import Forecast
from src.hindcast.hindcast_seasonal import Hindcast
from src.observation.observation_seasonal import Observation
from src.config.config_models import ConfigModelos
from src.config.config_path import path_hcst, path_fcst, path_obs
from scipy.stats import gamma, norm
from scipy.stats import pearsonr 
from joblib import Parallel, delayed
from lifelines import CoxPHFitter

##################################################
#CLASSE COM A FUNÇÃO PARA CALCULAR AS CALIBRAÇÕES#
##################################################

class Calibration:
    """
    Gera as previsões multimodelo e modelo calibradas

    Parâmetros usados:
        path_obs (str): Caminho para os dados observacionais.
        path_fcst (str): Caminho para os dados de previsão.
        path_hcst (str): Caminho para os dados de hindcast.
        fcst_date (datetime.date): Data de referência da previsão.
        model (str): Nome do modelo (se é multimodelo = "multimodel")
        var (str): Variável de interesse.

    Retorna:
        xarray.DataArray: Mapa de correlação (period, lat, lon),
        onde period multimodelo é 'week01','week02', 'week03', 'week04', 'fort01', 'fort02', '3wks01', 'mnth01', 'ds4401'
    """


    @staticmethod  
    def regression_calibration_model(path_fcst, path_hcst, path_obs, base, year_fcst, month_fcst, model, var):
        ''' Calibração das previsões em tempo-real através do método da regressão '''

        # --- Observação
        obs = Observation(path_obs)
        statistcs = obs.mean_std_anom_obs(base, month_fcst, var) 
        anom = {k: v['anomaly'] for k, v in statistcs.items() if 'anomaly' in v}
        std = {k: v['std'] for k, v in statistcs.items() if 'std' in v}
        mean = {k: v['mean'] for k, v in statistcs.items() if 'mean' in v}     
        mediana = {k: v['mediana'] for k, v in statistcs.items() if 'mean' in v}           
        tercil_inf = {k: v['tercilinf'] for k, v in statistcs.items() if 'tercilinf' in v}    
        tercil_sup = {k: v['tercilsup'] for k, v in statistcs.items() if 'tercilsup' in v}   
        total = {k: v['total'] for k, v in statistcs.items() if 'total' in v}   

        #transformar em array
        ordered_periods = list(anom.keys()) 
        obs_series = np.stack([obs.calculate_obs_periods(base, month_fcst, var)[p] for p in ordered_periods], axis=0)
        obs_total = np.stack([total[p] for p in ordered_periods], axis=0)
        obs_anomaly = np.stack([anom[p] for p in ordered_periods], axis=1)
        obs_std = np.stack([std[p] for p in ordered_periods], axis=0)
        obs_mean = np.stack([mean[p] for p in ordered_periods], axis=0)
        obs_mediana = np.stack([mediana[p] for p in ordered_periods], axis=0)        
        obs_tercinf = np.stack([tercil_inf[p] for p in ordered_periods], axis=0)
        obs_tercsup = np.stack([tercil_sup[p] for p in ordered_periods], axis=0)   
        
        # --- Hindcast
        hindcast = Hindcast(path_fcst, path_hcst)
        model_hcst, hcst_mean, hcst_std, hcst_anomaly = hindcast.mean_std_anom_hindcast(base, year_fcst, month_fcst, model, var)     

        if model_hcst is None:
            raise ValueError("Sem modelos suficientes para gerar o Multimodelo\n")

        # --- Previsão tempo-real (Forecast)
        #models_available = Calibration.check_models(base, path_fcst, year_fcst, month_fcst, var)
        if model == "multimodel":
            forecast = Forecast(path_fcst)
            realtime_fcst = forecast.forecast_multimodel(base, year_fcst, month_fcst, var)
        else:
            forecast = Forecast(path_fcst)
            model_fcst = forecast.read_fcst_file(base, year_fcst, month_fcst, model, var)
            fcst_dict = forecast.calculate_fcst_periods(base, year_fcst, month_fcst, model, model_fcst, var)
            realtime_fcst = forecast.dict_to_array(base, fcst_dict, ["mnth00","mnth01","mnth02","mnth03","mnth04","seas00","seas01","seas02"], var)

        # --- Correlação
        model_cor = Calibration.correlation_model(obs_anomaly, hcst_anomaly, year_fcst, month_fcst, model, var)

        # ---- Calibração
        anomaly_multimodel = (realtime_fcst) - (hcst_mean)

        prediction_signal = (anomaly_multimodel) / (hcst_std)
        fcst_stdev = np.sqrt( 1 - (model_cor ** 2))
        fcst_mean_stand = prediction_signal * model_cor #Forecast Mean (standardized)
        fcst_mm = (fcst_mean_stand * obs_std) #Anomaly calibrated

        sefcst = (obs_std) * (np.sqrt( 1 - (model_cor ** 2))) #Forecast Standard Deviation (in millimeters)
        fsfcst = (fcst_mean_stand * obs_std) + (obs_mean) #Forecast Mean (in millimeters)    

        if var == "prec":
            fsfcst[fsfcst < 0] = 0
        #

        #--- Probabilidade acima/abaixo da média (calibrada)
        prob_below_calib = stats.norm(fsfcst, sefcst).cdf(obs_mean)
        prob_above_calib = (1 - (stats.norm(fsfcst, sefcst).cdf(obs_mean))) * 100

        #--- Probabilidade acima/abaixo dos tercis (calibrada)
        sefcst_stand = (np.sqrt( 1 - (model_cor ** 2)))

        prob_below_tercinf = stats.norm(fsfcst, sefcst).cdf(obs_tercinf) * 100
        prob_above_tercinf = ( 1 - stats.norm(fsfcst, sefcst).cdf(obs_tercinf)) * 100  

        prob_below_tercsup = stats.norm(fsfcst, sefcst).cdf(obs_tercsup) * 100
        prob_above_tercsup = ( 1 - stats.norm(fsfcst, sefcst).cdf(obs_tercsup)) * 100  
        prob_central_terc = (100 - prob_below_tercinf - prob_above_tercsup)    

        # prob_below_tercinf = stats.norm(fcst_mean_stand, sefcst_stand).cdf(-0.43) * 100
        # prob_above_tercinf = ( 1 - stats.norm(fcst_mean_stand, sefcst_stand).cdf(-0.43)) * 100  

        # prob_below_tercsup = stats.norm(fcst_mean_stand, sefcst_stand).cdf(0.43) * 100
        # prob_above_tercsup = ( 1 - stats.norm(fcst_mean_stand, sefcst_stand).cdf(0.43)) * 100  
        # prob_central_terc = (100 - prob_below_tercinf - prob_above_tercsup)

        #--- Probabilidade dos tercis mais prováveis
        stacked_probs = np.stack([prob_below_tercinf, prob_central_terc, prob_above_tercsup], axis=0)  # shape (3, 9, 180, 360)
        max_idx = np.argmax(stacked_probs, axis=0) # Índices da maior probabilidade ao longo do eixo 0 (categoria)
        max_val = np.max(stacked_probs, axis=0) # Primeiro obtemos o valor máximo em cada ponto
        prob_tercile = np.zeros_like(max_val)
        prob_tercile[max_idx == 0] = -max_val[max_idx == 0]  # below → negativo
        prob_tercile[max_idx == 2] =  max_val[max_idx == 2]  # above → positivo

        if var == "prec":
            #--- Probabilidade de precipitação de pelo menos 10mm, 20mm, 40mm, 60mm, 80mm...
            thresholds_mm = np.array([10, 20, 40, 60, 80, 100, 150, 200, 250, 300, 400, 500, 600])
            prob_exc_mm = (1.0 - norm.cdf(thresholds_mm[:, None, None, None],  
                loc=fsfcst[None, :, :, :], scale=sefcst[None, :, :, :])) * 100

            #--- Dado um conjunto de probabilidades p (por ex 20%, 50%, 80%), achar o mm correspondente
            probabilities = np.array([0.2, 0.5, 0.8])  
            prec_percent = (norm.ppf(probabilities[:, None, None, None],
                loc=fsfcst[None, :, :, :], scale=sefcst[None, :, :, :]))

            return (anomaly_multimodel, fcst_mm, fsfcst, sefcst, prob_above_calib, prob_tercile, 
                    prob_exc_mm, prec_percent, obs_mean, obs_std, obs_total, obs_tercinf, 
                    obs_tercsup, prob_below_tercinf, prob_above_tercinf, prob_below_tercsup, 
                    prob_above_tercsup, prob_central_terc, model_cor)

            # return (fcst_mm, fsfcst, sefcst, obs_mean, obs_std, obs_tercinf, 
            #         obs_tercsup, prob_below_tercinf, prob_above_tercinf, prob_below_tercsup, 
            #         prob_above_tercsup, prob_central_terc, model_cor)

        elif var == "t2mt":
            return (anomaly_multimodel, fcst_mm, fsfcst, sefcst, prob_above_calib, prob_tercile, 
                    obs_mean, obs_std, obs_total, obs_tercinf, obs_tercsup, prob_below_tercinf, 
                    prob_above_tercinf, prob_below_tercsup, prob_above_tercsup, prob_central_terc, model_cor)


    @staticmethod
    def calibration_cox_model(path_fcst, path_hcst, path_obs, base, year_fcst, month_fcst, model, var, block_size=12):
        # --- Observação e hindcast
        obs = Observation(path_obs)
        stats = obs.mean_std_anom_obs_gamma(base, month_fcst, var)
        ordered_periods = list(stats.keys())
        
        obs_series = np.stack([obs.calculate_obs_periods(base, month_fcst, var)[p] for p in ordered_periods], axis=1)
        obs_anomaly = np.stack([stats[p]['anomaly'] for p in ordered_periods], axis=1)
        obs_mediana = np.stack([stats[p]['mediana'] for p in ordered_periods], axis=0)
        obs_tercinf = np.stack([stats[p]['tercilinf'] for p in ordered_periods], axis=0)
        obs_tercsup = np.stack([stats[p]['tercilsup'] for p in ordered_periods], axis=0)
        obs_iqr = np.stack([stats[p]['intqobs'] for p in ordered_periods], axis=0)

        hindcast = Hindcast(path_fcst, path_hcst)
        hcst_total, hcst_mean, hcst_std, hcst_anomaly = hindcast.mean_std_anom_hindcast(base, year_fcst, month_fcst, model, var)

        if hcst_total is None:
            raise ValueError("Sem modelos suficientes para gerar o Multimodelo\n")

        # --- Previsão tempo-real (Forecast)
        #models_available = Calibration.check_models(base, path_fcst, year_fcst, month_fcst, var)
        if model == "multimodel":
            forecast = Forecast(path_fcst)
            realtime_fcst = forecast.forecast_multimodel(base, year_fcst, month_fcst, var)
        else:
            forecast = Forecast(path_fcst)
            model_fcst = forecast.read_fcst_file(base, year_fcst, month_fcst, model, var)
            fcst_dict = forecast.calculate_fcst_periods(base, year_fcst, month_fcst, model, model_fcst, var)
            realtime_fcst = forecast.dict_to_array(base, fcst_dict, ["mnth00","mnth01","mnth02","mnth03","mnth04","seas00","seas01","seas02"], var)

        anomfcst = realtime_fcst - hcst_mean  # Assumindo que realtime_fcst já calculado

        if base == "nmme":
            time = 30 #1991-2020
        elif base == "copernicus":
            time = 24 #1993-2016 

        # --- Inicializa arrays de saída
        shape = obs_series.shape[1:]  # (period, lat, lon)
        anomalia_fcst_cox = np.full(shape, np.nan)
        mediana_fcst_cox = np.full(shape, np.nan)
        probexc_mediana = np.full(shape, np.nan)
        probexc_tercinf = np.full(shape, np.nan)
        probexc_tercsup = np.full(shape, np.nan)
        probyobs_cox = np.full((8, time, 72, 144), np.nan)
        probyfcst_cox = np.full((8, time, 72, 144), np.nan)
        varx_cox = np.full((8, time, 72, 144), np.nan)
        coef_beta = np.full(shape, np.nan)
        inter_quartil = np.full(shape, np.nan)

        if var == "prec":
            prob_exc_mm = np.full((13, anomfcst.shape[0], 72, 144), np.nan)
            prec_percent = np.full((3, anomfcst.shape[0], 72, 144), np.nan)

        # --- Função para processar blocos
        def process_block(lat_start, lat_end, lon_start, lon_end, period):
            results_block = []

            MAX_EVENTS = obs_series.shape[0]

            def pad_to_max(arr, max_len):
                out = np.full(max_len, np.nan)
                n = min(len(arr), max_len)
                out[:n] = arr[:n]
                return out
            
            for clat in range(lat_start, lat_end):
                for clon in range(lon_start, lon_end):
                    obs_pt = obs_series[:, period, clat, clon]

                    anomhcst = hcst_anomaly[:, period, clat, clon]
                    present = np.ones_like(obs_pt)

                    if base == "nmme":
                        years_hcst = range(1991, 2021)
                    else:
                        years_hcst = range(1993, 2017)
                    
                    df = pd.DataFrame({"obs": obs_pt, "anomhcst": anomhcst, "present": present})
                    
                    try:
                        cox_model = CoxPHFitter()
                        cox_model.fit(df, duration_col="obs", event_col="present")
                        coef = cox_model.params_["anomhcst"]
                        basePEX = cox_model.baseline_survival_
                        varx_clim = basePEX.index.values
                        proby_clim = basePEX.values.flatten()             
                    except:
                        coef = 0.0
                        basePEX = pd.Series(np.linspace(1, 0, len(df)), index=np.sort(df["obs"]))
                        varx_clim = basePEX.index.values
                        proby_clim = basePEX.values.flatten()
                    
                    exp_term = np.exp(coef * anomfcst[period, clat, clon])
                    proby_fcstcox = proby_clim ** exp_term

                    varx_pad = pad_to_max(varx_clim, MAX_EVENTS)
                    proby_clim_pad = pad_to_max(proby_clim, MAX_EVENTS)
                    proby_fcst_pad = pad_to_max(proby_fcstcox, MAX_EVENTS)  

                    #CÁLCULO MEDIANA PREVISTA (DADA A PROBABILIDADE ENCONTRA NA CURVA PREVISTA O VALOR DA MEDIANA)
                    mediana_prevcox = Calibration.interpolation_cox(varx_clim, proby_fcstcox, 0.5, inverter=False)
                    quartil_1 = Calibration.interpolation_cox(varx_clim, proby_fcstcox, 0.75, inverter=False)
                    quartil_3 = Calibration.interpolation_cox(varx_clim, proby_fcstcox, 0.25, inverter=False) 
                    iqr = quartil_3 - quartil_1
                                   
                    #CÁLCULO DA PROBABILIDADE ANOMALIA POSITIVA (ACIMA DA MEDIANA)
                    prob_mediana = Calibration.probabilidade_cox(varx_clim, proby_fcstcox, obs_mediana[period, clat, clon], alongar=True, inverter=False)
                    
                    #CÁLCULO DA PROBABILIDADE PREVISTA ABAIXO TERCIL INFERIOR OBSERVADO E ACIMA TERCIL SUPERIOR OBSERVADO
                    prob_tinf = Calibration.probabilidade_cox(varx_clim, proby_fcstcox, obs_tercinf[period, clat, clon], alongar=True, inverter=False)
                    prob_tsup = Calibration.probabilidade_cox(varx_clim, proby_fcstcox, obs_tercsup[period, clat, clon], alongar=True, inverter=False)
               
                    results_block.append((clat, clon, mediana_prevcox, mediana_prevcox - obs_mediana[period, clat, clon], 
                    prob_tinf, prob_tsup, prob_mediana, proby_clim_pad, proby_fcst_pad, varx_pad, coef, iqr))

                    if var == "prec":
                        thresholds_mm = [10,20,40,60,80,100,150,200,250,300,400,500,600]
                        prob_exc_mm = [Calibration.probabilidade_cox(varx_clim, proby_fcstcox, t, alongar=True, inverter=False) for t in thresholds_mm]

                        probabilities = np.array([0.2, 0.5, 0.8])         
                        prec_percent = [Calibration.interpolation_cox(varx_clim, proby_fcstcox, p, inverter=True) for p in probabilities]

                        results_block[-1] += (prob_exc_mm, prec_percent)

            return results_block


        # --- Paralelização por blocos
        for period in range(anomfcst.shape[0]):
            lat_blocks = [(i, min(i+block_size, 72)) for i in range(0, 72, block_size)]
            lon_blocks = [(j, min(j+block_size, 144)) for j in range(0, 144, block_size)]
            
            results = Parallel(n_jobs=-1)(
                delayed(process_block)(lat_s, lat_e, lon_s, lon_e, period)
                for lat_s, lat_e in lat_blocks
                for lon_s, lon_e in lon_blocks
            )

            # Merge resultados do bloco
            for block in results:
                for res in block:
                    clat, clon, mediana, anom, p_inf, p_sup, p_med, py_clim, py_fcst, varx, beta, interq = res[:12]
                    mediana_fcst_cox[period, clat, clon] = mediana
                    anomalia_fcst_cox[period, clat, clon] = anom
                    probexc_tercinf[period, clat, clon] = p_inf
                    probexc_tercsup[period, clat, clon] = p_sup                    
                    probexc_mediana[period, clat, clon] = p_med
                    coef_beta[period, clat, clon] = p_med
                    probyobs_cox[period, :, clat, clon] = py_clim
                    probyfcst_cox[period, :, clat, clon] = py_fcst 
                    varx_cox[period, :, clat, clon] = varx 
                    inter_quartil[period, clat, clon] = interq 

                    if var == "prec":
                        prob_prec_mm = res[12]  # lista com 13 arrays
                        for i, p in enumerate(prob_prec_mm):
                            prob_exc_mm[i, period, clat, clon] = p

                        prob_prec_percent = res[13]  # lista com 3 arrays
                        for i, p in enumerate(prob_prec_percent):
                            prec_percent[i, period, clat, clon] = p

        #PROBABILITY ABOVE/BELOW TERCILES CALIBRATED
        prob_below_inf = 1 - probexc_tercinf
        prob_above_sup = probexc_tercsup
        prob_below_sup = 1 - probexc_tercsup
        prob_central_terc = 1 - prob_below_inf - prob_above_sup
        probbelow_mediana = 1 - probexc_mediana

        stacked_probs = np.stack([prob_below_inf, prob_central_terc, prob_above_sup], axis=0)

        max_idx = np.argmax(stacked_probs, axis=0)
        max_val = np.max(stacked_probs, axis=0) 

        prob_tercile = np.zeros_like(max_val)
        prob_tercile[max_idx == 0] = -max_val[max_idx == 0]  # below → negativo
        prob_tercile[max_idx == 2] =  max_val[max_idx == 2]  # above → positivo

        if var == "prec":
            return (anomalia_fcst_cox, mediana_fcst_cox, probexc_mediana*100, prob_tercile*100, 
            prob_exc_mm*100, prec_percent, prob_below_inf, probexc_tercinf, prob_below_sup,
            prob_above_sup, probyobs_cox, probyfcst_cox, varx_cox, coef_beta, inter_quartil, 
            obs_mediana, obs_iqr)

        else:
            return (anomalia_fcst_cox, mediana_fcst_cox, probexc_mediana*100, prob_tercile*100, 
            prob_below_inf, probexc_tercinf, prob_below_sup,prob_above_sup, probyobs_cox, probyfcst_cox, 
            varx_cox, coef_beta, inter_quartil, obs_mediana, obs_iqr)

    @staticmethod
    def ks_gamma_bootstrap(sample, B=1000, n_jobs=6):

        # --- Limpeza
        sample = sample[~np.isnan(sample)]
        sample = sample[sample > 0]

        n = len(sample)

        if n < 5:
            return np.nan, np.nan

        mean = np.mean(sample)
        var = np.var(sample, ddof=1)

        if mean <= 0 or var <= 0:
            return np.nan, np.nan

        alpha_hat = mean**2 / var
        theta_hat = var / mean

        if alpha_hat <= 0 or theta_hat <= 0:
            return np.nan, np.nan

        # --- KS real
        try:
            D_real, _ = kstest(sample, 'gamma', args=(alpha_hat, 0, theta_hat))
        except:
            return np.nan, np.nan

        # --- Função interna do bootstrap
        def bootstrap_iteration(_):

            sim = gamma.rvs(a=alpha_hat, loc=0, scale=theta_hat, size=n)

            mean_b = np.mean(sim)
            var_b = np.var(sim, ddof=1)

            if mean_b <= 0 or var_b <= 0:
                return 0.0

            alpha_b = mean_b**2 / var_b
            theta_b = var_b / mean_b

            if alpha_b <= 0 or theta_b <= 0:
                return 0.0

            D_b, _ = kstest(sim, 'gamma', args=(alpha_b, 0, theta_b))
            return D_b

        # --- Paralelização
        D_boot = Parallel(n_jobs=n_jobs)(
            delayed(bootstrap_iteration)(b) for b in range(B)
        )

        D_boot = np.array(D_boot)

        # --- p-valor bootstrap
        p_boot = (np.sum(D_boot >= D_real) + 1) / (B + 1)

        return D_real, p_boot

    @staticmethod  
    def gamma_calibration_model(path_fcst, path_hcst, path_obs, base, year_fcst, month_fcst, model, var):
        ''' Calibração das previsões em tempo-real através do método Gamma '''

        print("gamma regression: ", month_fcst)
        print("model: ", model, "var: ", var)

        # --- Observação
        obs = Observation(path_obs)
        statistcs = obs.mean_std_anom_obs_gamma(base, month_fcst, var) 
        anom = {k: v['anomaly'] for k, v in statistcs.items() if 'anomaly' in v}
        std = {k: v['std'] for k, v in statistcs.items() if 'std' in v}
        vari = {k: v['variance'] for k, v in statistcs.items() if 'std' in v}
        mean = {k: v['mean'] for k, v in statistcs.items() if 'mean' in v} 
        mediana =  {k: v['mediana'] for k, v in statistcs.items() if 'mediana' in v}   
        tercil_inf = {k: v['tercilinf'] for k, v in statistcs.items() if 'tercilinf' in v}    
        tercil_sup = {k: v['tercilsup'] for k, v in statistcs.items() if 'tercilsup' in v}   
        total = {k: v['total'] for k, v in statistcs.items() if 'total' in v}   

        #transformar em array
        ordered_periods = list(anom.keys()) 
        obs_series = np.stack([obs.calculate_obs_periods(base, month_fcst, var)[p] for p in ordered_periods], axis=0)
        obs_total = np.stack([total[p] for p in ordered_periods], axis=1)
        obs_anomaly = np.stack([anom[p] for p in ordered_periods], axis=1)
        obs_std = np.stack([std[p] for p in ordered_periods], axis=0)
        obs_mean = np.stack([mean[p] for p in ordered_periods], axis=0)
        obs_var =  np.stack([vari[p] for p in ordered_periods], axis=0)
        obs_mediana = np.stack([mediana[p] for p in ordered_periods], axis=0)        
        obs_tercinf = np.stack([tercil_inf[p] for p in ordered_periods], axis=0)
        obs_tercsup = np.stack([tercil_sup[p] for p in ordered_periods], axis=0)             

        # --- Hindcast 
        hindcast = Hindcast(path_fcst, path_hcst)
        hcst_total, hcst_mean, hcst_std, hcst_var, hcst_anomaly = hindcast.mean_std_anom_hindcast_gamma(base, year_fcst, month_fcst, model, var)     

        # --- Previsão tempo-real (Forecast)
        #models_available = Calibration.check_models(base, path_fcst, year_fcst, month_fcst, var)
        if model == "multimodel":
            forecast = Forecast(path_fcst)
            realtime_fcst = forecast.forecast_multimodel(base, year_fcst, month_fcst, var)
        else:
            forecast = Forecast(path_fcst)
            model_fcst = forecast.read_fcst_file(base, year_fcst, month_fcst, model, var)
            fcst_dict = forecast.calculate_fcst_periods(base, year_fcst, month_fcst, model, model_fcst, var)
            realtime_fcst = forecast.dict_to_array(base, fcst_dict, ["mnth00","mnth01","mnth02","mnth03","mnth04","seas00","seas01","seas02"], var)

        # --- Correlação
        model_cor = Calibration.correlation_model(obs_anomaly, hcst_anomaly, year_fcst, month_fcst, model, var)

        # --- Parâmetros Gamma 
        alpha_obs = (obs_mean ** 2) / obs_var #obs
        alpha_hcst = (hcst_mean ** 2) / hcst_var #hcst
        beta_obs  = obs_var / obs_mean #obs
        beta_hcst = hcst_var / hcst_mean #hcst

        # --- Calcular o p-value do teste Kolmogorov-Smirnov (KS)
        ntime, nmonth, nlat, nlon = obs_total.shape

        #p_obs = np.full((nmonth, nlat, nlon), np.nan)
        p_hcst = np.full((nmonth, nlat, nlon), np.nan)

        print("obs serie:",obs_total[:, 6,30, 55])
        print("hcst serie:", hcst_total[:, 6,30, 55])
        print("shape obs:", alpha_obs[6,30, 55])
        print("scale obs:",beta_obs[6,30, 55])
        print("shape hcst:", alpha_hcst[6,30, 55])
        print("scale hcst:", beta_hcst[6,30, 55])


        def processar_gridpoint(m, i, j,
                                obs_total,
                                hcst_total):

            resultado_obs = np.nan
            resultado_hcst = np.nan

            serie_obs = obs_total[:, m, i, j]
            serie_hcst = hcst_total[:, m, i, j]

            # OBS
            if np.sum(~np.isnan(serie_obs)) > 10:

                _, p = Calibration.ks_gamma_bootstrap(
                    serie_obs,
                    B=1000
                )

                resultado_obs = p

            # HCST
            if np.sum(~np.isnan(serie_hcst)) > 10:

                _, p = Calibration.ks_gamma_bootstrap(
                    serie_hcst,
                    B=1000
                )

                resultado_hcst = p

            return m, i, j, resultado_obs, resultado_hcst

        tarefas = [
            (m, i, j)
            for m in range(nmonth)
            for i in range(nlat)
            for j in range(nlon)
        ]

        resultados =  Parallel(
            n_jobs = -1,
            verbose = 10
        )(
            delayed(processar_gridpoint)(
                m,i,j,
                obs_total,
                hcst_total
            )
            for m, i, j in tarefas
        )

        for m, i, j, p_obs_val, p_hcst_val in resultados:

            #p_obs[m, i, j] = p_obs_val
            p_hcst[m, i, j] = p_hcst_val

        for m in range(nmonth):
            for i in range(nlat):
                for j in range(nlon):

                    # serie_obs = obs_total[:, m, i, j]
                    serie_hcst = hcst_total[:, m, i, j]

                    # if np.sum(~np.isnan(serie_obs)) > 10:

                    #     # D, p = kstest(
                    #     #     serie_obs,
                    #     #     'gamma',
                    #     #     args=(alpha_obs[m,i,j], 0, beta_obs[m,i,j])
                    #     # )

                    #     D, p = Calibration.ks_gamma_bootstrap(serie_obs, B=1000)                   

                    #     p_obs[m,i,j] = p

                    if np.sum(~np.isnan(serie_hcst)) > 10:

                        # D, p = kstest(
                        #     serie_hcst,
                        #     'gamma',
                        #     args=(alpha_hcst[m,i,j], 0, beta_hcst[m,i,j])
                        # )

                        D, p = Calibration.ks_gamma_bootstrap(serie_hcst, B=1000)

                        p_hcst[m,i,j] = p

        # --- Padronização Gamma para Normal
        eps = 1e-6
        ntime, nper, nlat, nlon = hcst_total.shape

        media2_all = np.full((ntime, nper, nlat, nlon), np.nan)
        alpha2_all = np.full((ntime, nper, nlat, nlon), np.nan)
        beta2_all  = np.full((ntime, nper, nlat, nlon), np.nan)
        prob_below_all = np.full((ntime, nper, nlat, nlon), np.nan)
        prob_above_all = np.full((ntime, nper, nlat, nlon), np.nan)

        serie_hcst = hcst_total
        serie_obs  = obs_total

        # ====================================================
        # 1. Gamma -> Normal (padronização das séries - HCST)
        # ====================================================
        gamma_hcst = gamma.cdf(
            serie_hcst,
            a=alpha_hcst,
            scale=beta_hcst
        )

        gamma_hcst = np.clip(gamma_hcst, eps, 1 - eps) #coloca valores no inicio e no fim da série para evitar 0 e 1
        spi_h = norm.ppf(gamma_hcst) #Transforma probabilidade -> Normal(0,1)

        # ===================================================
        # 1. Gamma -> Normal (padronização das séries - OBS)
        # ===================================================
        gamma_obs = gamma.cdf(
            serie_obs,
            a=alpha_obs,
            scale=beta_obs
        )

        gamma_obs = np.clip(gamma_obs, eps, 1 - eps)
        spi_o = norm.ppf(gamma_obs)

        # =============================================
        # 2. Correlação entre os valores padronizados
        # =============================================       
        mean_h = spi_h.mean(axis=0)
        mean_o = spi_o.mean(axis=0)

        std_h = spi_h.std(axis=0, ddof=1)
        std_o = spi_o.std(axis=0, ddof=1)

        cov = ((spi_h - mean_h) * (spi_o - mean_o)).mean(axis=0)

        corr = cov / (std_h * std_o)
        corr = np.where(corr < 0, 0, corr) # zerar correlação negativa

        # ----------------------------------------------------------
        # Usar as novas séries de dados transformados 
        # p/ estimar alpha e beta (Regressão no espaço padronizado)
        # ----------------------------------------------------------

        n = spi_o.shape[0]  # ntime - 1

        var_o = spi_o.var(axis=0, ddof=1)
        var_h = spi_h.var(axis=0, ddof=1)

        factor = (n - 2) / (n - 1)

        se = np.sqrt(var_o * factor) * np.sqrt(1 - corr**2)

        beta_reg = corr * np.sqrt(var_o / var_h)

        alpha_reg = mean_o - beta_reg * mean_h

        # ----------------------------------------
        # Selecionar valor da previsão (hindcast)
        # do ano k e padronizar essa previsão
        # ----------------------------------------
        x_prev = realtime_fcst   # (nper, nlat, nlon)

        xp = gamma.cdf(
            x_prev,
            a=alpha_hcst,
            scale=beta_hcst
        )

        xp = np.clip(xp, eps, 1 - eps)

        xlinhaprevisao = norm.ppf(xp) #Padronização

        ylinhamedio = alpha_reg + beta_reg * xlinhaprevisao #Regressão no espaço padronizado (Y')

        # ----------------------------------------
        # Voltar para unidades físicas (mm)
        # calculo do alpha e beta para gerar
        # a distribuição Gamma prevista
        # ---------------------------------------- 
        
        anomalia2 = ylinhamedio * obs_std
        media2 = ylinhamedio * obs_std + obs_mean #Cálculo da Média prevista em milimetros
        desvio2 = obs_std * np.sqrt(1 - corr**2)
        media2[~np.isfinite(media2)] = np.nan     

        alpha2 = (media2**2) / (desvio2**2) #Estimativa dos valores de alpha da gamma prevista
        beta2  = (desvio2**2) / media2 #Estimativa dos valores de beta da gamma prevista       

        #Calibrated Probability Above/Below Obs. Terciles  
        prob_below_inf = gamma.cdf(obs_tercinf, a=alpha2, scale=beta2) 
        prob_above_inf = 1 - gamma.cdf(obs_tercinf, a=alpha2, scale=beta2) 

        prob_below_sup = gamma.cdf(obs_tercsup, a=alpha2,scale=beta2)          
        prob_above_sup = 1 - gamma.cdf(obs_tercsup, a=alpha2,scale=beta2)

        prob_central_terc = (1 - prob_below_inf - prob_above_sup)

        stacked_probs = np.stack([prob_below_inf, prob_central_terc, prob_above_sup], axis=0)

        max_idx = np.argmax(stacked_probs, axis=0)
        max_val = np.max(stacked_probs, axis=0) 

        prob_tercile = np.zeros_like(max_val)
        prob_tercile[max_idx == 0] = -max_val[max_idx == 0]  # below → negativo
        prob_tercile[max_idx == 2] =  max_val[max_idx == 2]  # above → positivo


        return (anomalia2, media2, desvio2, alpha2, beta2, prob_below_inf, prob_above_inf, 
                prob_below_sup, prob_above_sup, prob_central_terc, prob_tercile*100, corr, alpha_obs,
                beta_obs, p_hcst)

        #return (anomalia2, media2, alpha2, beta2, prob_tercile*100) 

    # @staticmethod  
    # def obs_artigo(path_fcst, path_hcst, path_obs, base, year_fcst, month_fcst, var):
    #     ''' Calibração das previsões em tempo-real através do método Gamma '''

    #     print("gamma regression: ", month_fcst)
    #     print("model: ", model, "var: ", var)

    #     # --- Observação
    #     obs = Observation(path_obs)
    #     statistcs = obs.mean_std_anom_obs_gamma(base, month_fcst, var) 
    #     anom = {k: v['anomaly'] for k, v in statistcs.items() if 'anomaly' in v}
    #     std = {k: v['std'] for k, v in statistcs.items() if 'std' in v}
    #     vari = {k: v['variance'] for k, v in statistcs.items() if 'std' in v}
    #     mean = {k: v['mean'] for k, v in statistcs.items() if 'mean' in v} 
    #     mediana =  {k: v['mediana'] for k, v in statistcs.items() if 'mediana' in v}   
    #     tercil_inf = {k: v['tercilinf'] for k, v in statistcs.items() if 'tercilinf' in v}    
    #     tercil_sup = {k: v['tercilsup'] for k, v in statistcs.items() if 'tercilsup' in v}   
    #     total = {k: v['total'] for k, v in statistcs.items() if 'total' in v}   

    #     #transformar em array
    #     ordered_periods = list(anom.keys()) 
    #     obs_series = np.stack([obs.calculate_obs_periods(base, month_fcst, var)[p] for p in ordered_periods], axis=0)
    #     obs_total = np.stack([total[p] for p in ordered_periods], axis=1)
    #     obs_anomaly = np.stack([anom[p] for p in ordered_periods], axis=1)
    #     obs_std = np.stack([std[p] for p in ordered_periods], axis=0)
    #     obs_mean = np.stack([mean[p] for p in ordered_periods], axis=0)
    #     obs_var =  np.stack([vari[p] for p in ordered_periods], axis=0)
    #     obs_mediana = np.stack([mediana[p] for p in ordered_periods], axis=0)        
    #     obs_tercinf = np.stack([tercil_inf[p] for p in ordered_periods], axis=0)
    #     obs_tercsup = np.stack([tercil_sup[p] for p in ordered_periods], axis=0)   

    #     if month_fcst == 11:

    #         files = [
    #             "GPCP-DEC2024.nc",
    #             "GPCP-JAN2025.nc",
    #             "GPCP-FEB2025.nc"
    #         ]

    #         ndays_list = [
    #             calendar.monthrange(2024, 12)[1],
    #             calendar.monthrange(2025, 1)[1],
    #             calendar.monthrange(2025, 2)[1]
    #         ]

    #     elif month_fcst == 2:

    #         # files = [
    #         #     "GPCP-MAR2025.nc",
    #         #     "GPCP-APR2025.nc",
    #         #     "GPCP-MAY2025.nc"
    #         # ]

    #         # ndays_list = [
    #         #     calendar.monthrange(2025, 3)[1],
    #         #     calendar.monthrange(2025, 4)[1],
    #         #     calendar.monthrange(2025, 5)[1]
    #         # ]

    #         files = [
    #             "GPCP-MAR2016.nc",
    #             "GPCP-APR2016.nc",
    #             "GPCP-MAY2016.nc"
    #         ]

    #         ndays_list = [
    #             calendar.monthrange(2016, 3)[1],
    #             calendar.monthrange(2016, 4)[1],
    #             calendar.monthrange(2016, 5)[1]
    #         ]


    #     elif month_fcst == 8:

    #         files = [
    #             "GPCP-SEP2025.nc",
    #             "GPCP-OCT2025.nc",
    #             "GPCP-NOV2025.nc"
    #         ]

    #         ndays_list = [
    #             calendar.monthrange(2025, 9)[1],
    #             calendar.monthrange(2025, 10)[1],
    #             calendar.monthrange(2025, 11)[1]
    #         ]

    #     # -------------------------------
    #     # Abre dados mensais
    #     # -------------------------------

    #     datasets = [
    #         xr.open_dataset(
    #             f"/dados/mmclima/multimodelo/artigo/sazonal/obs/{f}"
    #         )["precip"]
    #         for f in files
    #     ]

    #     # -------------------------------
    #     # Converte mm/day → mm/mês
    #     # -------------------------------

    #     datasets_corr = []

    #     for da, nd in zip(datasets, ndays_list):
    #         datasets_corr.append(da * nd)

    #     # -------------------------------
    #     # Soma trimestral (mm/trimestre)
    #     # -------------------------------
    #     obs_trimestral = xr.concat(datasets_corr, dim="time").sum("time")
    #     obs_tri_np = obs_trimestral.values  

    #     print(obs_trimestral.shape)

    #     # ----------------------------------------------------------
    #     # ANOMALIA SAZONAL (observado - climatologia)
    #     # ----------------------------------------------------------
    #     obs_anom_tri = obs_tri_np - obs_mean[6, :, :]

    #     # ----------------------------------------------------------
    #     # CLASSIFICAÇÃO POR TERCIS
    #     # -1 = abaixo do normal (seco)
    #     #  0 = normal
    #     # +1 = acima do normal (úmido)
    #     # ----------------------------------------------------------

    #     terc_class = np.zeros_like(obs_tri_np)

    #     terc_class[obs_tri_np < obs_tercinf[6, :, :]] = -1
    #     terc_class[obs_tri_np > obs_tercsup[6, :, :]] = +1

    #     # ----------------------------------------------------------
    #     # CONVERTE DE VOLTA PRA XARRAY (mantém lat/lon)
    #     # ----------------------------------------------------------

    #     anom_xr = xr.DataArray(
    #         obs_anom_tri,
    #         coords=obs_trimestral.coords,
    #         dims=obs_trimestral.dims,
    #         name="precip_anomaly"
    #     )

    #     terc_xr = xr.DataArray(
    #         terc_class,
    #         coords=obs_trimestral.coords,
    #         dims=obs_trimestral.dims,
    #         name="tercile_class"
    #     )

    #     # ----------------------------------------------------------
    #     # CAMINHO DE SAÍDA
    #     # ----------------------------------------------------------

    #     out_dir = "/dados/mmclima/multimodelo/artigo/dados"

    #     fname_anom = (
    #         f"{out_dir}/GPCP_trimestral_anom_"
    #         f"{year_fcst}{month_fcst:02d}.nc"
    #     )

    #     fname_terc = (
    #         f"{out_dir}/GPCP_trimestral_tercile_"
    #         f"{year_fcst}{month_fcst:02d}.nc"
    #     )

    #     # ----------------------------------------------------------
    #     # ATRIBUTOS (boa prática CF)
    #     # ----------------------------------------------------------

    #     anom_xr.attrs = {
    #         "long_name": "Precipitation anomaly (seasonal accumulated)",
    #         "units": "mm",
    #         "description": "Observed seasonal precipitation anomaly relative to climatology",
    #         "source": "GPCP",
    #         "created_by": "Calibration pipeline"
    #     }

    #     terc_xr.attrs = {
    #         "long_name": "Precipitation tercile class",
    #         "description": (
    #             "-1 = below normal (lower tercile), "
    #             "0 = near normal (middle tercile), "
    #             "1 = above normal (upper tercile)"
    #         ),
    #         "source": "GPCP",
    #         "created_by": "Calibration pipeline"
    #     }

    #     # ----------------------------------------------------------
    #     # ENCODING (arquivo leve e rápido)
    #     # ----------------------------------------------------------

    #     encoding_anom = {
    #         "precip_anomaly": {
    #             "zlib": True,
    #             "complevel": 4,
    #             "dtype": "float32"
    #         }
    #     }

    #     encoding_terc = {
    #         "tercile_class": {
    #             "zlib": True,
    #             "complevel": 4,
    #             "dtype": "int8"
    #         }
    #     }

    #     # ----------------------------------------------------------
    #     # SALVAR NETCDF
    #     # ----------------------------------------------------------

    #     anom_xr.to_netcdf(
    #         fname_anom,
    #         format="NETCDF4",
    #         encoding=encoding_anom
    #     )

    #     terc_xr.to_netcdf(
    #         fname_terc,
    #         format="NETCDF4",
    #         encoding=encoding_terc
    #     )

    #     print("Arquivos salvos:")
    #     print(fname_anom)
    #     print(fname_terc)

    @staticmethod
    def run(type, *args, **kwargs):
        if type == "regression":
            return Calibration.regression_calibration_model(*args, **kwargs)
        elif type == "cox":
            return Calibration.calibration_cox_model(*args, **kwargs)
        else:
            raise ValueError(f"Tipo de calibração '{type}' não reconhecido.")

    @staticmethod
    def compute_period_names(year_fcst, month_fcst):
        periods = {
            "mnth00": (0,),
            "mnth01": (1,),
            "mnth02": (2,),
            "mnth03": (3,),
            "mnth04": (4,),
            "seas00": (0, 1, 2),
            "seas01": (1, 2, 3),
            "seas02": (2, 3, 4)
        }

        result = {}

        for period, offsets in periods.items():
            months = []
            for offset in offsets:
                month = month_fcst + offset
                year = year_fcst
                # Ajuste de ano se o mês passar de 12
                if month > 12:
                    month -= 12
                    year += 1
                months.append((month, year))

            if period.startswith("mnth"):
                # Apenas um mês
                m, y = months[0]
                month_abbr = calendar.month_abbr[m]
                result[period] = f"{month_abbr} {y}"
            elif period.startswith("seas"):
                # Três meses
                season_str = ''.join(calendar.month_abbr[m][0].upper() for m, _ in months)
                result[period] = f"{season_str} {months[0][1]}"

        return result


    @staticmethod                      
    def write_netcdf_model_regression(base, year_fcst, month_fcst, model, variable, anom_calib, 
    acum_calib, std_calib, prob_mean, prob_tercile, obs_mean, obs_std, obs_total, obs_tercinf, 
    obs_tercsup, prob_below_tercinf, prob_above_tercinf, prob_below_tercsup, prob_above_tercsup, 
    prob_central_terc, model_cor, prob_precip=None, prec_percent=None):

        """Escreve arquivos NetCDF para previsão calibrada pelo método da regressão, compatíveis com o GrADS."""
        period_dates = Calibration.compute_period_names(year_fcst, month_fcst) 
        month = f"{month_fcst:02d}"
        fcst_date = f"{year_fcst}{month}0100"

        # Ajusta latitudes e longitudes
        obs = xr.open_dataset("/dados/mmclima/multimodelo/seasonal/obs/gpcp/obs_gpcp_pr_mon_mean_1979-2025.nc")
        lat_obs = obs["lat"].values
        lon_obs = obs["lon"].values

        if base == "nmme":
            time = range(30) #1991-2020
        elif base == "copernicus":
            time = range(24) #1993-2016 

        if variable == "prec":
            varis = ["anom", "prob", "acum", "terc", "stdfcst","prob10mm", "prob20mm", "prob40mm", "prob60mm", 
            "prob80mm", "prob100mm", "prob150mm", "prob200mm", "prob250mm", "prob300mm", "prob400mm", 
            "prob500mm", "prob600mm", "percent20", "percent50", "percent80", "obsmean", "obsstd",
            "obstotal", "obstercinf", "obstercsup", "ptercinfbelow", "ptercinfabove", 
            "ptercsupbelow", "ptercsupabove", "pcentral", "corr"]

        elif variable == "t2mt":
            varis = ["anom", "prob", "acum", "terc", "stdfcst", "obsmean", "obsstd",
            "obstotal", "obstercinf", "obstercsup", "ptercinfbelow", "ptercinfabove", 
            "ptercsupbelow", "ptercsupabove", "pcentral", "corr"]

        version_multimodel = ConfigModelos.get_multimodel_version(base)

        #Define o nome do diretório dos modelos
        if base == "nmme":
            name_model_dir = model
        elif base == "copernicus":
            if model == "multimodel":
                name_model_dir = "multimodel"
            else:
                name_model_dir = ConfigModelos.get_model_dir_c3s(model)   

        nc_path =  (f"/dados/mmclima/multimodelo/seasonal/posproc/{base}/"
            f"{version_multimodel}/forecast/regr/{name_model_dir}/{year_fcst}/{year_fcst}{month}0100/")  

        if not os.path.exists(nc_path):
            os.makedirs(nc_path)
        
        periods = {
            0: 'mnth00', 1: 'mnth01', 2: 'mnth02', 3: 'mnth03', 4: 'mnth04', 
            5: 'seas00', 6: 'seas01', 7: 'seas02'
        }
        
        for period in range(acum_calib.shape[0]):
            name_period = periods.get(period, f"period{period}")
            forecast_date = period_dates[name_period]
            print("Issued:", period_dates['mnth00'], "For:", forecast_date)
            
            for var_name in varis:
                file_path = f"{nc_path}fcst_{variable}_{var_name}_{name_period}_{name_model_dir}_calibrated_regr_{fcst_date}.nc"
                print("Arquivo gerado:", file_path)

                with nc.Dataset(file_path, format='NETCDF3_CLASSIC', mode='w') as ds:
                    # Criação das dimensões
                    ds.createDimension('lat', 72)
                    ds.createDimension('lon', 144)

                    is_3d = (var_name == "obstotal")                    
                    if is_3d:
                        ds.createDimension('time', len(time))

                    # Variáveis de coordenadas
                    lat_var = ds.createVariable('lat', 'f8', ('lat',))
                    lon_var = ds.createVariable('lon', 'f8', ('lon',))
                    lat_var[:] = lat_obs
                    lon_var[:] = lon_obs
                    lat_var.units = "degrees_north"
                    lon_var.units = "degrees_east"

                    if is_3d:
                        time_var = ds.createVariable('time', 'f8', ('time',))
                        time_var[:] = time
                        time_var.units = "years"
                        
                    # Variável de dados
                    dims = ('lat', 'lon') if not is_3d else ('time', 'lat', 'lon')
                    var = ds.createVariable(var_name, 'f8', dims, fill_value=-999.99)
                    var.long_name = f"{var_name} forecast"

                    if variable == "prec":
                        var.units = "mm" if var_name != "prob" else "%",
                        
                        prob_10mm, prob_20mm, prob_40mm, prob_60mm, prob_80mm, prob_100mm, \
                            prob_150mm, prob_200mm, prob_250mm, prob_300mm, prob_400mm, prob_500mm, prob_600mm = prob_precip
                        
                        percent_20, percent_50, percent_80 = prec_percent
                        
                        data_dict = {
                        "acum": acum_calib[period, ...],
                        "stdfcst": std_calib[period, ...],
                        "anom": anom_calib[period, ...],
                        "prob": prob_mean[period, ...],
                        "terc": prob_tercile[period, ...],
                        "prob10mm": prob_10mm[period, ...],
                        "prob20mm": prob_20mm[period, ...],
                        "prob40mm": prob_40mm[period, ...],
                        "prob60mm": prob_60mm[period, ...],
                        "prob80mm": prob_80mm[period, ...],
                        "prob100mm": prob_100mm[period, ...],
                        "prob150mm": prob_150mm[period, ...],
                        "prob200mm": prob_200mm[period, ...],
                        "prob250mm": prob_250mm[period, ...],
                        "prob300mm": prob_300mm[period, ...],
                        "prob400mm": prob_400mm[period, ...],
                        "prob500mm": prob_500mm[period, ...],
                        "prob600mm": prob_600mm[period, ...],  
                        "percent20": percent_20[period, ...],  
                        "percent50": percent_50[period, ...],  
                        "percent80": percent_80[period, ...],
                        "obsmean": obs_mean[period, ...],
                        "obsstd": obs_std[period, ...],
                        "obstotal": obs_total[period, ...],
                        "obstercinf": obs_tercinf[period, ...],
                        "obstercsup": obs_tercsup[period, ...],
                        "ptercinfbelow": prob_below_tercinf[period, ...],  
                        "ptercinfabove": prob_above_tercinf[period, ...],  
                        "ptercsupbelow": prob_below_tercsup[period, ...],  
                        "ptercsupabove": prob_above_tercsup[period, ...],
                        "pcentral": prob_central_terc[period, ...],
                        "corr": model_cor[period, ...],                                         
                    }

                    elif variable == "t2mt":
                        var.units = "°C" if var_name != "prob" else "%"     

                        data_dict = {
                            "acum": acum_calib[period, ...],
                            "stdfcst": std_calib[period, ...],                            
                            "anom": anom_calib[period, ...],
                            "prob": prob_mean[period, ...],
                            "terc": prob_tercile[period, ...],
                            "obsmean": obs_mean[period, ...],
                            "obsstd": obs_std[period, ...],
                            "obstotal": obs_total[period, ...],
                            "obstercinf": obs_tercinf[period, ...],
                            "obstercsup": obs_tercsup[period, ...],
                            "ptercinfbelow": prob_below_tercinf[period, ...],  
                            "ptercinfabove": prob_above_tercinf[period, ...],  
                            "ptercsupbelow": prob_below_tercsup[period, ...],  
                            "ptercsupabove": prob_above_tercsup[period, ...],
                            "pcentral": prob_central_terc[period, ...],
                            "corr": model_cor[period, ...],                               
                        }                        

                    # Atribui os dados
                    data_to_write = data_dict.get(var_name)
                    var[...] = data_to_write   

                    # Atributos globais
                    ds.description = f"Forecast {var_name} calibrated by regression - period {name_period}"
                    ds.history = f"Issued: {period_dates['mnth00'].upper()} For: {forecast_date.upper()}"
                    ds.source = f"{name_model_dir} calibrated forecast - Regression"

    @staticmethod
    def write_netcdf_model_nocalibrated(base, year_fcst, month_fcst, model, variable, anom_nocalib):        
        """Escreve arquivos NetCDF para previsão não calibrada, compatíveis com o GrADS."""
        period_dates = Calibration.compute_period_names(year_fcst, month_fcst) 
        month = f"{month_fcst:02d}"
        fcst_date = f"{year_fcst}{month}0100"
        # Ajusta latitudes e longitudes
        obs = xr.open_dataset("/dados/mmclima/multimodelo/seasonal/obs/gpcp/obs_gpcp_pr_mon_mean_1979-2025.nc")
        lat_obs = obs["lat"].values
        lon_obs = obs["lon"].values

        varis = ["anom"]

        version_multimodel = ConfigModelos.get_multimodel_version(base)

        #Define o nome do diretório dos modelos
        if base == "nmme":
            name_model_dir = model
        elif base == "copernicus":
            if model == "multimodel":
                name_model_dir = "multimodel"
            else:
                name_model_dir = ConfigModelos.get_model_dir_c3s(model)   

        nc_path =  (f"/dados/mmclima/multimodelo/seasonal/posproc/{base}/"
            f"{version_multimodel}/forecast/nocalib/{name_model_dir}/{year_fcst}/{year_fcst}{month}0100/")  

        if not os.path.exists(nc_path):
            os.makedirs(nc_path)
        
        periods = {
            0: 'mnth00', 1: 'mnth01', 2: 'mnth02', 3: 'mnth03', 4: 'mnth04', 
            5: 'seas00', 6: 'seas01', 7: 'seas02'
        }
        
        for period in range(anom_nocalib.shape[0]):
            name_period = periods.get(period, f"period{period}")
            forecast_date = period_dates[name_period]
            print("Issued:", period_dates['mnth00'], "For:", forecast_date)
            
            for var_name in varis:
                file_path = f"{nc_path}fcst_{variable}_{var_name}_{name_period}_{name_model_dir}_nocalib_{fcst_date}.nc"
                print("Arquivo gerado:", file_path)

                with nc.Dataset(file_path, format='NETCDF3_CLASSIC', mode='w') as ds:
                    # Dimensões
                    ds.createDimension('lat', 72)
                    ds.createDimension('lon', 144)
                    
                    # Variáveis de coordenadas
                    lat_var = ds.createVariable('lat', 'f8', ('lat',))
                    lon_var = ds.createVariable('lon', 'f8', ('lon',))
                    lat_var[:] = lat_obs
                    lon_var[:] = lon_obs
                    lat_var.units = "degrees_north"
                    lon_var.units = "degrees_east"

                    # Variável de dados
                    var = ds.createVariable(var_name, 'f8', ('lat', 'lon'), fill_value=-999.99)
                    var.long_name = f"{var_name} forecast"
                    if variable == "prec":
                        var.units = "mm" if var_name != "prob" else "%"
                    elif variable == "t2mt":
                        var.units = "°C" if var_name != "prob" else "%"                    
                    
                    # Atribui os dados
                    if var_name == "anom":
                        var[:, :] = anom_nocalib[period, ...]                 
                        
                    # Atributos globais
                    ds.description = f"Forecast {var_name} no calibrated - period {name_period}"
                    ds.history = f"Issued: {period_dates['mnth00'].upper()} For: {forecast_date.upper()}"


    @staticmethod 
    def write_netcdf_model_cox(base, year_fcst, month_fcst, model, variable, anom_calib, 
        acum_calib, prob_mean, prob_tercile,  prob_below_inf, prob_above_inf, 
        prob_below_sup, prob_above_sup, probyobs_cox, probyfcst_cox, varx_cox, coef_beta,
        cox_iqr, obs_mediana, obs_iqr, prob_precip=None, prec_percent=None):

        """Escreve arquivos NetCDF para previsão calibrada pelo método da regressão, compatíveis com o GrADS."""
        period_dates = Calibration.compute_period_names(year_fcst, month_fcst) 
        month = f"{month_fcst:02d}"
        fcst_date = f"{year_fcst}{month}0100"
        # Ajusta latitudes e longitudes
        obs = xr.open_dataset("/dados/mmclima/multimodelo/seasonal/obs/gpcp/obs_gpcp_pr_mon_mean_1979-2025.nc")
        lat_obs = obs["lat"].values
        lon_obs = obs["lon"].values

        if base == "nmme":
            time = range(30) #1991-2020
        elif base == "copernicus":
            time = range(24) #1993-2016 

        if variable == "prec":

            varis = ["anom", "prob", "acum", "terc", "prob10mm", "prob20mm", "prob40mm", "prob60mm", 
            "prob80mm", "prob100mm", "prob150mm", "prob200mm", "prob250mm", "prob300mm", "prob400mm", 
            "prob500mm", "prob600mm", "percent20", "percent50", "percent80", "obsmedian","ptercinfbelow", 
            "ptercinfabove", "ptercsupbelow", "ptercsupabove", "probyobs", "probyfcst", "varx", "coef",
            "coxiqr","obsiqr"]

        elif variable == "t2mt":
            varis = ["anom", "prob", "acum", "terc", "obsmedian","ptercinfbelow", 
            "ptercinfabove", "ptercsupbelow", "ptercsupabove", "probyobs", "probyfcst", "varx", "coef",
            "coxiqr","obsiqr"]

        version_multimodel = ConfigModelos.get_multimodel_version(base)

        #Define o nome do diretório dos modelos
        if base == "nmme":
            name_model_dir = model
        elif base == "copernicus":
            if model == "multimodel":
                name_model_dir = "multimodel"
            else:
                name_model_dir = ConfigModelos.get_model_dir_c3s(model)   
                
        nc_path =  (f"/dados/mmclima/multimodelo/seasonal/posproc/{base}/"
            f"{version_multimodel}/forecast/cox/{name_model_dir}/{year_fcst}/{year_fcst}{month}0100/")  

        if not os.path.exists(nc_path):
            os.makedirs(nc_path)
        
        periods = {
            0: 'mnth00', 1: 'mnth01', 2: 'mnth02', 3: 'mnth03', 4: 'mnth04', 
            5: 'seas00', 6: 'seas01', 7: 'seas02'
        }
        
        for period in range(acum_calib.shape[0]):
            name_period = periods.get(period, f"period{period}")
            forecast_date = period_dates[name_period]
            print("Issued:", period_dates['mnth00'], "For:", forecast_date)
            
            for var_name in varis:
                file_path = f"{nc_path}fcst_{variable}_{var_name}_{name_period}_{name_model_dir}_calibrated_cox_{fcst_date}.nc"
                print("Arquivo gerado:", file_path)

                with nc.Dataset(file_path, format='NETCDF3_CLASSIC', mode='w') as ds:
                    # Criação das dimensões
                    ds.createDimension('lat', 72)
                    ds.createDimension('lon', 144)

                    is_3d = (var_name in ("probyobs", "probyfcst", "varx"))
                    if is_3d:
                        if base == "nmme":
                            ds.createDimension('time', 30)
                        else:
                            ds.createDimension('time', 24)

                    # Variáveis de coordenadas
                    lat_var = ds.createVariable('lat', 'f8', ('lat',))
                    lon_var = ds.createVariable('lon', 'f8', ('lon',))
                    lat_var[:] = lat_obs
                    lon_var[:] = lon_obs
                    lat_var.units = "degrees_north"
                    lon_var.units = "degrees_east"              

                    if is_3d:
                        time_var = ds.createVariable('time', 'f8', ('time',))
                        time_var[:] = time
                        time_var.units = "years"
                        
                    # Variável de dados
                    dims = ('lat', 'lon') if not is_3d else ('time', 'lat', 'lon')
                    var = ds.createVariable(var_name, 'f8', dims, fill_value=-999.99)
                    var.long_name = f"{var_name} forecast"

                    if variable == "prec":
                        var.units = "mm" if var_name != "prob" else "%",
                        
                        prob_10mm, prob_20mm, prob_40mm, prob_60mm, prob_80mm, prob_100mm, \
                            prob_150mm, prob_200mm, prob_250mm, prob_300mm, prob_400mm, prob_500mm, prob_600mm = prob_precip
                        
                        percent_20, percent_50, percent_80 = prec_percent

                        data_dict = {
                        "acum": acum_calib[period, ...],
                        "anom": anom_calib[period, ...],
                        "prob": prob_mean[period, ...],
                        "terc": prob_tercile[period, ...],
                        "prob10mm": prob_10mm[period, ...],
                        "prob20mm": prob_20mm[period, ...],
                        "prob40mm": prob_40mm[period, ...],
                        "prob60mm": prob_60mm[period, ...],
                        "prob80mm": prob_80mm[period, ...],
                        "prob100mm": prob_100mm[period, ...],
                        "prob150mm": prob_150mm[period, ...],
                        "prob200mm": prob_200mm[period, ...],
                        "prob250mm": prob_250mm[period, ...],
                        "prob300mm": prob_300mm[period, ...],
                        "prob400mm": prob_400mm[period, ...],
                        "prob500mm": prob_500mm[period, ...],
                        "prob600mm": prob_600mm[period, ...],  
                        "percent20": percent_20[period, ...],  
                        "percent50": percent_50[period, ...],  
                        "percent80": percent_80[period, ...],
                        "obsmedian": obs_mediana[period, ...],
                        "obsiqr": obs_iqr[period, ...],
                        "ptercinfbelow": prob_below_inf[period, ...],  
                        "ptercinfabove": prob_above_inf[period, ...],  
                        "ptercsupbelow": prob_below_sup[period, ...],  
                        "ptercsupabove": prob_above_sup[period, ...],    
                        "probyobs": probyobs_cox[period, ...],  
                        "probyfcst": probyfcst_cox[period, ...],  
                        "varx": varx_cox[period, ...],
                        "coef": coef_beta[period, ...],
                        "coxiqr": cox_iqr[period, ...]                                  
                    }

                    elif variable == "t2mt":
                        var.units = "°C" if var_name != "prob" else "%"     

                        data_dict = {
                        "acum": acum_calib[period, ...],
                        "anom": anom_calib[period, ...],
                        "prob": prob_mean[period, ...],
                        "terc": prob_tercile[period, ...],
                        "obsmedian": obs_mediana[period, ...],
                        "obsiqr": obs_iqr[period, ...],
                        "ptercinfbelow": prob_below_inf[period, ...],  
                        "ptercinfabove": prob_above_inf[period, ...],  
                        "ptercsupbelow": prob_below_sup[period, ...],  
                        "ptercsupabove": prob_above_sup[period, ...],    
                        "probyobs": probyobs_cox[period, ...],  
                        "probyfcst": probyfcst_cox[period, ...],  
                        "varx": varx_cox[period, ...],
                        "coef": coef_beta[period, ...],
                        "coxiqr": cox_iqr[period, ...]                             
                        }                        

                    # Atribui os dados
                    data_to_write = data_dict.get(var_name)
                    var[...] = data_to_write   

                    # Atributos globais
                    ds.description = f"Forecast {var_name} calibrated by regression - period {name_period}"
                    ds.history = f"Issued: {period_dates['mnth00'].upper()} For: {forecast_date.upper()}"
                    ds.source = f"{name_model_dir} calibrated forecast - COX"

    @staticmethod                    
    def write_netcdf_gamma(base, year_fcst, month_fcst, model, variable,
    anom_calib, acum_calib, stdev_calib, alpha_fcst, beta_fcst, prob_below_inf, prob_above_inf,
    prob_below_sup, prob_above_sup, prob_central_terc, prob_tercile, corr, alpha_obs, beta_obs, p_hcst):#, p_hcst, p_obs):

        """Escreve arquivos NetCDF para previsão calibrada pelo método da regressão, compatíveis com o GrADS."""
        period_dates = Calibration.compute_period_names(year_fcst, month_fcst) 
        month = f"{month_fcst:02d}"
        fcst_date = f"{year_fcst}{month}0100"
        # Ajusta latitudes e longitudes
        obs = xr.open_dataset("/dados/mmclima/multimodelo/seasonal/obs/gpcp/obs_gpcp_pr_mon_mean_1979-2025.nc")
        lat_obs = obs["lat"].values
        lon_obs = obs["lon"].values

        if variable == "prec":
            varis = ["anom", "acum", "stdfcst", "alphafcst", "betafcst", "ptercinfbelow", "ptercinfabove", 
            "ptercsupbelow", "ptercsupabove", "pcentral", "terc", "corr", "alphaobs", "betaobs", "pkshcst"]#, "pkshcst", "pksobs"]

        elif variable == "t2mt":
            varis = ["anom", "prob", "acum", "terc"]

        version_multimodel = ConfigModelos.get_multimodel_version(base)

        #Define o nome do diretório dos modelos
        if base == "nmme":
            name_model_dir = model
        elif base == "copernicus":
            if model == "multimodel":
                name_model_dir = "multimodel"
            else:
                name_model_dir = ConfigModelos.get_model_dir_c3s(model)   
                
        nc_path =  (f"/dados/mmclima/multimodelo/seasonal/posproc/{base}/"
            f"{version_multimodel}/forecast/gamma/{name_model_dir}/{year_fcst}/{year_fcst}{month}0100/")  

        if not os.path.exists(nc_path):
            os.makedirs(nc_path)
        
        periods = {
            0: 'mnth00', 1: 'mnth01', 2: 'mnth02', 3: 'mnth03', 4: 'mnth04', 
            5: 'seas00', 6: 'seas01', 7: 'seas02'
        }
        
        for period in range(acum_calib.shape[0]):
            name_period = periods.get(period, f"period{period}")
            forecast_date = period_dates[name_period]
            print("Issued:", period_dates['mnth00'], "For:", forecast_date)
            
            for var_name in varis:
                file_path = f"{nc_path}fcst_{variable}_{var_name}_{name_period}_{name_model_dir}_calibrated_gamma_{fcst_date}.nc"
                print("Arquivo gerado:", file_path)

                with nc.Dataset(file_path, format='NETCDF3_CLASSIC', mode='w') as ds:
                    # Dimensões
                    ds.createDimension('lat', 72)
                    ds.createDimension('lon', 144)
                    
                    # Variáveis de coordenadas
                    lat_var = ds.createVariable('lat', 'f8', ('lat',))
                    lon_var = ds.createVariable('lon', 'f8', ('lon',))
                    lat_var[:] = lat_obs
                    lon_var[:] = lon_obs
                    lat_var.units = "degrees_north"
                    lon_var.units = "degrees_east"

                    # Variável de dados
                    var = ds.createVariable(var_name, 'f8', ('lat', 'lon'), fill_value=-999.99)
                    var.long_name = f"{var_name} forecast"

                    if variable == "prec":
                        var.units = "mm" if var_name != "prob" else "%",

                        data_dict = {
                        "anom": anom_calib[period, ...],
                        "acum": acum_calib[period, ...],
                        "stdfcst": stdev_calib[period, ...],   
                        "alphafcst": alpha_fcst[period, ...],
                        "betafcst": beta_fcst[period, ...],    
                        "alphaobs": alpha_obs[period, ...],
                        "betaobs": beta_obs[period, ...],                                           
                        "ptercinfbelow": prob_below_inf[period, ...],      
                        "ptercinfabove": prob_above_inf[period, ...],   
                        "ptercsupbelow": prob_below_sup[period, ...],   
                        "ptercsupabove": prob_above_sup[period, ...],    
                        "pcentral": prob_central_terc[period, ...],   
                        "terc": prob_tercile[period, ...],     
                        "corr": corr[period, ...],
                        "pkshcst": p_hcst[period,...]
                        # "pksobs": p_obs[period,...]                                                                                                                                             
                    }

                    elif variable == "t2mt":
                        var.units = "°C" if var_name != "prob" else "%"     

                        data_dict = {
                            "acum": acum_calib[period, ...],
                            "anom": anom_calib[period, ...],
                            "prob": prob_mean[period, ...],
                            "terc": prob_tercile[period, ...]
                        }         

                    # Atribui os dados
                    data_to_write = data_dict.get(var_name)
                    var[...] = data_to_write   

                    # Atributos globais
                    ds.description = f"Forecast {var_name} calibrated by regression - period {name_period}"
                    ds.history = f"Issued: {period_dates['mnth00'].upper()} For: {forecast_date.upper()}"
                    ds.source = f"{model} calibrated forecast - COX"


model = "multimodel"
base = "nmme"
var = "prec"
month_fcst = 2
year_fcst = 2025
calibrations = ["gamma"]
# ['canesm5', 'ccsm4', 'cesm1', 'cfsv2', 'gem52nemo', 'spear', 'geos5v2', 'bam12', 'echam46']
for calib in calibrations:

    version_multimodel = ConfigModelos.get_multimodel_version(base)

    # Define o nome do diretório dos modelos
    if base == "nmme":
        name_model_dir = model
    elif base == "copernicus":
        if model == "multimodel":
            name_model_dir = "multimodel"
        else:
            name_model_dir = ConfigModelos.get_model_dir_c3s(model)   


    # # FAZ CHECAGEM SE OS ARQUIVOS DAS PREVISÕES CALIBRADAS FORAM GERADOS
    # if model != "multimodel": #o multimodelo sempre vai processar (no caso de atualizar modelo)
    #     pattern = os.path.join(path_fcst_nc, f"fcst_{var}_*.nc")
    #     files = glob.glob(pattern)

    #     if files:
    #         print(f"[SKIP] {model.upper()} ({var.upper()}) ({calib.upper()}) já processado")
    #         continue

    print(f"\n[RUN] {base.upper()} - {model.upper()} ({var.upper()}) ({calib.upper()})")                

    print(f"\nGerando os arquivos NetCDF das Previsões Sazonais calibradas para: {model.upper()} - {calib.upper()} - {var.upper()}")
    
    if calib == "regr":
        if var == "prec":

            (anom_nocalib, anom_calib, acum_calib, std_calib, prob_above_calib, prob_tercile, 
            prob_exc_mm, prec_percent, obs_mean, obs_std, obs_total, obs_tercinf, obs_tercsup, 
            prob_below_tercinf, prob_above_tercinf, prob_below_tercsup, prob_above_tercsup, 
            prob_central_terc, model_cor) = Calibration.regression_calibration_model(path_fcst, path_hcst, path_obs, base, year_fcst, month_fcst, model, var)
            
            Calibration.write_netcdf_model_nocalibrated(base, year_fcst, month_fcst, model, var, anom_nocalib)

            Calibration.write_netcdf_model_regression(base, year_fcst, month_fcst, model, 
            var, anom_calib, acum_calib, std_calib, prob_above_calib, prob_tercile, 
            obs_mean, obs_std, obs_total, obs_tercinf, obs_tercsup, prob_below_tercinf, 
            prob_above_tercinf, prob_below_tercsup, prob_above_tercsup, 
            prob_central_terc, model_cor, prob_exc_mm, prec_percent)

        elif var == "t2mt":
            (anom_nocalib, anom_calib, acum_calib, std_calib, prob_above_calib,  
            prob_tercile, obs_mean, obs_std, obs_total, obs_tercinf, obs_tercsup, 
            prob_below_tercinf, prob_above_tercinf, prob_below_tercsup, prob_above_tercsup, 
            prob_central_terc, model_cor) = Calibration.regression_calibration_model(path_fcst, path_hcst, path_obs, base, year_fcst, month_fcst, model, var)
            
            Calibration.write_netcdf_model_regression(base, year_fcst, month_fcst, model, 
            var, anom_calib, acum_calib, std_calib, prob_above_calib, prob_tercile, 
            obs_mean, obs_std, obs_total, obs_tercinf, obs_tercsup, prob_below_tercinf, 
            prob_above_tercinf, prob_below_tercsup, prob_above_tercsup, 
            prob_central_terc, model_cor)

            #Escreve o arquivo
            Calibration.write_netcdf_model_nocalibrated(base, year_fcst, month_fcst, model, var, anom_nocalib)

    elif calib == "cox":
        if var == "prec":
            (anom_calib, mediana_calib, prob_above_calib,
            prob_tercile, prob_exc_mm, prec_percent, prob_below_inf, prob_above_inf,
            prob_below_sup, prob_above_sup, probyobs_cox, probyfcst_cox, varx_cox, coef_beta, 
            cox_iqr, obs_mediana, obs_iqr) = Calibration.calibration_cox_model(path_fcst, path_hcst, path_obs, base, year_fcst, month_fcst, model, var)

            Calibration.write_netcdf_model_cox(base, year_fcst, month_fcst, model, var, 
            anom_calib, mediana_calib, prob_above_calib, prob_tercile, prob_below_inf, 
            prob_above_inf,  prob_below_sup, prob_above_sup, probyobs_cox, probyfcst_cox, 
            varx_cox, coef_beta, cox_iqr, obs_mediana, obs_iqr, prob_exc_mm, prec_percent)

        elif var == "t2mt":
            (anom_calib, mediana_calib, prob_above_calib,
            prob_tercile, prob_below_inf, prob_above_inf,
            prob_below_sup, prob_above_sup, probyobs_cox, probyfcst_cox, varx_cox, coef_beta, 
            cox_iqr, obs_mediana, obs_iqr) = Calibration.calibration_cox_model(path_fcst, path_hcst, path_obs, base, year_fcst, month_fcst, model, var)

            Calibration.write_netcdf_model_cox(base, year_fcst, month_fcst, model, var, 
            anom_calib, mediana_calib, prob_above_calib, prob_tercile, prob_below_inf, 
            prob_above_inf,  prob_below_sup, prob_above_sup, probyobs_cox, probyfcst_cox, 
            varx_cox, coef_beta, cox_iqr, obs_mediana, obs_iqr)

    elif calib == "gamma":
        if var == "prec":
            (anom_calib, acum_calib, stdev_calib, alpha, beta, prob_below_inf, prob_above_inf,
            prob_below_sup, prob_above_sup, prob_central_terc, prob_tercile, corr, alpha_obs, beta_obs, p_hcst) = Calibration.gamma_calibration_model(path_fcst, path_hcst, path_obs, base, year_fcst, month_fcst, model, var)
        
            Calibration.write_netcdf_gamma(base, year_fcst, month_fcst, model, var, 
            anom_calib, acum_calib, stdev_calib, alpha, beta, prob_below_inf, prob_above_inf,
            prob_below_sup, prob_above_sup, prob_central_terc, prob_tercile, corr, alpha_obs, beta_obs, p_hcst)
                
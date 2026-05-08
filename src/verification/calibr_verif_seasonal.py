import os
import pandas as pd
import numpy as np
import xarray as xr
import scipy.stats as stats
import netCDF4 as nc
import calendar
import time
import multiprocessing as mp
from pathlib import Path
from datetime import date, datetime,timedelta
from dateutil.relativedelta import *
from src.verification.hcst_verif_seasonal import Hindcast
from src.verification.obs_verif_seasonal import Observation
from src.config.config_models_seasonal import ConfigModelos
from scipy.stats import gamma, norm
from scipy.stats.stats import pearsonr
from scipy.stats import mannwhitneyu
from joblib import Parallel, delayed
from lifelines import CoxPHFitter
from scipy.interpolate import PchipInterpolator
from sklearn.metrics import roc_auc_score
import matplotlib.pyplot as plt



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
    def correlation_model(obs_total, hcst_total, n_jobs=6):
        """
        Cálculo da correlação em validação cruzada entre anomalias dos hindcasts e observações 
        """
        ny, np_, ni, nj = hcst_total.shape
        model_cor = np.full((ny, np_, ni, nj), np.nan)

        def compute_lat_block(i):
            out = np.full((ny, np_, nj), np.nan)
            for p in range(np_):
                for j in range(nj):
                    obs_series = obs_total[:, p, i, j]
                    hind_series = hcst_total[:, p, i, j]
                    if np.all(np.isnan(obs_series)) or np.all(np.isnan(hind_series)):
                        continue

                    # Leave-one-out
                    for y in range(ny):
                        obs_anom = np.delete(obs_series, y)
                        hind_anom = np.delete(hind_series, y)

                        mask = ~np.isnan(obs_anom) & ~np.isnan(hind_anom)
                        if mask.sum() > 1:
                            corr = pearsonr(hind_anom[mask], obs_anom[mask])[0]
                            out[y, p, j] = max(corr, 0)  # Corr negativa vira 0
            return i, out

        # Paraleliza por latitude
        results = Parallel(n_jobs=n_jobs, backend='loky')(
            delayed(compute_lat_block)(i) for i in range(ni)
        )

        for i, block in results:
            model_cor[:, :, i, :] = block

        return model_cor


    @staticmethod 
    def interpolation_cox(vetorx, prob, y_alvo, alongar=True, inverter=True, verbose=False):
        """
        Alonga e interpola uma curva (varx_clim, curva) para encontrar o valor de x correspondente a y_alvo.
        """
        try:
            curva_proc = 1 - prob if inverter else prob
            times_proc = vetorx

            if alongar:
                if inverter:
                    # Estamos usando CDF (P[T ≤ t]), então extremos são 0 → 1
                    curva_proc = np.concatenate(([0], curva_proc, [1]))
                else:
                    # Estamos usando curva de sobrevivência (P[T > t]), então extremos são 1 → 0
                    curva_proc = np.concatenate(([1], curva_proc, [0]))

                times_proc = np.concatenate(([np.min(vetorx)], vetorx, [np.max(vetorx)]))
                #times_proc = np.concatenate(([0], vetorx, [np.max(vetorx)]))

            for i in range(len(curva_proc) - 1):
                y1, y2 = curva_proc[i], curva_proc[i + 1]
                x1, x2 = times_proc[i], times_proc[i + 1]

                if (y1 - y_alvo) * (y2 - y_alvo) <= 0 and y1 != y2:
                    x_interp = x1 + (y_alvo - y1) * ((x2 - x1) / (y2 - y1))
                    return float(x_interp)

            if verbose:
                print(" Valor y_alvo fora do intervalo da curva.")
            return None

        except Exception as e:
            if verbose:
                print(f"[Erro na interpolação]: {e}")
            return None

    @staticmethod  
    def probabilidade_cox(vetorx, prob, x_alvo, alongar=True, inverter=True, verbose=False):
        """
        Encontra o valor da probabilidade (y) dado um valor de X (x_alvo),
        interpolando a curva (vetorx, prob).

        Parâmetros:
        ------------
        vetorx : array-like
            Eixo X da curva (ex: valores de precipitação ou temperatura).
        prob : array-like
            Eixo Y da curva (ex: probabilidades cumulativas ou de sobrevivência).
        x_alvo : float
            Valor de X para o qual se quer estimar a probabilidade.
        alongar : bool, opcional
            Se True, adiciona limites [mín, máx] à curva para garantir cobertura total.
        inverter : bool, opcional
            Se True, usa 1 - prob (para converter de curva de sobrevivência → CDF).
        verbose : bool, opcional
            Se True, exibe mensagens em caso de erro ou extrapolação.

        Retorna:
        --------
        float ou None
            Valor interpolado da probabilidade correspondente a x_alvo.
        """
        try:
            # Garantir arrays NumPy
            vetorx = np.asarray(vetorx, dtype=float)
            prob = np.asarray(prob, dtype=float)

            # Ordenar vetorx (caso não esteja)
            order = np.argsort(vetorx)
            vetorx = vetorx[order]
            prob = prob[order]

            # Inversão, se necessário
            curva_proc = 1 - prob if inverter else prob
            times_proc = vetorx

            # Alongamento controlado
            if alongar:
                xmin, xmax = np.min(times_proc), np.max(times_proc)

                if inverter:
                    # Curva tipo CDF (0 → 1)
                    curva_proc = np.concatenate(([0], curva_proc, [1]))
                else:
                    # Curva de sobrevivência (1 → 0)
                    curva_proc = np.concatenate(([1], curva_proc, [0]))

                # Adiciona bordas ligeiramente fora do domínio
                delta = 0.01 * abs(xmax - xmin)
                times_proc = np.concatenate(([xmin - delta], vetorx, [xmax + delta]))

            # Clampar o alvo dentro dos limites
            x_alvo = np.clip(x_alvo, np.min(times_proc), np.max(times_proc))

            # Interpolação linear
            for i in range(len(times_proc) - 1):
                x1, x2 = times_proc[i], times_proc[i + 1]
                y1, y2 = curva_proc[i], curva_proc[i + 1]

                if (x1 - x_alvo) * (x2 - x_alvo) <= 0 and x1 != x2:
                    y_interp = y1 + (x_alvo - x1) * ((y2 - y1) / (x2 - x1))
                    return float(np.clip(y_interp, 0, 1))  # restringe entre 0 e 1

            if verbose:
                print(f"Valor x_alvo={x_alvo} fora do intervalo da curva [{times_proc[0]}, {times_proc[-1]}].")
            return None

        except Exception as e:
            if verbose:
                print(f"[Erro na interpolação]: {e}")
            return None

    @staticmethod  
    def gamma_calibration_model(path_fcst, path_hcst, path_obs, base, year_fcst, month_fcst, model, var):
        ''' Calibração das previsões em tempo-real através do método da regressão '''

        print("linear regression: ", month_fcst)
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
        obs_std = np.stack([std[p] for p in ordered_periods], axis=1)
        obs_mean = np.stack([mean[p] for p in ordered_periods], axis=1)
        obs_var =  np.stack([vari[p] for p in ordered_periods], axis=1)
        obs_mediana = np.stack([mediana[p] for p in ordered_periods], axis=1)        
        obs_tercinf = np.stack([tercil_inf[p] for p in ordered_periods], axis=1)
        obs_tercsup = np.stack([tercil_sup[p] for p in ordered_periods], axis=1)             
        
        # --- Hindcast 
        hindcast = Hindcast(path_fcst, path_hcst)
        hcst_total, hcst_mean, hcst_std, hcst_var, hcst_anomaly = hindcast.mean_std_anom_hindcast_gamma(base, year_fcst, month_fcst, model, var)     

        # --- Correlação 
        model_cor = Calibration.correlation_model(obs_total, hcst_total)

        # --- Parâmetros Gamma 
        alpha_obs = (obs_mean ** 2) / obs_var #obs
        alpha_hcst = (hcst_mean ** 2) / hcst_var #hcst
        beta_obs  = obs_var / obs_mean #obs
        beta_hcst = hcst_var / hcst_mean #hcst
        
        # --- Padronização Gamma para Normal
        eps = 1e-6
        ntime, nper, nlat, nlon = hcst_total.shape

        anomalia2_all = np.full((ntime, nper, nlat, nlon), np.nan)
        media2_all = np.full((ntime, nper, nlat, nlon), np.nan)
        alpha2_all = np.full((ntime, nper, nlat, nlon), np.nan)
        beta2_all  = np.full((ntime, nper, nlat, nlon), np.nan)
        prob_below_all = np.full((ntime, nper, nlat, nlon), np.nan)
        prob_above_all = np.full((ntime, nper, nlat, nlon), np.nan)
        prob_below_mean_all = np.full((ntime, nper, nlat, nlon), np.nan)

        for k in range(ntime):

            # -------------------
            # Remover o ano k 
            # -------------------
            mask = np.ones(ntime, dtype=bool) #Cria um array booleano de tamanho ntime 
            mask[k] = False  #Coloca False exatamente na posição k (remover o ano na validação cruzada)
            serie_hcst = hcst_total[mask, :, :, :]  # Série sem o ano k
            serie_obs  = obs_total[mask, :, :, :]   

            # ====================================================
            # 1. Gamma -> Normal (padronização das séries - HCST)
            # ====================================================
            gamma_hcst = gamma.cdf(
                serie_hcst,
                a=alpha_hcst[k][None, :, :, :], #adiciona uma dimensão e seleciona o indice k
                scale=beta_hcst[k][None, :, :, :]
            )

            gamma_hcst = np.clip(gamma_hcst, eps, 1 - eps) #coloca valores no inicio e no fim da série para evitar 0 e 1
            spi_h = norm.ppf(gamma_hcst) #Transforma probabilidade -> Normal(0,1)

            # ===================================================
            # 1. Gamma -> Normal (padronização das séries - OBS)
            # ===================================================
            gamma_obs = gamma.cdf(
                serie_obs,
                a=alpha_obs[k][None, :, :, :],
                scale=beta_obs[k][None, :, :, :]
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
            x_prev = hcst_total[k]   # (nper, nlat, nlon)

            xp = gamma.cdf(
                x_prev,
                a=alpha_hcst[k],
                scale=beta_hcst[k]
            )

            xp = np.clip(xp, eps, 1 - eps)

            xlinhaprevisao = norm.ppf(xp) #Padronização

            ylinhamedio = alpha_reg + beta_reg * xlinhaprevisao #Regressão no espaço padronizado (Y')

            # ----------------------------------------
            # Voltar para unidades físicas (mm)
            # calculo do alpha e beta para gerar
            # a distribuição Gamma prevista
            # ---------------------------------------- 

            anomalia2 = ylinhamedio * obs_std[k] * corr     
            #media2 =  (ylinhamedio * obs_std[k] * corr) + obs_mean[k]    
            media2 = ylinhamedio * obs_std[k] + obs_mean[k] #Cálculo da Média prevista em milimetros
            desvio2 = obs_std[k] * np.sqrt(1 - corr**2)
            media2[~np.isfinite(media2)] = np.nan     

            alpha2 = (media2**2) / (desvio2**2) #Estimativa dos valores de alpha da gamma prevista
            beta2  = (desvio2**2) / media2 #Estimativa dos valores de beta da gamma prevista       

            #Calibrated Probability Above/Below Obs. Terciles  
            prob_below_inf = gamma.cdf(obs_tercinf[k], a=alpha2, scale=beta2) 
            prob_above_sup = 1 - gamma.cdf(obs_tercsup[k], a=alpha2,scale=beta2)

            #--- Probabilidade acima/abaixo da média (calibrada)       
            prob_below_mean = gamma.cdf(obs_mean[k], a=alpha2, scale=beta2) 
            prob_above_mean = 1 - gamma.cdf(obs_mean[k], a=alpha2,scale=beta2)

            anomalia2_all[k] = anomalia2
            media2_all[k] = media2
            alpha2_all[k] = alpha2
            beta2_all[k]  = beta2
            prob_below_all[k] = prob_below_inf
            prob_above_all[k] = prob_above_sup
            prob_below_mean_all[k] = prob_below_mean

        #BINÁRIOS
        binobsinf = (obs_total <= obs_tercinf).astype(int)
        binobssup = (obs_total >= obs_tercsup).astype(int)
        binobsmed = (obs_total <= obs_mean).astype(int)

        return (obs_total, obs_anomaly, anomalia2_all, media2_all, alpha2_all, beta2_all, prob_below_all, 
        prob_above_all, prob_below_mean_all, binobsinf, binobssup, binobsmed)

    @staticmethod  
    def regression_calibration_model(path_fcst, path_hcst, path_obs, base, year_fcst, month_fcst, model, var):
        ''' Calibração das previsões em tempo-real através do método da regressão '''

        print("linear regression: ", month_fcst)
        print("model: ", model, "var: ", var)

        # --- Observação
        obs = Observation(path_obs)
        statistcs = obs.mean_std_anom_obs(base, month_fcst, var) 
        anom = {k: v['anomaly'] for k, v in statistcs.items() if 'anomaly' in v}
        std = {k: v['std'] for k, v in statistcs.items() if 'std' in v}
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
        obs_std = np.stack([std[p] for p in ordered_periods], axis=1)
        obs_mean = np.stack([mean[p] for p in ordered_periods], axis=1)
        obs_mediana = np.stack([mediana[p] for p in ordered_periods], axis=1)        
        obs_tercinf = np.stack([tercil_inf[p] for p in ordered_periods], axis=1)
        obs_tercsup = np.stack([tercil_sup[p] for p in ordered_periods], axis=1)             
        
        # --- Hindcast 
        hindcast = Hindcast(path_fcst, path_hcst)
        hcst_total, hcst_mean, hcst_std, hcst_anomaly = hindcast.mean_std_anom_hindcast(base, year_fcst, month_fcst, model, var)     

        # --- Correlação 
        model_cor = Calibration.correlation_model(obs_total, hcst_total)

             
        # ---- Calibração
        #anomaly_multimodel = (realtime_fcst) - (hcst_mean)
        prediction_signal = (hcst_anomaly) / (hcst_std)
        fcst_stdev = np.sqrt( 1 - (model_cor ** 2))
        fcst_mean_stand = prediction_signal * model_cor #Forecast Mean (standardized)
        fcst_mm = (fcst_mean_stand * obs_std) #Anomaly calibrated
        sefcst = (obs_std) * (np.sqrt( 1 - (model_cor ** 2))) #Forecast Standard Deviation (in millimeters)
        fsfcst = (fcst_mean_stand * obs_std) + (obs_mean) #Forecast Mean (in millimeters)     
        if var == "prec":
            fsfcst[fsfcst < 0] = 0       

        #--- Probabilidade acima/abaixo da média (calibrada)
        prob_below_mean = stats.norm(fsfcst, sefcst).cdf(obs_mean)
        prob_above_mean = (1 - (stats.norm(fsfcst, sefcst).cdf(obs_mean)))

        #PROBABILITY ABOVE/BELOW TERCILES CALIBRATED
        #sefcst_stand = (np.sqrt( 1 - (model_cor ** 2))) #desvio padrão padronizado
        prob_below_inf = stats.norm(fsfcst, sefcst).cdf(obs_tercinf) #* 100
        prob_above_sup = ( 1 - stats.norm(fsfcst, sefcst).cdf(obs_tercsup)) #* 100       
        prob_central_terc = (1 - prob_below_inf - prob_above_sup)

        #BINÁRIOS
        binobsinf = (obs_total <= obs_tercinf).astype(int)
        binobssup = (obs_total >= obs_tercsup).astype(int)
        binobsmed = (obs_total <= obs_mean).astype(int)

        return (obs_anomaly, obs_total, fcst_mm, fsfcst, prob_below_mean, 
        prob_below_inf, prob_above_sup, binobsmed, binobsinf, binobssup)


    @staticmethod  
    def corr_verif(obs_anomaly, hcst_anomaly):
        ''' Cálculo da correlação leave-one-out entre anomalias dos hindcasts e observações, com paralelização '''

        model_cor = np.full((hcst_anomaly.shape[1], 72, 144), np.nan) 

        for p in range (hcst_anomaly.shape[1]):
            for i in range(72):
                for j in range(144):
                    obs_anom_point = obs_anomaly[:, p, i, j]
                    hind_anom_point = hcst_anomaly[:, p, i, j]
                    # Máscara de valores válidos (não-NaN em ambas séries)
                    valid_mask = ~np.isnan(obs_anom_point) & ~np.isnan(hind_anom_point)

                    if valid_mask.sum() > 1:  # Só calcula correlação se houver dados suficientes
                        model_cor[p, i, j] = pearsonr(
                            hind_anom_point[valid_mask],
                            obs_anom_point[valid_mask]
                        )[0]
        model_cor[model_cor < 0] = 0
        #
        return model_cor    

    @staticmethod  
    def corr_verif_with_pvalue(obs_anomaly, hcst_anomaly, alpha=0.05):
        """
        Cálculo da correlação leave-one-out entre anomalias dos hindcasts
        e observações, com p-value e máscara de significância.

        Retorna:
            cor_array  (period, lat, lon)
            p_array    (period, lat, lon)
            sig_array  (period, lat, lon)  -> True onde p < alpha e r > 0
        """

        nper = hcst_anomaly.shape[1]
        nlat = 72
        nlon = 144

        cor_array = np.full((nper, nlat, nlon), np.nan)
        p_array   = np.full((nper, nlat, nlon), np.nan)
        sig_array = np.zeros((nper, nlat, nlon), dtype=bool)

        for p in range(nper):
            for i in range(nlat):
                for j in range(nlon):

                    obs_anom_point  = obs_anomaly[:, p, i, j]
                    hcst_anom_point = hcst_anomaly[:, p, i, j]

                    # Máscara de valores válidos
                    valid = ~np.isnan(obs_anom_point) & ~np.isnan(hcst_anom_point)

                    if valid.sum() > 1:
                        r, pval = pearsonr(
                            hcst_anom_point[valid],
                            obs_anom_point[valid]
                        )

                        cor_array[p, i, j] = r
                        p_array[p, i, j] = pval

                        # Significância estatística (bicaudal)
                        if (pval < alpha) and (r > 0):
                            sig_array[p, i, j] = True

        # Zerar correlações negativas (opcional, seguindo seu padrão)
        cor_array[cor_array < 0] = 0

        return cor_array, p_array, sig_array  

    @staticmethod  
    def area_roc(bin_array, prob_array, n_jobs=13):
        """
        Calcula Área sob a Curva ROC em paralelo.
        
        Parâmetros:
        - bin_array: np.ndarray, shape (period_climatology, 8, 72, 144)
        - prob_array: np.ndarray, shape (period_climatology, 8, 72, 144)
        - n_jobs: número de threads para paralelização (-1 = todos os núcleos)

        Retorno:
        - auc: np.ndarray, shape (8, 72, 144)
        """
        nyears, nleads, nlat, nlon = bin_array.shape
        auc_array = np.full((nleads, nlat, nlon), np.nan)

        def compute_point(lead, i, j):
            bin_series = bin_array[:, lead, i, j]
            prob_series = prob_array[:, lead, i, j]

            try:
                auc = roc_auc_score(bin_series, prob_series)
                return (lead, i, j, auc)
            except ValueError:
                return (lead, i, j, np.nan)

        # Lista de tarefas
        tasks = [(lead, i, j) for lead in range(nleads)
                                for i in range(nlat)
                                for j in range(nlon)]

        results = Parallel(n_jobs=n_jobs)(delayed(compute_point)(l, i, j) for l, i, j in tasks)

        # Preencher matriz de saída
        for lead, i, j, value in results:
            auc_array[lead, i, j] = value

        return auc_array

    @staticmethod  
    def area_roc_with_pvalue(bin_array, prob_array, alpha=0.05, n_jobs=6):
        """
        Calcula:
            - Area Under the ROC Curve (AUC)
            - p-value (Mann–Whitney U test)
            - máscara de significância (p < alpha e AUC > 0.5)

        Parâmetros:
            bin_array  : (nyears, nleads, nlat, nlon)
            prob_array : (nyears, nleads, nlat, nlon)

        Retorna:
            auc_array : (nleads, nlat, nlon)
            p_array   : (nleads, nlat, nlon)
            sig_array : (nleads, nlat, nlon)  [bool]
        """

        nyears, nleads, nlat, nlon = bin_array.shape

        auc_array = np.full((nleads, nlat, nlon), np.nan)
        p_array   = np.full((nleads, nlat, nlon), np.nan)
        sig_array = np.zeros((nleads, nlat, nlon), dtype=bool)

        def compute_point(lead, i, j):
            bin_series  = bin_array[:, lead, i, j]
            prob_series = prob_array[:, lead, i, j]

            # Remove NaNs
            valid = ~np.isnan(bin_series) & ~np.isnan(prob_series)

            bin_s  = bin_series[valid]
            prob_s = prob_series[valid]

            # Precisa ter eventos e não-eventos
            if len(bin_s) < 3:
                return lead, i, j, np.nan, np.nan, False

            if (np.sum(bin_s == 1) < 2) or (np.sum(bin_s == 0) < 2):
                return lead, i, j, np.nan, np.nan, False

            try:
                auc = roc_auc_score(bin_s, prob_s)

                # Mann–Whitney U test (AUC equivalence)
                prob_event   = prob_s[bin_s == 1]
                prob_nonev   = prob_s[bin_s == 0]

                u_stat, pval = mannwhitneyu(
                    prob_event,
                    prob_nonev,
                    alternative="greater"
                )

                sig = (pval < alpha) and (auc > 0.5)

                return lead, i, j, auc, pval, sig

            except ValueError:
                return lead, i, j, np.nan, np.nan, False

        # Lista de tarefas
        tasks = [(lead, i, j)
                for lead in range(nleads)
                for i in range(nlat)
                for j in range(nlon)]

        results = Parallel(n_jobs=n_jobs)(
            delayed(compute_point)(l, i, j) for l, i, j in tasks
        )

        # Preencher matrizes de saída
        for lead, i, j, auc, pval, sig in results:
            auc_array[lead, i, j] = auc
            p_array[lead, i, j]   = pval
            sig_array[lead, i, j] = sig

        return auc_array, p_array, sig_array

    @staticmethod          
    def msss_skill(forecast_anom, obs_anom):
        """
        Calcula o índice de destreza do erro quadrático médio (MSSS).
        
        forecast_anom, obs_anom: np.ndarray (ntime, 8, 72, 144)
        Retorna: msss (8, 72, 144)
        """
        fmse = np.mean((forecast_anom - obs_anom) ** 2, axis=0)
        refmse = np.mean((0 - obs_anom) ** 2, axis=0)
        msss = 1 - (fmse / refmse)
        return msss

    @staticmethod  
    def compute_bias(forecast_total, obs_total):
        """
        Calcula o viés (bias) entre previsão total e observação total.
        
        forecast_total, obs_total: np.ndarray (ntime, 8, 72, 144)
        Retorna: bias (8, 72, 144)
        """
        return np.mean(forecast_total - obs_total, axis=0)

    @staticmethod  
    def msss_fase_amplitude(forecast_anom, obs_anom):
        """
        Calcula fase (pher) e amplitude (aper) do índice de destreza.

        forecast_anom, obs_anom: np.ndarray (ntime, 8, 72, 144)
        Retorna:
            pher: np.ndarray (8, 72, 144)
            aper: np.ndarray (8, 72, 144)
        """
        # Desvios padrão
        fstd = np.std(forecast_anom, axis=0)
        ostd = np.std(obs_anom, axis=0)

        # Correlação de Pearson ao longo do tempo
        nyears, nleads, nlat, nlon = forecast_anom.shape
        corr = np.full((nleads, nlat, nlon), np.nan)

        for lead in range(nleads):
            for i in range(nlat):
                for j in range(nlon):
                    f = forecast_anom[:, lead, i, j]
                    o = obs_anom[:, lead, i, j]
                    if np.all(np.isnan(f)) or np.all(np.isnan(o)):
                        continue
                    if np.std(f) == 0 or np.std(o) == 0:
                        continue
                    corr[lead, i, j] = np.corrcoef(f, o)[0, 1]

        # Fase
        pher = 2 * (fstd / ostd) * corr
        # Amplitude
        aper = (fstd / ostd) ** 2

        return pher, aper


    @staticmethod
    def run(type, *args, **kwargs):
        if type == "regression":
            return Calibration.regression_calibration_model(*args, **kwargs)
        elif type == "cox":
            return Calibration.calibration_cox_model(*args, **kwargs)

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
                month_abbr = calendar.month_abbr[m].upper()
                result[period] = f"{month_abbr} {y}"
            elif period.startswith("seas"):
                # Três meses
                season_str = ''.join(calendar.month_abbr[m][0].upper() for m, _ in months)
                result[period] = f"{season_str} {months[0][1]}"

        return result

    @staticmethod
    def process_point_wrapper(base, ano_out, period, clat, clon,
                              hcst_anomaly, obs_series, obs_tercinf,
                              obs_tercsup, obs_mediana):

        obs_pt = np.delete(obs_series[period, :, clat, clon], ano_out)
        anomhcst = np.delete(hcst_anomaly[:, period, clat, clon], ano_out)
        present = np.ones_like(obs_pt)

        years = list(range(1991, 2021)) if base == "nmme" else list(range(1993, 2017))
        years_hcst = np.delete(years, ano_out)

        dados = pd.DataFrame({
            "year": years_hcst,
            "obs": obs_pt,
            "anomhcst": anomhcst,
            "present": present
        })

        try:
            cox_model = CoxPHFitter()
            cox_model.fit(
                dados[["obs", "anomhcst", "present"]],
                duration_col="obs",
                event_col="present",
                show_progress=False
            )
            coef = cox_model.params_["anomhcst"]
            basePEX = cox_model.baseline_survival_
            varx_clim = basePEX.index.values
            proby_clim = basePEX.values.flatten()

        except Exception:
            coef = 0.0
            basePEX = pd.Series(np.linspace(1, 0, len(dados)), index=np.sort(dados["obs"]))
            varx_clim = basePEX.index.values
            proby_clim = basePEX.values.flatten()

        # --- Cox previsão ---
        anomfcst_val = hcst_anomaly[ano_out, period, clat, clon]
        exp_term = np.exp(coef * anomfcst_val)
        proby_fcstcox = proby_clim ** exp_term

        tercinf_climatology = obs_tercinf[ano_out, period, clat, clon]
        tercsup_climatology = obs_tercsup[ano_out, period, clat, clon]
        mediana_climatology = obs_mediana[ano_out, period, clat, clon]

        mediana_prevcox = Calibration.interpolation_cox(varx_clim, proby_fcstcox, 0.5, inverter=False)
        pinf = Calibration.probabilidade_cox(varx_clim, proby_fcstcox, tercinf_climatology, alongar=True, inverter=False)
        psup = Calibration.probabilidade_cox(varx_clim, proby_fcstcox, tercsup_climatology, alongar=True, inverter=False)
        pmed = Calibration.probabilidade_cox(varx_clim, proby_fcstcox, mediana_climatology, alongar=True, inverter=False)

        return (ano_out, period, clat, clon,
                mediana_prevcox,
                mediana_prevcox - mediana_climatology,
                pinf, psup, pmed)

    @staticmethod
    def calibration_cox_model(path_fcst, path_hcst, path_obs, base,
                              year_fcst, month_fcst, model, var):

        t0 = time.perf_counter()

        # --- Observações ---
        obs = Observation(path_obs)
        statistcs = obs.mean_std_anom_obs(base, month_fcst, var)
        anom = {k: v['anomaly'] for k, v in statistcs.items() if 'anomaly' in v}
        std = {k: v['std'] for k, v in statistcs.items() if 'std' in v}
        mean = {k: v['mean'] for k, v in statistcs.items() if 'mean' in v}
        mediana = {k: v['mediana'] for k, v in statistcs.items() if 'mediana' in v}
        tercil_inf = {k: v['tercilinf'] for k, v in statistcs.items() if 'tercilinf' in v}
        tercil_sup = {k: v['tercilsup'] for k, v in statistcs.items() if 'tercilsup' in v}
        total = {k: v['total'] for k, v in statistcs.items() if 'total' in v}

        ordered_periods = list(anom.keys())
        obs_series = np.stack([obs.calculate_obs_periods(base, month_fcst, var)[p] for p in ordered_periods], axis=0)
        obs_total = np.stack([total[p] for p in ordered_periods], axis=1)
        obs_anomaly = np.stack([anom[p] for p in ordered_periods], axis=1)
        obs_std = np.stack([std[p] for p in ordered_periods], axis=1)
        obs_mean = np.stack([mean[p] for p in ordered_periods], axis=1)
        obs_mediana = np.stack([mediana[p] for p in ordered_periods], axis=1)
        obs_tercinf = np.stack([tercil_inf[p] for p in ordered_periods], axis=1)
        obs_tercsup = np.stack([tercil_sup[p] for p in ordered_periods], axis=1)

        # --- Hindcast ---
        hindcast = Hindcast(path_fcst, path_hcst)
        hcst_total, hcst_mean, hcst_std, hcst_anomaly = hindcast.mean_std_anom_hindcast(
            base, year_fcst, month_fcst, model, var
        )

        # --- Dimensões e arrays ---
        if base == "nmme":
            shape = (30, 8, 72, 144)
            years = list(range(1991, 2021))
        else:
            shape = (24, 8, 72, 144)
            years = list(range(1993, 2017))

        mediana_fcst_cox = np.full(shape, np.nan, np.float32)
        anomalia_fcst_cox = np.full(shape, np.nan, np.float32)
        probexc_mediana = np.full(shape, np.nan, np.float32)
        probexc_tercinf = np.full(shape, np.nan, np.float32)
        probexc_tercsup = np.full(shape, np.nan, np.float32)

        total_jobs = len(years) * 8 * 72 * 144
        #print(f"Iniciando {total_jobs:,} pontos com {mp.cpu_count()} CPUs disponíveis...")
        print("cox regression: ", month_fcst)
        print("model: ", model, "var: ", var)

        # --- Execução paralela ---
        results = Parallel(n_jobs=13, batch_size='auto', backend="loky", verbose=0)(
            delayed(Calibration.process_point_wrapper)(
                base, ano, period, clat, clon,
                hcst_anomaly, obs_series,
                obs_tercinf, obs_tercsup, obs_mediana
            )
            for ano in range(len(years))
            for period in range(8)
            for clat in range(72)
            for clon in range(144)
        )

        # --- Inserção vetorizada ---
        for (ano_, period, clat, clon, mediana_prevcox, anom, p_inf, p_sup, p_med) in results:
            mediana_fcst_cox[ano_, period, clat, clon] = mediana_prevcox
            anomalia_fcst_cox[ano_, period, clat, clon] = anom
            probexc_tercinf[ano_, period, clat, clon] = p_inf
            probexc_tercsup[ano_, period, clat, clon] = p_sup
            probexc_mediana[ano_, period, clat, clon] = p_med

        # --- Probabilidades derivadas ---
        prob_below_inf = 1 - probexc_tercinf
        prob_above_sup = probexc_tercsup
        prob_central_terc = 1 - prob_below_inf - prob_above_sup
        probbelow_mediana = 1 - probexc_mediana

        # --- Binários ---
        binobsinf = (obs_total <= obs_tercinf).astype(int)
        binobssup = (obs_total >= obs_tercsup).astype(int)
        binobsmediana = (obs_total <= obs_mediana).astype(int)

        t1 = time.perf_counter()

        return (obs_anomaly, obs_total, anomalia_fcst_cox, mediana_fcst_cox, 
                probbelow_mediana, prob_below_inf, prob_above_sup,
                binobsmediana, binobsinf, binobssup)

    # @staticmethod
    # def nocalibration_model(base, month_fcst, model, var, year_fcst, path_fcst, path_hcst):

    #     def process_year(i, hcst_total):
    #         print(f"Processando ano {i}", flush=True)
    #         n_members = hcst_total.shape[2]

    #         # Exclui o ano i
    #         data_excl_i = np.delete(hcst_total, i, axis=0)
    #         anos = data_excl_i.shape[0]

    #         # Cálculo tercis e média
    #         tercinf = np.nanpercentile(data_excl_i, 33.33, axis=(0, 2))
    #         tercsup = np.nanpercentile(data_excl_i, 66.66, axis=(0, 2))
    #         mediahcst = np.nanmean(data_excl_i, axis=(0, 2))

    #         # Seleciona o ano retirado (validação cruzada)
    #         hcst = hcst_total[i, ...]  # shape (8,20,72,144)

    #         # Máscaras booleanas
    #         below_mask = hcst <= tercinf[:, None, :, :]
    #         above_mask = hcst >= tercsup[:, None, :, :]
    #         below_mean_mask = hcst <= mediahcst[:, None, :, :]

    #         # Cálculo das probabilidades 
    #         prob_below_i = np.sum(below_mask, axis=1) / n_members
    #         prob_above_i = np.sum(above_mask, axis=1) / n_members
    #         prob_below_mean_i = np.sum(below_mean_mask, axis=1) / n_members
            
    #         return prob_below_i, prob_above_i, prob_below_mean_i

    #     hindcast = Hindcast(path_fcst, path_hcst) 
    #     hcst = hindcast.climatology_model_hcst_members(base, month_fcst, model, var)

    #     hcst_total_members = hindcast.dict_to_array_members(base, hcst, 
    #                         ["mnth00","mnth01","mnth02","mnth03","mnth04","seas00","seas01","seas02"]
    #                         ,var,model)      

    #     n_years = hcst_total_members.shape[0]

    #     results = Parallel(n_jobs=3, backend="loky", verbose=0)(
    #         delayed(process_year)(i, hcst_total_members) for i in range(n_years))

    #     #Reconstrói resultados
    #     prob_below_inf = np.stack([r[0] for r in results], axis=0)
    #     prob_above_sup = np.stack([r[1] for r in results], axis=0)
    #     prob_below_mean = np.stack([r[2] for r in results], axis=0)

    #     return (prob_below_inf, prob_above_sup, prob_below_mean)

    @staticmethod
    def nocalibration_model(base, month_fcst, model, var, year_fcst, path_fcst, path_hcst):

        def process_year(i, hcst_total):
            n_members = hcst_total.shape[2]

            mask_years = np.ones(hcst_total.shape[0], dtype=bool)
            mask_years[i] = False
            data_excl_i = hcst_total[mask_years]

            tercinf = np.nanpercentile(data_excl_i, 33.33, axis=(0, 2))
            tercsup = np.nanpercentile(data_excl_i, 66.66, axis=(0, 2))
            mediahcst = np.nanmean(data_excl_i, axis=(0, 2))

            hcst = hcst_total[i]

            below_mask = hcst <= tercinf[:, None, :, :]
            above_mask = hcst >= tercsup[:, None, :, :]
            below_mean_mask = hcst <= mediahcst[:, None, :, :]

            prob_below_i = np.sum(below_mask, axis=1) / n_members
            prob_above_i = np.sum(above_mask, axis=1) / n_members
            prob_below_mean_i = np.sum(below_mean_mask, axis=1) / n_members

            return prob_below_i, prob_above_i, prob_below_mean_i

        # =========================
        # CARREGA DADOS
        # =========================
        hindcast = Hindcast(path_fcst, path_hcst)
        hcst = hindcast.climatology_model_hcst_members(base, month_fcst, model, var)

        hcst_total_members = hindcast.dict_to_array_members(
            base, hcst,
            ["mnth00","mnth01","mnth02","mnth03","mnth04","seas00","seas01","seas02"],
            var, model
        )

        n_years = hcst_total_members.shape[0]

        total_sum = np.nansum(hcst_total_members, axis=(0, 2))      # (8, 72, 144)
        total_count = np.sum(~np.isnan(hcst_total_members), axis=(0, 2))

        # =================
        # LOOP (paralelo)
        # ================
        results = Parallel(n_jobs=3, backend="loky", verbose=0)(
            delayed(process_year)(i, hcst_total_members)
            for i in range(n_years)
        )

        # =========================
        # RECONSTRUÇÃO
        # =========================
        prob_below_inf = np.stack([r[0] for r in results], axis=0)
        prob_above_sup = np.stack([r[1] for r in results], axis=0)
        prob_below_mean = np.stack([r[2] for r in results], axis=0)

        return prob_below_inf, prob_above_sup, prob_below_mean


    @staticmethod
    def write_netcdf_model_calibrated(
        base, year_fcst, month_fcst, model, variable, 
        type_calibration, cor_skill, prob_med, prob_tinf, 
        prob_tsup, binobs_med, binobs_tinf, binobs_tsup, 
        aroc_med, aroc_tinf, aroc_tsup, msss_skill, msss_fase, 
        msss_amplitude, bias):

        """ Escreve arquivos NetCDF para previsão calibrada 
        pelo método da regressão e o método COX. """

        period_dates = Calibration.compute_period_names(year_fcst, month_fcst) 
        month = f"{month_fcst:02d}"
        fcst_date = f"{year_fcst}{month}0100"
        obs = xr.open_dataset("/dados/mmclima/multimodelo/seasonal/obs/gpcp/obs_gpcp_pr_mon_mean_1979-2025.nc")
        lat_obs = obs["lat"].values
        lon_obs = obs["lon"].values

        if base == "nmme":
            time = range(30) #1991-2020
        elif base == "copernicus":
            time = range(24) #1993-2016    

        varis = ["corskill","probmed","probtinf","probtsup",
                "binobsmed","binobstinf","binobstsup",
                "arocmed","aroctinf","aroctsup", "mssskill", 
                "msssfase", "msssamplitude", "bias"] 

        version_multimodel = ConfigModelos.get_multimodel_version(base)

        #Define o nome do diretório dos modelos
        if base == "nmme":
            name_model_dir = model
        elif base == "copernicus":
            if model == "multimodel":
                name_model_dir = "multimodel"
            else:
                name_model_dir = ConfigModelos.get_model_dir(model)   

        nc_path =  (f"/dados/mmclima/multimodelo/seasonal/posproc/{base}/"
            f"{version_multimodel}/verification/{type_calibration}/{name_model_dir}/")                   

        if not os.path.exists(nc_path):
            os.makedirs(nc_path)

        periods = {
            0: 'mnth00', 1: 'mnth01', 2: 'mnth02', 3: 'mnth03', 4: 'mnth04', 
            5: 'seas00', 6: 'seas01', 7: 'seas02'
        }
        
        for period in range(cor_skill.shape[0]):
            name_period = periods.get(period, f"period{period}")
            forecast_date = period_dates[name_period]
            print("Issued:", period_dates['mnth00'], "For:", forecast_date)
            
            for var_name in varis:
                file_path = f"{nc_path}{variable}_{var_name}_{name_period}_{name_model_dir}_calibrated_{type_calibration}_{fcst_date}.nc"
                print(type_calibration)
                print(file_path)

                with nc.Dataset(file_path, format='NETCDF3_CLASSIC', mode='w') as ds:
                    # Criação das dimensões
                    ds.createDimension('lat', 72)
                    ds.createDimension('lon', 144)

                    is_3d = var_name not in ["corskill", "cortotal", "arocmed", "aroctinf", "aroctsup", "mssskill", "msssfase", "msssamplitude", "bias"]
                    if is_3d:
                        ds.createDimension('time', len(time))

                    #Coordenadas
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

                    # Criação da variável principal
                    dims = ('lat', 'lon') if not is_3d else ('time', 'lat', 'lon')
                    var = ds.createVariable(var_name, 'f8', dims, fill_value=-999.99)
                    var.long_name = f"{var_name} forecast"

                    # Mapeamento de dados
                    data_dict = { 
                        "corskill": cor_skill[period, ...],
                        "cortotal": cor_skill[period, ...],
                        "probmed": prob_med[:, period, ...],
                        "probtinf": prob_tinf[:, period, ...],
                        "probtsup": prob_tsup[:, period, ...],
                        "binobsmed": binobs_med[:, period, ...],
                        "binobstinf": binobs_tinf[:, period, ...],
                        "binobstsup": binobs_tsup[:, period, ...],
                        "arocmed": aroc_med[period, ...],
                        "aroctinf": aroc_tinf[period, ...],
                        "aroctsup": aroc_tsup[period, ...],
                        "mssskill": msss_skill[period, ...],          
                        "msssfase": msss_fase[period, ...],     
                        "msssamplitude": msss_amplitude[period, ...],  
                        "bias": bias[period, ...],                                         
                    }

                    data_to_write = data_dict.get(var_name)
                    var[...] = data_to_write   

                    # Atributos globais
                    ds.description = f"{var_name} of {variable} anomaly calibrated by regression - period {name_period}"
                    ds.history = f"Issued: {period_dates['mnth00']} For: {forecast_date}"
                    ds.source = f"{name_model_dir} calibrated forecast - Regression"
 
    @staticmethod
    def write_netcdf_model_nocalibrated(base, year_fcst, month_fcst, model, variable, 
        cor_skill, prob_med, prob_tinf, 
        prob_tsup, binobs_med, binobs_tinf, binobs_tsup, 
        aroc_med, aroc_tinf, aroc_tsup, msss_skill, msss_fase, 
        msss_amplitude, bias):

        """Escreve arquivos NetCDF para previsão não calibrada, compatíveis com o GrADS."""
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

        varis = ["corskill","probmed","probtinf","probtsup",
                "binobsmed","binobstinf","binobstsup",
                "arocmed","aroctinf","aroctsup", "mssskill", 
                "msssfase", "msssamplitude", "bias"] 

        version_multimodel = ConfigModelos.get_multimodel_version(base)

        #Define o nome do diretório dos modelos
        if base == "nmme":
            name_model_dir = model
        elif base == "copernicus":
            if model == "multimodel":
                name_model_dir = "multimodel"
            else:
                name_model_dir = ConfigModelos.get_model_dir(model)   

        nc_path =  (f"/dados/mmclima/multimodelo/seasonal/posproc/{base}/"
            f"{version_multimodel}/verification/nocalib/{name_model_dir}/")     
        
        print(nc_path)

        if not os.path.exists(nc_path):
            os.makedirs(nc_path)
        
        periods = {
            0: 'mnth00', 1: 'mnth01', 2: 'mnth02', 3: 'mnth03', 4: 'mnth04', 
            5: 'seas00', 6: 'seas01', 7: 'seas02'
        }
        
        for period in range(cor_skill.shape[0]):
            name_period = periods.get(period, f"period{period}")
            forecast_date = period_dates[name_period]
            print("Issued:", period_dates['mnth00'], "For:", forecast_date)
            
            for var_name in varis:
                file_path = f"{nc_path}{variable}_{var_name}_{name_period}_{name_model_dir}_nocalib_{fcst_date}.nc"
                
                with nc.Dataset(file_path, format='NETCDF3_CLASSIC', mode='w') as ds:
                    # Dimensões
                    ds.createDimension('lat', 72)
                    ds.createDimension('lon', 144)
                    is_3d = var_name not in ["corskill", "cortotal", "arocmed", "aroctinf", "aroctsup", "mssskill", "msssfase", "msssamplitude", "bias"]
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
                    # Criação da variável principal
                    dims = ('lat', 'lon') if not is_3d else ('time', 'lat', 'lon')
                    var = ds.createVariable(var_name, 'f8', dims, fill_value=-999.99)
                    var.long_name = f"{var_name} forecast"

                    if variable == "prec":
                        var.units = "mm" if var_name != "prob" else "%"
                    elif variable == "t2mt":
                        var.units = "°C" if var_name != "prob" else "%"     

                    data_dict = { 
                        "corskill": cor_skill[period, ...],
                        "cortotal": cor_skill[period, ...],
                        "probmed": prob_med[:, period, ...],
                        "probtinf": prob_tinf[:, period, ...],
                        "probtsup": prob_tsup[:, period, ...],
                        "binobsmed": binobs_med[:, period, ...],
                        "binobstinf": binobs_tinf[:, period, ...],
                        "binobstsup": binobs_tsup[:, period, ...],
                        "hcstanomaly": hcst_anomaly[:, period, ...],
                        "obsanomaly": obs_anomaly[:, period, ...],                        
                        "arocmed": aroc_med[period, ...],
                        "aroctinf": aroc_tinf[period, ...],
                        "aroctsup": aroc_tsup[period, ...],
                        "mssskill": msss_skill[period, ...],          
                        "msssfase": msss_fase[period, ...],     
                        "msssamplitude": msss_amplitude[period, ...],  
                        "bias": bias[period, ...],                                         
                    }

                    data_to_write = data_dict.get(var_name)
                    var[...] = data_to_write               
                        
                    # Atributos globais
                    ds.description = f"{var_name} of {variable} anomaly calibrated by regression - period {name_period}"
                    ds.history = f"Issued: {period_dates['mnth00']} For: {forecast_date}"
                    ds.source = f"{name_model_dir} calibrated forecast - Regression"
  

    @staticmethod
    def write_netcdf_model_artigo(base, year_fcst, month_fcst, model, variable,
        type_calibration,cor_skill,sig_corskill, prob_mean=None, prob_tinf=None,prob_tsup=None,binobs_tinf=None,
        binobs_tsup=None, bionbs_mean=None, rocss_tinf=None,rocss_tsup=None, sig_aroctinf=None, sig_aroctsup=None):

        # --------------------------------------------------
        # Datas e coordenadas
        # --------------------------------------------------
        period_dates = Calibration.compute_period_names(year_fcst, month_fcst)
        month = f"{month_fcst:02d}"
        fcst_date = f"{year_fcst}{month}0100"

        obs = xr.open_dataset(
            "/dados/mmclima/multimodelo/seasonal/obs/gpcp/obs_gpcp_pr_mon_mean_1979-2025.nc"
        )
        #lat_obs = obs["lat"].values[::-1]
        lat_obs = obs["lat"]
        lon_obs = obs["lon"].values
        print(lat_obs)
        if base == "nmme":
            time = range(30)  # 1991–2020
        elif base == "copernicus":
            time = range(24)  # 1993–2016

        # --------------------------------------------------
        # Definição das variáveis a escrever
        # --------------------------------------------------
        if type_calibration == "nocalib":
            varis = ["corskill","sigcorskill"]
        else:
            varis = [
                "corskill", "sigcorskill",
                "probtinf", "probtsup",
                "binobstinf", "binobstsup",
                "probmean", "bionbsmean",
                "rocsstinf", "rocsstsup",
                "sigaroctinf", "sigaroctsup"
            ]

        # --------------------------------------------------
        # Nome do modelo
        # --------------------------------------------------
        if base == "nmme":
            name_model_dir = model
        elif base == "copernicus":
            name_model_dir = (
                "multimodel" if model == "multimodel"
                else ConfigModelos.get_model_dir(model)
            )

        nc_path = "/dados/mmclima/multimodelo/artigo/dados/"
        os.makedirs(nc_path, exist_ok=True)

        periods = {
            0: 'mnth00', 1: 'mnth01', 2: 'mnth02', 3: 'mnth03',
            4: 'mnth04', 5: 'seas00', 6: 'seas01', 7: 'seas02'
        }

        for period in range(cor_skill.shape[0]):

            name_period = periods.get(period, f"period{period}")
            forecast_date = period_dates[name_period]

            print("Issued:", period_dates['mnth00'], "For:", forecast_date)

            # -----------------------------
            # Dicionário de dados
            # -----------------------------
            data_dict = {
                "corskill": cor_skill[period, ...],
                "sigcorskill": sig_corskill[period, ...]           
            }

            if type_calibration != "nocalib":
                data_dict.update({
                    "probmean": prob_mean[:, period, ...],
                    "probtinf": prob_tinf[:, period, ...],
                    "probtsup": prob_tsup[:, period, ...],
                    "binobstinf": binobs_tinf[:, period, ...],
                    "binobstsup": binobs_tsup[:, period, ...],
                    "bionbsmean": bionbs_mean[:, period, ...],                    
                    "rocsstinf": rocss_tinf[period, ...],
                    "rocsstsup": rocss_tsup[period, ...],
                    "sigaroctinf": sig_aroctinf[period, ...],
                    "sigaroctsup": sig_aroctsup[period, ...],          
                })

            # -----------------------------
            # Escrita NetCDF por variável
            # -----------------------------
            for var_name in varis:

                file_path = (
                    f"{nc_path}{variable}_{var_name}_{name_period}_"
                    f"{name_model_dir}_calibrated_{type_calibration}_{fcst_date}.nc"
                )

                print("Writing:", file_path)

                with nc.Dataset(file_path, format='NETCDF3_CLASSIC', mode='w') as ds:

                    # Dimensões
                    ds.createDimension('lat', len(lat_obs))
                    ds.createDimension('lon', len(lon_obs))

                    is_3d = var_name in [
                        "probtinf", "probtsup", "probmean",
                        "binobstinf", "binobstsup", "bionbsmean"
                    ]

                    if is_3d:
                        ds.createDimension('time', len(time))
                        dims = ('time', 'lat', 'lon')
                    else:
                        dims = ('lat', 'lon')

                    # Coordenadas
                    lat_var = ds.createVariable('lat', 'f8', ('lat',))
                    lon_var = ds.createVariable('lon', 'f8', ('lon',))
                    lat_var[:] = lat_obs
                    lon_var[:] = lon_obs
                    lat_var.units = "degrees_north"
                    lon_var.units = "degrees_east"

                    if is_3d:
                        time_var = ds.createVariable('time', 'i4', ('time',))
                        time_var[:] = list(time)
                        time_var.units = "years"

                    # Variável principal
                    var = ds.createVariable(
                        var_name, 'f8', dims, fill_value=-999.99
                    )
                    var.long_name = f"{var_name} forecast"

                    field = data_dict[var_name]

                    # -------------------------
                    # Inverter eixo latitude
                    # -------------------------

                    if field.ndim == 2:
                        # (lat, lon)
                        field = field[::-1, :]

                    elif field.ndim == 3:
                        # (time, lat, lon)
                        field = field[:, ::-1, :]

                    #var[...] = field
                    var[...] = data_dict[var_name]
                    print(var.shape)

                    # Atributos globais
                    ds.description = (
                        f"{var_name} of {variable} anomaly "
                        f"calibrated by {type_calibration} - period {name_period}"
                    )
                    ds.history = (
                        f"Issued: {period_dates['mnth00']} "
                        f"For: {forecast_date}"
                    )
                    ds.source = (
                        f"{name_model_dir} calibrated forecast - {type_calibration}"
                    )

# ############
# #DIRETÓRIOS#
# ############
# path_hcst = "/dados/mmclima/multimodelo/seasonal/hindcast"
# path_fcst = "/dados/mmclima/multimodelo/seasonal/forecast"
# path_obs = "/dados/mmclima/multimodelo/seasonal/obs"

#inicio = time.time()  # <<< Início da contagem

# bases = ["nmme"]
# models_nmme = ["multimodel","canesm5", "ccsm4", "cesm1", "cfsv2", "gem52nemo", "geos5v2", "spear","bam12"]#
# models_cs3 = ["multimodel","ecmwf", "ukmo","meteo_france","dwd","cmcc","ncep","jma","eccc4","eccc5","bom","bam12"] 
# varis = ["prec","t2mt"]#"prec","t2mt"
# type_calibrations = ["nocalib"]#"regr","gamma","nocalib","cox"
# #months = [2]
# months = list(range(1, 13))
# year_fcst = 2026

# ####################
# # --- Hindcast --- #
# ####################
# for base in bases:
    
#     print(base)
#     if base == "nmme":
#         models = ["multimodel","canesm5", "ccsm4", "cesm1", "cfsv2", "gem52nemo", "geos5v2", "spear","bam12"]
#     elif base == "copernicus":
#         models = ["multimodel","ecmwf", "ukmo","meteo_france","dwd","cmcc","ncep","jma","eccc4","eccc5","bom","bam12"] 


# for var in varis:
#     for type_calibration in type_calibrations:
#         for model in models:
#             for month_fcst in months:
#                 print(type_calibration)
#                 print(month_fcst)  
#                 print(model)
#                 print(var)
                
#                 if type_calibration == "regr": 
#                     #Gera a previsão calibrada (método da Regressão)
#                     (obs_anomaly, obs_total, fcst_calib_anomaly, fcst_calib_mean, prob_below_mean, prob_below_inf, 
#                     prob_above_sup, binobsmed, binobsinf, binobssup) = Calibration.regression_calibration_model(path_fcst, path_hcst, path_obs, base, year_fcst, month_fcst, model, var)

#                     #Area sob a curva ROC
#                     auroc_below_mean = Calibration.area_roc(binobsmed, prob_below_mean)
#                     auroc_below_inf = Calibration.area_roc(binobsinf, prob_below_inf)
#                     auroc_above_sup = Calibration.area_roc(binobssup, prob_above_sup)

#                     #Correlação
#                     cor_anom_verif = Calibration.corr_verif(obs_anomaly, fcst_calib_anomaly)

#                     #Índice de destreza do Erro Quadrático Médio e Fase/Amplitude
#                     msss_skill = Calibration.msss_skill(fcst_calib_anomaly, obs_anomaly)
#                     bias = Calibration.compute_bias(fcst_calib_mean, obs_total)
#                     msss_fase, msss_amplitude = Calibration.msss_fase_amplitude(fcst_calib_anomaly, obs_anomaly)

#                     Calibration.write_netcdf_model_calibrated(base, year_fcst, month_fcst, model,
#                     var, type_calibration, cor_anom_verif, prob_below_mean, prob_below_inf, 
#                     prob_above_sup, binobsmed, binobsinf, binobssup, auroc_below_mean, auroc_below_inf, auroc_above_sup,
#                     msss_skill, msss_fase, msss_amplitude, bias)

#                 elif type_calibration == "cox":
#                     #Gera a previsão calibrada (método COX)
#                     (obs_anomaly, obs_total, mediana_fcst_cox, anomalia_fcst_cox, probexc_mediana, prob_below_inf, 
#                     prob_above_sup, binobsmediana, binobsinf, binobssup) = Calibration.calibration_cox_model(path_fcst, path_hcst, path_obs, base, year_fcst, month_fcst, model, var)

#                     #Area sob a curva ROC
#                     auroc_below_mean = Calibration.area_roc(binobsmediana, probexc_mediana)
#                     auroc_below_inf = Calibration.area_roc(binobsinf, prob_below_inf)
#                     auroc_above_sup = Calibration.area_roc(binobssup, prob_above_sup)

#                     #Correlação
#                     cor_anom_verif = Calibration.corr_verif(obs_anomaly, anomalia_fcst_cox)
#                     #cor_total_verif = Calibration.corr_verif(obs_total, mediana_fcst_cox)

#                     #Índice de destreza do Erro Quadrático Médio e Fase/Amplitude
#                     msss_skill = Calibration.msss_skill(anomalia_fcst_cox, obs_anomaly)
#                     bias = Calibration.compute_bias(mediana_fcst_cox, obs_total)
#                     msss_fase, msss_amplitude = Calibration.msss_fase_amplitude(anomalia_fcst_cox, obs_anomaly)

#                     Calibration.write_netcdf_model_calibrated(base, year_fcst, month_fcst, model,
#                     var, type_calibration, cor_anom_verif, probexc_mediana, prob_below_inf, 
#                     prob_above_sup, binobsmediana, binobsinf, binobssup, auroc_below_mean, auroc_below_inf, auroc_above_sup,
#                     msss_skill, msss_fase, msss_amplitude, bias)

#                 elif type_calibration == "nocalib":

#                     #OBSERVATION
#                     obs = Observation(path_obs)
#                     statistcs = obs.mean_std_anom_obs(base, month_fcst, var) 
#                     anom = {k: v['anomaly'] for k, v in statistcs.items() if 'anomaly' in v}
#                     std = {k: v['std'] for k, v in statistcs.items() if 'std' in v}
#                     mean = {k: v['mean'] for k, v in statistcs.items() if 'mean' in v} 
#                     mediana =  {k: v['mediana'] for k, v in statistcs.items() if 'mediana' in v}   
#                     tercil_inf = {k: v['tercilinf'] for k, v in statistcs.items() if 'tercilinf' in v}    
#                     tercil_sup = {k: v['tercilsup'] for k, v in statistcs.items() if 'tercilsup' in v}   
#                     total = {k: v['total'] for k, v in statistcs.items() if 'total' in v}   

#                     #Transformar em array
#                     ordered_periods = list(anom.keys()) 
#                     obs_series = np.stack([obs.calculate_obs_periods(base, month_fcst, var)[p] for p in ordered_periods], axis=0)
#                     obs_total = np.stack([total[p] for p in ordered_periods], axis=1)
#                     obs_anomaly = np.stack([anom[p] for p in ordered_periods], axis=1)
#                     obs_std = np.stack([std[p] for p in ordered_periods], axis=1)
#                     obs_mean = np.stack([mean[p] for p in ordered_periods], axis=1)
#                     obs_mediana = np.stack([mediana[p] for p in ordered_periods], axis=1)        
#                     obs_tercinf = np.stack([tercil_inf[p] for p in ordered_periods], axis=1)
#                     obs_tercsup = np.stack([tercil_sup[p] for p in ordered_periods], axis=1)    
    
#                     # --- Binários ---
#                     binobsinf = (obs_total <= obs_tercinf).astype(int)
#                     binobssup = (obs_total >= obs_tercsup).astype(int)
#                     binobsmed = (obs_total <= obs_mean).astype(int)

#                     #VERIFICAÇÃO NÃO-CALIBRADA MULTIMODELO
#                     if model == "multimodel":

#                         if base == "nmme":
#                             models_all = ["canesm5", "ccsm4","cesm1", "cfsv2", "gem52nemo", "geos5v2", "spear", "bam12"] #
#                         if base == "copernicus":
#                             models_all = ["ecmwf", "ukmo","meteo_france","dwd","cmcc","ncep","jma","eccc4","eccc5","bom","bam12"]
                        
#                         models_available = models_all

#                         # model_names = [model if base == "nmme" else ConfigModelos.get_model_dir(model)
#                         # for model in models_available]

#                         prob_tinf_results, prob_tsup_results, prob_mean_results = [], [], []

#                         for mdl in models_available:    
#                             print(f"Cálculo Prob. Multimodelo - processando: {mdl}")
#                             name_model = mdl if base == "nmme" else ConfigModelos.get_model_dir(mdl)
#                             (prob_below_inf, prob_above_sup, 
#                             prob_below_mean) = Calibration.nocalibration_model(base, month_fcst, mdl, 
#                                                                 var, year_fcst, path_fcst, path_hcst)
#                             prob_tinf_results.append(prob_below_inf)
#                             prob_tsup_results.append(prob_above_sup)
#                             prob_mean_results.append(prob_below_mean)

#                         # Média multi-modelo das probabilidades 
#                         multimodel_ptinf = np.nanmean(prob_tinf_results, axis=0)
#                         multimodel_ptsup = np.nanmean(prob_tsup_results, axis=0)
#                         multimodel_pmean = np.nanmean(prob_mean_results, axis=0)                                                                                                           
                        
#                         hindcast = Hindcast(path_fcst, path_hcst) 
#                         hcst_total_ensmean, _, _, hcst_anomaly = hindcast.mean_std_anom_hindcast(base, 
#                                                                     year_fcst, month_fcst, model, var)     

#                         #Correlações e índices de destreza
#                         cor_anom_verif = Calibration.corr_verif(obs_anomaly, hcst_anomaly)
#                         auroc_below_mean = Calibration.area_roc(binobsmed, multimodel_pmean)
#                         auroc_below_inf = Calibration.area_roc(binobsinf, multimodel_ptinf)
#                         auroc_above_sup = Calibration.area_roc(binobssup, multimodel_ptsup)
#                         msss_skill = Calibration.msss_skill(hcst_anomaly, obs_anomaly)
#                         bias = Calibration.compute_bias(hcst_total_ensmean, obs_total)
#                         msss_fase, msss_amplitude = Calibration.msss_fase_amplitude(hcst_anomaly, obs_anomaly)

#                         #Escrever os arquivos NetCDF
#                         Calibration.write_netcdf_model_nocalibrated(base, year_fcst, month_fcst, model,
#                         var, cor_anom_verif, prob_below_mean, prob_below_inf, prob_above_sup,
#                         binobsmed, binobsinf, binobssup, auroc_below_mean, auroc_below_inf, auroc_above_sup,
#                         msss_skill, msss_fase, msss_amplitude, bias)

#                     #VERIFICAÇÃO NÃO-CALIBRADA MODELOS SEPARADOS
#                     else:
#                         name_model = model if base == "nmme" else ConfigModelos.get_model_dir(model)

#                         (prob_below_inf, prob_above_sup, 
#                         prob_below_mean) = Calibration.nocalibration_model(base, month_fcst, model, 
#                                                                 var, year_fcst, path_fcst, path_hcst)

#                         hindcast = Hindcast(path_fcst, path_hcst) 
#                         hcst_total_ensmean, _, _, hcst_anomaly = hindcast.mean_std_anom_hindcast(base, 
#                                                                     year_fcst, month_fcst, model, var)     

#                         #Correlações e índices de destreza
#                         cor_anom_verif = Calibration.corr_verif(obs_anomaly, hcst_anomaly)
#                         auroc_below_mean = Calibration.area_roc(binobsmed, prob_below_mean)
#                         auroc_below_inf = Calibration.area_roc(binobsinf, prob_below_inf)
#                         auroc_above_sup = Calibration.area_roc(binobssup, prob_above_sup)
#                         msss_skill = Calibration.msss_skill(hcst_anomaly, obs_anomaly)
#                         bias = Calibration.compute_bias(hcst_total_ensmean, obs_total)
#                         msss_fase, msss_amplitude = Calibration.msss_fase_amplitude(hcst_anomaly, obs_anomaly)

#                         #Escrever os arquivos NetCDF
#                         Calibration.write_netcdf_model_nocalibrated(base, year_fcst, month_fcst, model,
#                         var, cor_anom_verif, prob_below_mean, prob_below_inf, prob_above_sup,
#                         binobsmed, binobsinf, binobssup, auroc_below_mean, auroc_below_inf, auroc_above_sup,
#                         msss_skill, msss_fase, msss_amplitude, bias)

#########
# ARTIGO#
#########
#     for var in varis:
#         for type_calibration in type_calibrations:
#             for model in models:
#                 for month_fcst in months:
#                     print(type_calibration)
#                     print(month_fcst)  
#                     print(model)
#                     print(var)
#                     if type_calibration == "regr": 
#                         #Gera a previsão calibrada (método da Regressão)
#                         (obs_anomaly, obs_total, fcst_calib_anomaly, fcst_calib_mean, prob_below_mean, prob_below_inf, 
#                         prob_above_sup, binobsmed, binobsinf, binobssup) = Calibration.regression_calibration_model(path_fcst, path_hcst, path_obs, base, year_fcst, month_fcst, model, var)

#                         #Area sob a curva ROC
#                         auroc_below_inf, _, sig_aroctinf = Calibration.area_roc_with_pvalue(binobsinf, prob_below_inf)
#                         auroc_above_sup, _, sig_aroctsup = Calibration.area_roc_with_pvalue(binobssup, prob_above_sup)

#                         #ROC Skill Score
#                         rocss_below_inf = 2 * auroc_below_inf - 1
#                         rocss_above_sup = 2 * auroc_above_sup - 1

#                         #Correlação
#                         cor_total_verif, _, sig_cortotal = Calibration.corr_verif_with_pvalue(obs_anomaly, fcst_calib_anomaly)

#                         Calibration.write_netcdf_model_artigo(base, year_fcst, month_fcst, model, var, 
#                         type_calibration, cor_total_verif, sig_cortotal, prob_below_mean, prob_below_inf, prob_above_sup, binobsinf, binobssup, binobsmed, 
#                         auroc_below_inf, auroc_above_sup, sig_aroctinf, sig_aroctsup)                       

#                     elif type_calibration == "cox":
#                         #Gera a previsão calibrada (método COX)
#                         (obs_anomaly, obs_total, mediana_fcst_cox, anomalia_fcst_cox, prob_below_mediana, prob_below_inf, 
#                         prob_above_sup, binobsmediana, binobsinf, binobssup) = Calibration.calibration_cox_model(path_fcst, path_hcst, path_obs, base, year_fcst, month_fcst, model, var)

#                         #Area sob a curva ROC
#                         auroc_below_inf, _, sig_aroctinf = Calibration.area_roc_with_pvalue(binobsinf, prob_below_inf)
#                         auroc_above_sup, _, sig_aroctsup = Calibration.area_roc_with_pvalue(binobssup, prob_above_sup)

#                         #ROC Skill Score
#                         rocss_below_inf = 2 * auroc_below_inf - 1
#                         rocss_above_sup = 2 * auroc_above_sup - 1

#                         #Correlação
#                         cor_total_verif, _, sig_cortotal = Calibration.corr_verif_with_pvalue(obs_anomaly, anomalia_fcst_cox)

#                         Calibration.write_netcdf_model_artigo(base, year_fcst, month_fcst, model, var, 
#                         type_calibration, cor_total_verif, sig_cortotal, prob_below_mediana, prob_below_inf, prob_above_sup, binobsinf, binobssup, binobsmediana, 
#                         auroc_below_inf, auroc_above_sup, sig_aroctinf, sig_aroctsup)        

#                     if type_calibration == "gamma":
#                         (obs_total, obs_anomaly, fcst_calib_anomaly, fcst_calib_mean, fcst_alpha, fcst_beta, prob_below_inf, 
#                         prob_above_sup, prob_below_mean, binobsinf, binobssup, binobsmed) = Calibration.gamma_calibration_model(path_fcst, path_hcst, path_obs, base, year_fcst, month_fcst, model, var)

#                         #Area sob a curva ROC
#                         auroc_below_inf, _, sig_aroctinf = Calibration.area_roc_with_pvalue(binobsinf, prob_below_inf)
#                         auroc_above_sup, _, sig_aroctsup = Calibration.area_roc_with_pvalue(binobssup, prob_above_sup)

#                         #ROC Skill Score
#                         rocss_below_inf = 2 * auroc_below_inf - 1
#                         rocss_above_sup = 2 * auroc_above_sup - 1

#                         #Correlação
#                         cor_total_verif, _, sig_cortotal = Calibration.corr_verif_with_pvalue(obs_anomaly, fcst_calib_anomaly)

#                         Calibration.write_netcdf_model_artigo(base, year_fcst, month_fcst, model, var, 
#                         type_calibration, cor_total_verif, sig_cortotal, prob_below_mean, prob_below_inf, prob_above_sup, binobsinf, binobssup, binobsmed, 
#                         auroc_below_inf, auroc_above_sup, sig_aroctinf, sig_aroctsup)       

#                     if type_calibration == "nocalib":
#                         obs = Observation(path_obs)
#                         statistcs = obs.mean_std_anom_obs_gamma(base, month_fcst, var)   
#                         total = {k: v['total'] for k, v in statistcs.items() if 'total' in v}   
#                         anom = {k: v['anomaly'] for k, v in statistcs.items() if 'anomaly' in v}
#                         mean = {k: v['mean'] for k, v in statistcs.items() if 'mean' in v} 
#                         #transformar em array
#                         ordered_periods = list(anom.keys()) 
#                         obs_total = np.stack([total[p] for p in ordered_periods], axis=1)
#                         obs_mean = np.stack([mean[p] for p in ordered_periods], axis=1)
#                         obs_anomaly = np.stack([anom[p] for p in ordered_periods], axis=1)                        
#                         #
#                         hindcast = Hindcast(path_fcst, path_hcst)
#                         hcst_total, hcst_mean, hcst_std, hcst_var, hcst_anomaly = hindcast.mean_std_anom_hindcast_gamma(base, year_fcst, month_fcst, model, var)     
#                         cor_total_verif, _, sig_cortotal = Calibration.corr_verif_with_pvalue(obs_anomaly, hcst_anomaly)

#                         Calibration.write_netcdf_model_artigo(base, year_fcst, month_fcst, model, var, 
#                         type_calibration, cor_total_verif, sig_cortotal)  


# fim = time.time()  # <<< Fim da contagem
# print(f"Tempo total: {(fim - inicio)/60:.2f} minutos")

# ##################################################
# #DOWNLOAD DADOS DA PREVISÃO seasonal EM TEMPO-REAL#
# ##################################################
# model = "multimodel"
# type_calibration = "regression"
# base = "nmme"
# year_fcst = 2025
# month_fcst = 6


# # {"ecmwf": "51",
# #             "ukmo": "604",
# #             "meteo_france": "9", #8 antigo
# #             "dwd": "22",
# #             "cmcc": "35",
# #             "ncep": "2",
# #             "jma": "3",
# #             "eccc4": "4",
# #             "eccc5": "5",
# #             "bom": "2"}

# # if base == "nmme":
# #     vars_nmme = ["prec", "tref"]
# #     models_nmme = ["canesm5", "ccsm4", "cesm1", "cfsv2", "gem52nemo", "geos5v2", "spear"]
# #     for model in models_nmme:
# #         for var in vars_nmme:
# #             download_realtime_nmme(year_fcst, month_fcst, model, var)
# # else:
# #     vars_copernicus = ["total_precipitation", "2m_temperature"]
# #     models_copernicus = ["ecmwf","ukmo","meteo_france","dwd","cmcc","ncep","jma","eccc4","eccc5","bom"]
# #     for model in models_copernicus:
# #         for var in vars_copernicus:
# #             download_realtime_copernicus(year_fcst, month_fcst, model, var)

# # ###################################################
# # #INTERPOLAÇÃO DOS DADOS PARA GRADE DAS OBSERVAÇÕES#
# # ###################################################
# interp_fcst(base, year_fcst, month_fcst)


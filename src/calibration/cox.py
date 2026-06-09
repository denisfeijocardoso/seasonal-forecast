import numpy as np

class CoxCalibration:


    @staticmethod
    def _interpolation_cox(
            vetorx: np.array, 
            prob: np.array, 
            y_alvo: float, 
            alongar: bool = True, 
            inverter: bool = True, 
            verbose: bool = False
    ):
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
    def _probabilidade_cox(
        vetorx: np.array, 
        prob: np.array, 
        x_alvo: float, 
        alongar: bool = True, 
        inverter: bool = True, 
        verbose: bool = False
    ):
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
    
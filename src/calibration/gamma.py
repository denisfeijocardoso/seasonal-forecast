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
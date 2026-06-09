def run_realtime_seasonal(year_fcst, month_fcst, base, var):

    """
    Executa o pipeline completo de processamento das previsões sazonais em tempo real.

    Etapas:
        1. Download dos dados dos modelos a partir das bases NMME e Copernicus.
        2. Interpolação dos dados dos modelos para a mesma grade das observações (GPCP)
        2. Geração das previsões calibradas:
            - Multimodelo
            - Modelos individuais
        3. Geração das figuras (mapas) para publicação no site.

    Parâmetros:
        base (str): Nome da base de dados ("nmme" ou "copernicus").
        year_fcst (str): Ano da previsão (ex: "2026").
        month_fcst (str): Mês da previsão em formato numérico (ex: "4").
    """

    # Formatação da data de inicialização
    month_str = f"{month_fcst:02d}"
    fcst_date = f"{year_fcst}{month_str}0100"

    #========================================================
    #Download das previsões em tempo-real - Copernicus (C3S)
    #========================================================
    if base == "copernicus":
        models = ["ecmwf","ukmo","meteo_france","dwd","cmcc","ncep","jma","eccc4","eccc5","bom"]

        var_download = {"prec": "total_precipitation",
                    "t2mt": "2m_temperature" }

        print("Baixando dados das previsões em tempo-real - Copernicus (C3S)")  
        
        for model in models:    
            download_realtime_copernicus(year_fcst, month_fcst, model, var_download[var])

        print("Baixando dados dos hindcasts faltantes para o mês - Copernicus (C3S)")  
        Run.run_download_hcst_c3s(month_fcst)

        # Interpolação para grade da observação
        print("Interpolando os dados de previsão em tempo-real dos modelos para a mesma grade da observação (GPCP)")  
        interp_fcst("copernicus", year_fcst, month_fcst, var)

    #============================================
    #Download das previsões em tempo-real - NMME
    #============================================
    elif base == "nmme":
        models = ["canesm5", "ccsm4", "cesm1", "cfsv2", "gem52nemo", "geos5v2", "spear"] 

        var_download = {"prec": "prec",
                    "t2mt": "tref" }

        print("Baixando dados das previsões em tempo-real - North American Multi-Model Ensemble (NMME)")  
        
        for model in models:    
            download_realtime_nmme(year_fcst, month_fcst, model, var_download[var])

        #Interpola os arquivos para a grade da observação
        interp_fcst("nmme", year_fcst, month_fcst, var)

    #=====================================================================
    #Geração das previsões calibradas (multimodelo e modelos individuais)
    #=====================================================================
#        inicio = time.time()  # <<< Início da contagem

    # Define modelos base (sem multimodel)
    if base == "nmme":
        models_all = ["canesm5", "ccsm4","cesm1", "cfsv2", "gem52nemo", "geos5v2", "spear","bam12"]
    elif base == "copernicus":
        models_all = ["ecmwf", "ukmo","meteo_france","dwd","cmcc","ncep","jma","eccc4","eccc5","bom","bam12"]

    calibrations = ["cox","regr"]

    #==================
    #Rodar a calibração
    #==================

    # FAZ CHECAGEM DE QUAIS MODELOS ESTÃO DISPONÍVES (CHECA SE OS ARQUIVOS FORAM BAIXADOS)
    models_available = Calibration.check_models(base, path_fcst, year_fcst, month_fcst, var)
    print(f"Modelos disponíveis (forecast): {models_available}")
    models_to_run = ["multimodel"] + models_available

    for model in models_to_run:   

        for calib in calibrations:

            try:
                version_multimodel = ConfigModelos.get_multimodel_version(base)

                # Define o nome do diretório dos modelos
                if base == "nmme":
                    name_model_dir = model
                elif base == "copernicus":
                    if model == "multimodel":
                        name_model_dir = "multimodel"
                    else:
                        name_model_dir = ConfigModelos.get_model_dir_c3s(model)   

                path_fcst_nc = (
                    f"/dados/mmclima/multimodelo/seasonal/posproc/{base}/"
                    f"{version_multimodel}/forecast/{calib}/{name_model_dir}/"
                    f"{year_fcst}/{year_fcst}{month_str}0100/")

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
                        prob_below_sup, prob_above_sup, prob_central_terc, prob_tercile, corr, alpha_obs, beta_obs, 
                        p_hcst, p_obs) = Calibration.gamma_calibration_model(path_fcst, path_hcst, path_obs, base, year_fcst, month_fcst, model, var)
                    
                        Calibration.write_netcdf_gamma(base, year_fcst, month_fcst, model, var, 
                        anom_calib, acum_calib, stdev_calib, alpha, beta, prob_below_inf, prob_above_inf,
                        prob_below_sup, prob_above_sup, prob_central_terc, prob_tercile, corr, alpha_obs, beta_obs,
                        p_hcst, p_obs)

            except ValueError as e:
                print(f"\n[SKIP] {model.upper()} ({var.upper()}) ({calib.upper()}): {e}")
                continue

#        fim = time.time()  # <<< Fim da contagem
#        print(f"Tempo total: {(fim - inicio)/60:.2f} minutos")
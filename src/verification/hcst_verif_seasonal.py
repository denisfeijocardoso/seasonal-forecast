import os
import numpy as np
import pandas as pd
import xarray as xr
import netCDF4
import calendar
from pathlib import Path
from datetime import date, datetime,timedelta
from dateutil.relativedelta import *
from src.config.config_models_seasonal import ConfigModelos
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

#Directories
path_hcst = "/dados/mmclima/multimodelo/seasonal/hindcast"
path_fcst = "/dados/mmclima/multimodelo/seasonal/forecast"

class Hindcast:
    def __init__(self, path_fcst, path_hcst):
        self.path_fcst = path_fcst
        self.path_hcst = path_hcst

    def read_hcst_file(self, base, year_hcst, month_hcst, model, var):
        '''Armazena os dados de cada modelo fornecidos como lista no parâmetro models e para a variável var.
        Exemplo: year,month,day = itera na lista de climatologia '''

        if model == "multimodel":
            name_model = "multimodel"
        else:
            name_model = model if base == "nmme" else ConfigModelos.get_model_dir(model)

        month = f"{month_hcst:02d}"
        month_name = calendar.month_abbr[month_hcst].capitalize() #nome do mês
        hcst_dir = f"{self.path_hcst}/{base}/{name_model}/{year_hcst}/"
        file_name_hcst = os.path.join(hcst_dir, f"{var}_monthly_{name_model}_hcst_interp_{year_hcst}{month}01.nc")
        model_hcst = xr.open_dataset(file_name_hcst, decode_times=False)
        model_hcst = model_hcst.squeeze()
        var_name = list(model_hcst.data_vars)[0]

        #Faz a média do ensemble
        if model == "bam12":
            member_dim = "ens"
        else:
            member_dim = "M" if base == "nmme" else "number"

        model_hcst = model_hcst.mean(dim=member_dim, skipna=True)

        if base == "copernicus" and model != "bam12": #transforma de m/s para mm/dia
            model_hcst[var_name] = (model_hcst[var_name] * 1000  * 86400) if var == "prec" else model_hcst[var_name]

        dataset = model_hcst

        model_hcst.close()

        return dataset

    def read_hcst_file_members(self, base, year_hcst, month_hcst, model, var):
        """
        Igual à read_hcst_file, mas mantém a dimensão dos membros (sem tirar média do ensemble).
        """
        if model == "multimodel":
            name_model = "multimodel"
        else:
            name_model = model if base == "nmme" else ConfigModelos.get_model_dir(model)

        month = f"{month_hcst:02d}"
        month_name = calendar.month_abbr[month_hcst].capitalize()
        hcst_dir = f"{self.path_hcst}/{base}/{name_model}/{year_hcst}/"
        file_name_hcst = os.path.join(hcst_dir, f"{var}_monthly_{name_model}_hcst_interp_{year_hcst}{month}01.nc")

        model_hcst = xr.open_dataset(file_name_hcst, decode_times=False)
        model_hcst = model_hcst.squeeze()
        var_name = list(model_hcst.data_vars)[0]

        # NÃO tira média do ensemble
        # Apenas converte unidades se necessário
        if base == "copernicus" and model != "bam12":  
            model_hcst[var_name] = (model_hcst[var_name] * 1000 * 86400) if var == "prec" else model_hcst[var_name]

        dataset = model_hcst
        model_hcst.close()
        return dataset

    def calculate_hcst_periods(self, base, year_hcst, month_hcst, model, model_hcst, var):
        '''Faz os acumulados ou médias para trimestre 1 e 2; seleciona mes 1, 2, 3 e 4'''
        hcst = {} 

        periods = {
            "mnth00": (0, 1), "mnth01": (1, 2), "mnth02": (2, 3), "mnth03": (3, 4), "mnth04": (4, 5),
            "seas00": (0, 3), "seas01": (1, 4), "seas02": (2, 5)
        }

        for period, (start, end) in periods.items():
            is_mensal = period.startswith("mnth")  # ou: period in ["mon1", "mon2", ...]

            # Se a variável for precipitação, usamos o sum, caso contrário, usamos o mean
            if var == "prec":
                if base == "nmme":
                    if is_mensal:
                        new_date = date(year_hcst, month_hcst, 1) + relativedelta(months=start) #soma um mes
                        ndays = calendar.monthrange(year_hcst, new_date.month)[1]

                        if model == "bam12":
                            sel = model_hcst.isel(time=slice(start, end))
                            var_name = list(sel.data_vars)[0]
                        else:
                            sel = model_hcst.isel(L=slice(start, end))    
                            var_name = list(sel.data_vars)[0]  
                            sel[var_name] = sel[var_name] * ndays

                        hcst[period] = sel[var_name].squeeze()
                    else:
                        if period == "seas00":
                            hcst[period] = (
                                hcst["mnth00"] + hcst["mnth01"] + hcst["mnth02"]
                            )                        
                        elif period == "seas01":
                            hcst[period] = (
                                hcst["mnth01"] + hcst["mnth02"] + hcst["mnth03"]
                            )
                        elif period == "seas02":
                            hcst[period] = (
                                hcst["mnth02"] + hcst["mnth03"] + hcst["mnth04"]
                            )

                elif base == "copernicus": 
                    if is_mensal:
                        new_date = date(year_hcst, month_hcst, 1) + relativedelta(months=start) #soma um mes
                        ndays = calendar.monthrange(year_hcst, new_date.month)[1]   

                        if model == "bam12":
                            sel = model_hcst.isel(time=slice(start, end))
                            var_name = list(sel.data_vars)[0]
                        else:
                            sel = model_hcst.isel(forecastMonth=slice(start, end))      
                            var_name = list(sel.data_vars)[0]
                            sel[var_name] = sel[var_name] * ndays  

                        hcst[period] = sel[var_name].squeeze()
                    else:
                        if period == "seas00":
                            hcst[period] = (
                                 hcst["mnth00"] + hcst["mnth01"] + hcst["mnth02"]
                            )                             
                        elif period == "seas01":
                            hcst[period] = (
                                hcst["mnth01"] + hcst["mnth02"] + hcst["mnth03"]
                            )
                        elif period == "seas02":
                            hcst[period] = (
                                hcst["mnth02"] + hcst["mnth03"] + hcst["mnth04"]
                            )    

            elif var == "t2mt":
                if base == "nmme":
                    if is_mensal:
                        new_date = date(year_hcst, month_hcst, 1) + relativedelta(months=start) #soma um mes
                        ndays = calendar.monthrange(year_hcst, new_date.month)[1]

                        if model == "bam12":
                            sel = model_hcst.isel(time=slice(start, end))
                        else:
                            sel = model_hcst.isel(L=slice(start, end))    

                        var_name = list(sel.data_vars)[0]
                        sel[var_name] = sel[var_name] - 273.15
                        hcst[period] = sel[var_name].squeeze()

                    else:
                        if period == "seas00":
                            hcst[period] = (
                                (hcst["mnth00"] + hcst["mnth01"] + hcst["mnth02"]) / 3
                            )                             
                        elif period == "seas01":
                            hcst[period] = (
                                (hcst["mnth01"] + hcst["mnth02"] + hcst["mnth03"]) / 3
                            )
                        elif period == "seas02":
                            hcst[period] = (
                                (hcst["mnth02"] + hcst["mnth03"] + hcst["mnth04"]) / 3
                            )    

                elif base == "copernicus": 
                    if is_mensal:
                        new_date = date(year_hcst, month_hcst, 1) + relativedelta(months=start) #soma um mes
                        ndays = calendar.monthrange(year_hcst, new_date.month)[1]     

                        if model == "bam12":
                            sel = model_hcst.isel(time=slice(start, end))
                        else:
                            sel = model_hcst.isel(forecastMonth=slice(start, end))

                        var_name = list(sel.data_vars)[0]
                        sel[var_name] = sel[var_name] - 273.15
                        hcst[period] = sel[var_name].squeeze()
                    else:
                        if period == "seas00":
                            hcst[period] = (
                                (hcst["mnth00"] + hcst["mnth01"] + hcst["mnth02"]) / 3
                            )                             
                        elif period == "seas01":
                            hcst[period] = (
                                (hcst["mnth01"] + hcst["mnth02"] + hcst["mnth03"]) / 3
                            )
                        elif period == "seas02":
                            hcst[period] = (
                                (hcst["mnth02"] + hcst["mnth03"] + hcst["mnth04"]) / 3
                            )    

        return hcst


    def climatology_model_hcst(self, base, month_hcst, model, var):
        '''Calcula os acumulados/médias para o periodo de climatologia'''
        if base == "nmme":
            years_hcst = range(1991, 2021)  
        elif base == "copernicus":
            years_hcst = range(1993, 2017)
        #
        hindcast = {}
        for year_hcst in years_hcst:
            model_hcst = self.read_hcst_file(base, year_hcst, month_hcst, model, var)
            hindcast[year_hcst] = self.calculate_hcst_periods(base, year_hcst, month_hcst, model, model_hcst, var)
        return hindcast 

    def climatology_model_hcst_members(self, base, month_hcst, model, var):
        """
        Calcula os acumulados/médias para o período de climatologia
        mas mantém a dimensão dos membros (sem média ensemble).
        """
        if base == "nmme":
            years_hcst = range(1991, 2021)
        elif base == "copernicus":
            years_hcst = range(1993, 2017)

        hindcast = {}
        for year_hcst in years_hcst:
            # Lê arquivo sem tirar média dos membros
            model_hcst = self.read_hcst_file_members(base, year_hcst, month_hcst, model, var)
            # Usa exatamente a mesma lógica para acumulados e médias
            hindcast[year_hcst] = self.calculate_hcst_periods(base, year_hcst, month_hcst, model, model_hcst, var)
        return hindcast

    def dict_to_array(self, base, hindcast, periods, var):
        '''Converte dicionario no formato hindcast[time][period][var] para array 
        com dimensão (time climatology, periods accumulation, lat, lon)'''

        if base == "nmme":
            years_hcst = range(1991, 2021)  
        elif base == "copernicus":
            years_hcst = range(1993, 2017)

        time_arrays = []            
        for t in range(len(hindcast)):
            period_arrays = [hindcast[years_hcst[t]][p].values for p in periods]
            stacked_periods = np.stack(period_arrays, axis=0)  # shape: (period, lat, lon)
            time_arrays.append(stacked_periods)

        return np.stack(time_arrays, axis=0) 

    def dict_to_array_members(self, base, hindcast, periods, var, model):
        '''Converte dicionário no formato hindcast[ano][periodo][var] para array 
        com dimensão (anos, períodos, membros, lat, lon)'''

        if base == "nmme":
            years_hcst = range(1991, 2021)  
        elif base == "copernicus":
            years_hcst = range(1993, 2017)

        time_arrays = []
        for t in range(len(hindcast)):
            period_arrays = []
            for p in periods:
                arr = hindcast[years_hcst[t]][p].values  # (members, lat, lon)

                # --- Tratamento especial para CFSv2 ---
                if model == "cfsv2":
                    arr = arr[:24, ...]  # mantém apenas os 24 primeiros membros
                elif model == "geos5v2":
                    arr = arr[:4, ...]  # mantém apenas os 4 primeiros membros

                period_arrays.append(arr)

            # Agora empilha períodos com mesma dimensão de membros
            stacked_periods = np.stack(period_arrays, axis=0)  # (period, members, lat, lon)
            time_arrays.append(stacked_periods)

        return np.stack(time_arrays, axis=0) 


    def hindcast_multimodel(self, base, year_fcst, month_fcst, var):    
        '''Calcula a média multimodelo para todos os períodos de acúmulo/media
        para os modelos disponíveis'''
        if base == "nmme":
            models_all = ["canesm5", "ccsm4","cesm1", "cfsv2", "gem52nemo", "geos5v2", "spear", "bam12"] #
            #models_all = ["ccsm4","cesm1", "cfsv2", "geos5v2", "spear", "bam12"] #
        if base == "copernicus":
            models_all = ["ecmwf", "ukmo","meteo_france","dwd","cmcc","ncep","jma","eccc4","eccc5","bom","bam12"]

        models_available = models_all
        model_names = [
        model if base == "nmme" else ConfigModelos.get_model_dir(model)
        for model in models_available]

        hcst_arrays = {}
        if base == "nmme":
            shape = (30, 8, 72, 144)  # define o shape padrão para arrays vazias
        elif base == "copernicus":
            shape = (24, 8, 72, 144) 

        for model in models_all:
            if model in models_available: 
                name_model = model if base == "nmme" else ConfigModelos.get_model_dir(model)
                hcst_dict = self.climatology_model_hcst(base, month_fcst, model, var)
                hcst_arrays[name_model] = self.dict_to_array(base, hcst_dict, ["mnth00","mnth01","mnth02","mnth03","mnth04","seas00","seas01","seas02"], var)
            else: 
                name_model = model if base == "nmme" else ConfigModelos.get_model_dir(model)
                hcst_arrays[name_model] = np.full(shape, np.nan)

        stacked = np.stack([hcst_arrays[m] for m in model_names], axis=0)
        multimodel_hcst = (np.nansum(stacked, axis=0))/len(models_available)

        return multimodel_hcst


    def mean_std_anom_hindcast(self, base, year_fcst, month_fcst, model, var):
        '''Calcula a média e o desvio padrão  da climatologia dos hindcasts'''
        if model == "multimodel":
            model_hcst = self.hindcast_multimodel(base, year_fcst, month_fcst, var)
            n_years = model_hcst.shape[0]
            hcst_mean = np.empty_like(model_hcst)
            hcst_std = np.empty_like(model_hcst)
            for i in range(n_years):
                # Remove o ano i
                data_excl_i = np.delete(model_hcst, i, axis=0)
                # Calcula média e std ao longo do tempo (dimensão 0)
                hcst_mean[i] = np.nanmean(data_excl_i, axis=0)
                hcst_std[i] = np.nanstd(data_excl_i, axis=0)
            hcst_anomaly = (model_hcst) - (hcst_mean)
        else:
            hcst_dict = self.climatology_model_hcst(base, month_fcst, model, var)
            model_hcst = self.dict_to_array(base, hcst_dict, ["mnth00","mnth01","mnth02","mnth03","mnth04","seas00","seas01","seas02"], var)
            n_years = model_hcst.shape[0]
            hcst_mean = np.empty_like(model_hcst)
            hcst_std = np.empty_like(model_hcst)
            for i in range(n_years):
                # Remove o ano i
                data_excl_i = np.delete(model_hcst, i, axis=0)
                # Calcula média e std ao longo do tempo (dimensão 0)
                hcst_mean[i] = np.nanmean(data_excl_i, axis=0)
                hcst_std[i] = np.nanstd(data_excl_i, axis=0)
            hcst_anomaly = (model_hcst) - (hcst_mean)      
        # 
        return model_hcst, hcst_mean, hcst_std, hcst_anomaly

    def mean_std_anom_hindcast_gamma(self, base, year_fcst, month_fcst, model, var):
        '''Calcula a média e o desvio padrão  da climatologia dos hindcasts'''
        if model == "multimodel":
            model_hcst = self.hindcast_multimodel(base, year_fcst, month_fcst, var)
            n_years = model_hcst.shape[0]
            hcst_mean = np.empty_like(model_hcst)
            hcst_std = np.empty_like(model_hcst)
            hcst_var = np.empty_like(model_hcst)            
            for i in range(n_years):
                # Remove o ano i
                data_excl_i = np.delete(model_hcst, i, axis=0)
                # Calcula média e std ao longo do tempo (dimensão 0)
                hcst_mean[i] = np.nanmean(data_excl_i, axis=0)
                hcst_std[i] = np.nanstd(data_excl_i, axis=0)
                hcst_var[i] = np.nanvar(data_excl_i, axis=0, ddof=0)
            hcst_anomaly = (model_hcst) - (hcst_mean)
        else:
            hcst_dict = self.climatology_model_hcst(base, month_fcst, model, var)
            model_hcst = self.dict_to_array(base, hcst_dict, ["mnth00","mnth01","mnth02","mnth03","mnth04","seas00","seas01","seas02"], var)
            n_years = model_hcst.shape[0]
            hcst_mean = np.empty_like(model_hcst)
            hcst_std = np.empty_like(model_hcst)
            hcst_var = np.empty_like(model_hcst)
            for i in range(n_years):
                # Remove o ano i
                data_excl_i = np.delete(model_hcst, i, axis=0)
                # Calcula média e std ao longo do tempo (dimensão 0)
                hcst_mean[i] = np.nanmean(data_excl_i, axis=0)
                hcst_std[i] = np.nanstd(data_excl_i, axis=0)
                hcst_var[i] = np.nanvar(data_excl_i, axis=0, ddof=0)                
            hcst_anomaly = (model_hcst) - (hcst_mean)      
        # 
        return model_hcst, hcst_mean, hcst_std, hcst_var, hcst_anomaly
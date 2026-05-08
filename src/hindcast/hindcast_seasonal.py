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

class Hindcast:
    def __init__(self, path_fcst, path_hcst):
        self.path_fcst = path_fcst
        self.path_hcst = path_hcst

    def is_all_nan(self, file_path):
        import xarray as xr

        try:
            with xr.open_dataset(file_path, decode_times=False)  as ds:

                # pega o nome da variável automaticamente
                var_name = list(ds.data_vars)[0]

                data = ds[var_name]

                return not data.notnull().any().compute().item()

        except Exception as e:
            print(f"Erro em {file_path}: {e}")
            return True

    def check_models(self, base, path_fcst, year_fcst, month_fcst, var):
        '''Checa quais modelos têm arquivos disponíveis para uma data e variável'''
        month = f"{month_fcst:02d}"
        month_name = calendar.month_abbr[month_fcst].capitalize() 
        fcst_dir = Path(path_fcst)

        if base == "copernicus":
            models = ["ecmwf", "ukmo","meteo_france","dwd","cmcc","ncep","jma","eccc4","eccc5","bom","bam12"]
        elif base == "nmme":
            models = ["canesm5", "ccsm4","cesm1", "cfsv2", "gem52nemo", "spear", "geos5v2", "bam12"]

        models_available = []

        for mdl in models:
            name_model_dir = mdl if base == "nmme" else ConfigModelos.get_model_dir_c3s(mdl)
            file_path = fcst_dir / base / name_model_dir / str(year_fcst) / f"{var}_monthly_{name_model_dir}_fcst_interp_{year_fcst}{month}01.nc"
            if file_path.exists() and file_path.stat().st_size > 2000:

                if not self.is_all_nan(file_path): #checa se o arquivo está todo cheio de NaN         
                    models_available.append(mdl)

        return models_available 

    def read_hcst_file(self, base, year_hcst, month_hcst, model, var):
        '''Armazena os dados de cada modelo fornecidos como lista no parâmetro models e para a variável var.
        Exemplo: year,month,day = itera na lista de climatologia '''

        if model == "multimodel":
            name_model = "multimodel"
        else:
            name_model = model if base == "nmme" else ConfigModelos.get_model_dir_c3s(model)

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

    def hindcast_multimodel(self, base, year_fcst, month_fcst, var):    
        '''Calcula a média multimodelo para todos os períodos de acúmulo/media
        para os modelos disponíveis'''
        if base == "nmme":
            models_all = ["canesm5", "ccsm4","cesm1", "cfsv2", "gem52nemo", "geos5v2", "spear", "bam12"] #
        if base == "copernicus":
            models_all = ["ecmwf", "ukmo","meteo_france","dwd","cmcc","ncep","jma","eccc4","eccc5","bom","bam12"]

        model_names = [model if base == "nmme" else ConfigModelos.get_model_dir_c3s(model) for model in models_all]

        models_available = self.check_models(base, self.path_fcst, year_fcst, month_fcst, var)
        #print("Modelos disponíveis (hindcast): ", models_available)

        # Verifica se há mais de um modelo disponível
        if len(models_available) <= 1:
            #print("Multimodelo não pode ser calculado: não há modelos disponíveis")
            return None

        hcst_arrays = {}
        if base == "nmme":
            shape = (30, 8, 72, 144)  # define o shape padrão para arrays vazias
        elif base == "copernicus":
            shape = (24, 8, 72, 144) 

        for model in models_all:
            name_model_dir = model if base == "nmme" else ConfigModelos.get_model_dir_c3s(model)
            if model in models_available: 
                hcst_dict = self.climatology_model_hcst(base, month_fcst, model, var)
                hcst_arrays[name_model_dir] = self.dict_to_array(base, hcst_dict, ["mnth00","mnth01","mnth02","mnth03","mnth04","seas00","seas01","seas02"], var)
            else:
                hcst_arrays[name_model_dir] = np.full(shape, np.nan)

        stacked = np.stack([hcst_arrays[m] for m in model_names], axis=0)
        multimodel_hcst = (np.nansum(stacked, axis=0))/len(models_available)

        return multimodel_hcst


    def mean_std_anom_hindcast(self, base, year_fcst, month_fcst, model, var):
        '''Calcula a média e o desvio padrão  da climatologia dos hindcasts'''
        if model == "multimodel":
            model_hcst = self.hindcast_multimodel(base, year_fcst, month_fcst, var)

            if model_hcst is None:
                print("\nMultimodelo não pode ser calculado: não há modelos disponíveis")
                return None, None, None, None

            hcst_mean = np.nanmean(model_hcst, axis = 0)
            hcst_std = np.nanstd(model_hcst, axis = 0)
            hcst_anomaly = (model_hcst) - (hcst_mean)
        else:
            hcst_dict = self.climatology_model_hcst(base, month_fcst, model, var)
            model_hcst = self.dict_to_array(base, hcst_dict, ["mnth00","mnth01","mnth02","mnth03","mnth04","seas00","seas01","seas02"], var)
            hcst_mean = np.nanmean(model_hcst, axis = 0)
            hcst_std = np.nanstd(model_hcst, axis = 0)
            hcst_anomaly = (model_hcst) - (hcst_mean)        

        return model_hcst, hcst_mean, hcst_std, hcst_anomaly

    def mean_std_anom_hindcast_gamma(self, base, year_fcst, month_fcst, model, var):
        '''Calcula a média e o desvio padrão  da climatologia dos hindcasts'''
        if model == "multimodel":
            model_hcst = self.hindcast_multimodel(base, year_fcst, month_fcst, var)
            hcst_mean = np.nanmean(model_hcst, axis = 0)
            hcst_std = np.nanstd(model_hcst, axis = 0)
            hcst_var = np.nanvar(model_hcst, axis = 0)
            hcst_anomaly = (model_hcst) - (hcst_mean)
        else:
            hcst_dict = self.climatology_model_hcst(base, month_fcst, model, var)
            model_hcst = self.dict_to_array(base, hcst_dict, ["mnth00","mnth01","mnth02","mnth03","mnth04","seas00","seas01","seas02"], var)
            hcst_mean = np.nanmean(model_hcst, axis = 0)
            hcst_std = np.nanstd(model_hcst, axis = 0)
            hcst_anomaly = (model_hcst) - (hcst_mean)        

        return model_hcst, hcst_mean, hcst_std, hcst_var, hcst_anomaly

# models_nmme = ["cfsv2", "canesm5", "gem52nemo", "spear", "cesm1", "ccsm4", "geos5v2", "bam12"]
# models_copernicus = ["cmccs35", "ecccs4", "ecccs5",  "ecmwfs5",  "jmas3",  "mfs8", "ncep", "dwds22", "ukmos6v604", "bam12"]

# hindcast = Hindcast(path_fcst, path_hcst)
# var = "prec" 

# #multimodel_hcst = hindcast.hindcast_multimodel("nmme", 2025, 3, var)

# model_hcst, hcst_mean, hcst_std, hcst_anomaly = hindcast.mean_std_anom_hindcast("nmme", 2025, 5, "multimodel", var)

# print(hcst_mean.shape) 
# print(model_hcst.shape)
# print(hcst_std.shape)
# print(hcst_anomaly.shape)

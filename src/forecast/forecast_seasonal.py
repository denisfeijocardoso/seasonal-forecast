import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import xarray as xr
import netCDF4
import calendar
from lifelines import CoxPHFitter
from scipy import interpolate
from pathlib import Path
from datetime import date, datetime,timedelta
from dateutil.relativedelta import *
from src.config.config_models_seasonal import ConfigModelos

class Forecast:
    def __init__(self, path_fcst):
        self.path_fcst = path_fcst

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

    def read_fcst_file(self, base, year_fcst, month_fcst, model, var):
        '''Armazena os dados de cada modelo fornecidos como lista no parâmetro models e para a variável var.
        Exemplo: year,month,day = itera na lista de climatologia '''

        if model == "multimodel":
            name_model = "multimodel"
        else:
            name_model = model if base == "nmme" else ConfigModelos.get_model_dir_c3s(model)   

        month = f"{month_fcst:02d}"
        month_name = calendar.month_abbr[month_fcst].capitalize() #nome do mês
        fcst_dir = f"{self.path_fcst}/{base}/{name_model}/{year_fcst}/"
        file_name_fcst = os.path.join(fcst_dir, f"{var}_monthly_{name_model}_fcst_interp_{year_fcst}{month}01.nc")
        model_fcst = xr.open_dataset(file_name_fcst, decode_times=False)
        model_fcst = model_fcst.squeeze()
        var_name = list(model_fcst.data_vars)[0]

        #Faz a média do ensemble
        if model == "bam12":
            member_dim = "ens"
        else:
            member_dim = "M" if base == "nmme" else "number"

        model_fcst = model_fcst.mean(dim=member_dim, skipna=True)

        # #Guarda valores de var para cada modelo e substitui valores menores que 0 por NaN e -9999.0 por NaN:
        # if var == "prec":
        #     model_fcst[var_name] = model_fcst[var_name].where((model_fcst[var_name] >= 0) | (model_fcst[var_name] != -9999.0), np.nan)
        # elif var == "t2mt":
        #     model_fcst[var_name] = model_fcst[var_name].where((model_fcst[var_name] != -9999.0), np.nan)

        if base == "copernicus" and model != "bam12": #transforma de m/s para mm/dia
            model_fcst[var_name] = (model_fcst[var_name] * 1000  * 86400) if var == "prec" else model_fcst[var_name]

        dataset = model_fcst

        model_fcst.close()

        return dataset

    def calculate_fcst_periods(self, base, year_fcst, month_fcst, model, model_fcst, var):
        '''Faz os acumulados ou médias para trimestre 1 e 2; seleciona mes 1, 2, 3 e 4'''
        fcst = {} 

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
                        new_date = date(year_fcst, month_fcst, 1) + relativedelta(months=start) #soma um mes
                        ndays = calendar.monthrange(year_fcst, new_date.month)[1]
                        if model == "bam12":
                            sel = model_fcst.isel(time=slice(start, end))
                            var_name = list(sel.data_vars)[0]
                            sel[var_name] = sel[var_name] * ndays                         
                        else:
                            sel = model_fcst.isel(L=slice(start, end))    
                            var_name = list(sel.data_vars)[0]  
                            sel[var_name] = sel[var_name] * ndays
                        fcst[period] = sel[var_name].squeeze()

                    else:
                        if period == "seas00":
                            fcst[period] = (
                                fcst["mnth00"] + fcst["mnth01"] + fcst["mnth02"]
                            )                        
                        elif period == "seas01":
                            fcst[period] = (
                                fcst["mnth01"] + fcst["mnth02"] + fcst["mnth03"]
                            )
                        elif period == "seas02":
                            fcst[period] = (
                                fcst["mnth02"] + fcst["mnth03"] + fcst["mnth04"]
                            )

                elif base == "copernicus": 
                    if is_mensal:
                        new_date = date(year_fcst, month_fcst, 1) + relativedelta(months=start) #soma um mes
                        ndays = calendar.monthrange(year_fcst, new_date.month)[1]     
                        if model == "bam12":
                            sel = model_fcst.isel(time=slice(start, end))
                            var_name = list(sel.data_vars)[0]
                        else:
                            sel = model_fcst.isel(forecastMonth=slice(start, end))      
                            var_name = list(sel.data_vars)[0]
                            sel[var_name] = sel[var_name] * ndays  
                        fcst[period] = sel[var_name].squeeze()
                    else:
                        if period == "seas00":
                            fcst[period] = (
                                 fcst["mnth00"] + fcst["mnth01"] + fcst["mnth02"]
                            )                             
                        elif period == "seas01":
                            fcst[period] = (
                                fcst["mnth01"] + fcst["mnth02"] + fcst["mnth03"]
                            )
                        elif period == "seas02":
                            fcst[period] = (
                                fcst["mnth02"] + fcst["mnth03"] + fcst["mnth04"]
                            )    

            elif var == "t2mt":
                if base == "nmme":
                    if is_mensal:
                        new_date = date(year_fcst, month_fcst, 1) + relativedelta(months=start) #soma um mes
                        ndays = calendar.monthrange(year_fcst, new_date.month)[1]
                        if model == "bam12":
                            sel = model_fcst.isel(time=slice(start, end))
                        else:
                            sel = model_fcst.isel(L=slice(start, end))    
                        var_name = list(sel.data_vars)[0]
                        sel[var_name] = sel[var_name] - 273.15
                        fcst[period] = sel[var_name].squeeze()
                    else:
                        if period == "seas00":
                            fcst[period] = (
                                (fcst["mnth00"] + fcst["mnth01"] + fcst["mnth02"]) / 3
                            )                             
                        elif period == "seas01":
                            fcst[period] = (
                                (fcst["mnth01"] + fcst["mnth02"] + fcst["mnth03"]) / 3
                            )
                        elif period == "seas02":
                            fcst[period] = (
                                (fcst["mnth02"] + fcst["mnth03"] + fcst["mnth04"]) / 3
                            )    

                elif base == "copernicus": 
                    if is_mensal:
                        new_date = date(year_fcst, month_fcst, 1) + relativedelta(months=start) #soma um mes
                        ndays = calendar.monthrange(year_fcst, new_date.month)[1]    
                        if model == "bam12":
                            sel = model_fcst.isel(time=slice(start, end))
                        else:
                            sel = model_fcst.isel(forecastMonth=slice(start, end))
                        var_name = list(sel.data_vars)[0]
                        sel[var_name] = sel[var_name] - 273.15
                        fcst[period] = sel[var_name].squeeze()
                    else:
                        if period == "seas00":
                            fcst[period] = (
                                (fcst["mnth00"] + fcst["mnth01"] + fcst["mnth02"]) / 3
                            )                             
                        elif period == "seas01":
                            fcst[period] = (
                                (fcst["mnth01"] + fcst["mnth02"] + fcst["mnth03"]) / 3
                            )
                        elif period == "seas02":
                            fcst[period] = (
                                (fcst["mnth02"] + fcst["mnth03"] + fcst["mnth04"]) / 3
                            )    

        return fcst

    def dict_to_array(self, base, forecast, periods, var):
        '''Converte dicionário no formato forecast[period][lat, lon] 
        para array com dimensão (periods_accumulation, lat, lon)'''

        period_arrays = []

        for p in periods:
            # forecast[p] é um xarray.DataArray ou ndarray com shape (lat, lon)
            data = forecast[p].values  # shape: (lat, lon)
            period_arrays.append(data)

        # Empilha os períodos na 1ª dimensão
        result = np.stack(period_arrays, axis=0)  # shape: (periods, lat, lon)

        return result

    def forecast_multimodel(self, base, year_fcst, month_fcst, var):    
        '''Calcula a média multimodelo para todos os períodos de acúmulo/media
        para os modelos disponíveis'''
        if base == "nmme":
            models_all = ["canesm5", "ccsm4","cesm1", "cfsv2", "gem52nemo", "geos5v2", "spear","bam12"]
        elif base == "copernicus":
            models_all = ["ecmwf", "ukmo","meteo_france","dwd","cmcc","ncep","jma","eccc4","eccc5","bom","bam12"]

        model_names = [model if base == "nmme" else ConfigModelos.get_model_dir_c3s(model) for model in models_all]

        models_available = self.check_models(base, self.path_fcst, year_fcst, month_fcst, var)
        #print(f"Modelos disponíveis (forecast): {models_available}")

        # Verifica se há mais de um modelo disponível
        if len(models_available) <= 1:
            print("Multimodelo não pode ser calculado: não há modelos disponíveis")
            return None
        
        fcst_arrays = {}
        if base == "nmme":
            shape = (8, 72, 144)  # define o shape padrão para arrays vazias
        elif base == "copernicus":
            shape = (8, 72, 144) 

        for model in models_all: 
            name_model_dir = model if base == "nmme" else ConfigModelos.get_model_dir_c3s(model)
            if model in models_available:
                model_fcst = self.read_fcst_file(base, year_fcst, month_fcst, model, var)
                fcst_dict = self.calculate_fcst_periods(base, year_fcst, month_fcst, model, model_fcst, var)
                fcst_arrays[name_model_dir] = self.dict_to_array(base, fcst_dict, ["mnth00","mnth01","mnth02","mnth03","mnth04","seas00","seas01","seas02"], var)
            else:
                fcst_arrays[name_model_dir] = np.full(shape, np.nan)
        stacked = np.stack([fcst_arrays[m] for m in model_names], axis=0)
        multimodel_fcst = (np.nansum(stacked, axis=0))/len(models_available)

        return multimodel_fcst
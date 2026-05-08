import os
import numpy as np
import pandas as pd
import xarray as xr
import netCDF4
import calendar
from pathlib import Path
from datetime import date, datetime,timedelta
from dateutil.relativedelta import *
from collections import defaultdict

class Observation:
    def __init__(self, path_obs):
        self.path_obs = path_obs

    def climatology_obs(self, base, month_obs):
        if base == "nmme":
            years_hcst = range(1991, 2021)
        elif base == "copernicus":
            years_hcst = range(1993, 2017)     
        results = []
        for i in range(5):
            for year in years_hcst:
                start_date = pd.Timestamp(year=year, month=month_obs, day=1)
                date = start_date + pd.DateOffset(months=i)
                results.append((date.month, date.year))
        return results

    def read_obs_file(self, base, month_obs, var):
        '''Lê os arquivos das observações para todos os anos da climatologia + meses à frente'''
        climatology = self.climatology_obs(base, month_obs)
        obs_data = defaultdict(dict)  # Mês -> {Ano -> DataArray}
        for month, year in climatology:
            ndays = calendar.monthrange(year, month)[1]
            month_name = calendar.month_abbr[month].capitalize()
            month_num = f"{month:02d}"
            if var == "prec": 
                file_name_obs = f"{self.path_obs}/gpcp/{year}/obs_gpcp_prec_mon_mean_{year}{month_num}01.nc"
                var_name = "precip"
            elif var == "t2mt":
                file_name_obs = f"{self.path_obs}/era5/obs_era5_t2mt_monthly_interp_{year}{month_num}01.nc"
                var_name = "t2m"
            
            ds = xr.open_dataset(file_name_obs, decode_timedelta=True)
            #print(ds.lat[37])
            #print(ds.lon[122])

            data = ds[var_name].squeeze()

            if var == "prec":
                #data = data.where(data >= 0)
                data = data * ndays
            elif var == "t2mt":
                data = data - 273.15

            obs_data[month][year] = data  # agora é um dicionário dentro de outro
            ds.close()

        return obs_data

    def calculate_obs_periods(self, base, month_obs, var):
        '''Faz os acumulados ou médias para trimestre 0, 1 e 2; seleciona mês 1, 2, 3 e 4'''
        obs_data = self.read_obs_file(base, month_obs, var)

        periods = {
            "mnth00": (0, 1), "mnth01": (1, 2), "mnth02": (2, 3),
            "mnth03": (3, 4), "mnth04": (4, 5),
            "seas00": (0, 3), "seas01": (1, 4), "seas02": (2, 5)
        }

        month_sequence = list(obs_data.keys())
        obs_periods = {}

        for label, (start_idx, end_idx) in periods.items():
            months = month_sequence[start_idx:end_idx]
            obs_periods[label] = []
            n_anos = min(len(obs_data[m]) for m in months) 

            for i in range(n_anos):
                if label.startswith("mnth"):
                    m = months[0]
                    ano_i = list(obs_data[m].keys())[i]
                    obs_periods[label].append(obs_data[m][ano_i])

                elif label.startswith("seas"):
                    acumulado = 0
                    for m in months:
                        ano_i = list(obs_data[m].keys())[i]
                        acumulado += obs_data[m][ano_i]

                    if var == "t2mt":
                        acumulado = acumulado / 3

                    obs_periods[label].append(acumulado)
   
        return obs_periods



    def mean_std_anom_obs(self, base, month_obs, var):
        '''Calcula a média, desvio padrão e anomalia da climatologia das observações'''
        obs_periods = self.calculate_obs_periods(base, month_obs, var) 

        # Períodos que queremos calcular estatísticas
        selected_periods = ['mnth00','mnth01', 'mnth02', 'mnth03', 'mnth04',
                            'seas00', 'seas01', 'seas02']

        stats = {}

        for label in selected_periods:
            data = obs_periods.get(label)
            data_array = np.array(data)

            # Calcula média, desvio padrão e anomalias
            mean = np.nanmean(data_array, axis=0)
            mediana = np.nanmedian(data_array, axis=0)
            std = np.nanstd(data_array, axis=0)
            tercil_inf = np.nanpercentile(data_array, 33.33, axis=0)
            tercil_sup = np.nanpercentile(data_array, 66.66, axis=0)
            obs_total = data_array      
            anomalias = obs_total - mean     

            # Armazena os resultados
            stats[label] = {
                'total': obs_total,
                'mean': mean,      
                'mediana': mediana,
                'std': std,        
                'anomaly': anomalias,   
                'tercilinf': tercil_inf,
                'tercilsup': tercil_sup
            }

        return stats

    def mean_std_anom_obs_gamma(self, base, month_obs, var):
        '''Calcula a média, desvio padrão e anomalia da climatologia das observações'''
        obs_periods = self.calculate_obs_periods(base, month_obs, var) 

        # Períodos que queremos calcular estatísticas
        selected_periods = ['mnth00','mnth01', 'mnth02', 'mnth03', 'mnth04',
                            'seas00', 'seas01', 'seas02']

        stats = {}

        for label in selected_periods:
            data = obs_periods.get(label)
            data_array = np.array(data)

            # Calcula média, desvio padrão e anomalias
            mean = np.nanmean(data_array, axis=0)
            mediana = np.nanmedian(data_array, axis=0)
            variance = np.nanvar(data_array, axis=0)
            std = np.nanstd(data_array, axis=0)
            tercil_inf = np.nanpercentile(data_array, 33.33, axis=0)
            tercil_sup = np.nanpercentile(data_array, 66.66, axis=0)
            quartil_inf = np.nanpercentile(data_array, 25, axis=0)
            quartil_sup = np.nanpercentile(data_array, 75, axis=0) 
            iqr_obs =  quartil_sup - quartil_inf         
            obs_total = data_array      
            anomalias = obs_total - mean     

            # Armazena os resultados
            stats[label] = {
                'total': obs_total,
                'mean': mean,      
                'mediana': mediana,
                'variance': variance,   
                'std': std,        
                'anomaly': anomalias,   
                'tercilinf': tercil_inf,
                'tercilsup': tercil_sup,
                "intqobs": iqr_obs
            }

        return stats




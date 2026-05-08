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
from joblib import Parallel, delayed

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
            n_years = data_array.shape[0]

            # Função auxiliar para processar cada ano
            def process_year(i):
                data_excl_i = np.delete(data_array, i, axis=0)
                mean = np.nanmean(data_excl_i, axis=0)
                mediana = np.nanmedian(data_excl_i, axis=0)
                std = np.nanstd(data_excl_i, axis=0)
                tercis = np.nanpercentile(data_excl_i, [33.33, 66.66], axis=0)
                obs = data_array[i, ...]
                return mean, mediana, std, tercis[0], tercis[1], obs

            # Executar em paralelo
            results = Parallel(n_jobs=-1)(delayed(process_year)(i) for i in range(n_years))

            # Pré-alocar arrays
            mean_loo = np.empty_like(data_array)
            mediana_loo = np.empty_like(data_array)            
            std_loo = np.empty_like(data_array)
            tercil_inf = np.empty_like(data_array)
            tercil_sup = np.empty_like(data_array)
            data_obs = np.empty_like(data_array)

            # Preencher os arrays com os resultados paralelos
            for i, (mean, mediana, std, t_inf, t_sup, obs) in enumerate(results):
                mean_loo[i] = mean
                mediana_loo[i] = mediana                
                std_loo[i] = std
                tercil_inf[i] = t_inf
                tercil_sup[i] = t_sup
                data_obs[i] = obs

            # Calcula anomalias com base na média removendo o ano atual
            anomalias = data_array - mean_loo

            # Armazena os resultados
            stats[label] = {
                'total': data_obs,
                'mean': mean_loo,      
                'mediana': mediana_loo,
                'std': std_loo,        
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
            n_years = data_array.shape[0]

            # Função auxiliar para processar cada ano
            def process_year(i):
                data_excl_i = np.delete(data_array, i, axis=0)
                mean = np.nanmean(data_excl_i, axis=0)
                mediana = np.nanmedian(data_excl_i, axis=0)
                std = np.nanstd(data_excl_i, axis=0)
                variance = np.nanvar(data_excl_i, axis=0, ddof=0)
                tercis = np.nanpercentile(data_excl_i, [33.33, 66.66], axis=0)
                obs = data_array[i, ...]
                return mean, mediana, std, variance, tercis[0], tercis[1], obs

            # Executar em paralelo
            results = Parallel(n_jobs=-1)(delayed(process_year)(i) for i in range(n_years))

            # Pré-alocar arrays
            mean_loo = np.empty_like(data_array)
            mediana_loo = np.empty_like(data_array)            
            std_loo = np.empty_like(data_array)
            var_loo = np.empty_like(data_array)
            tercil_inf = np.empty_like(data_array)
            tercil_sup = np.empty_like(data_array)
            data_obs = np.empty_like(data_array)

            # Preencher os arrays com os resultados paralelos
            for i, (mean, mediana, std, variance, t_inf, t_sup, obs) in enumerate(results):
                mean_loo[i] = mean
                mediana_loo[i] = mediana                
                std_loo[i] = std
                var_loo[i] = variance                
                tercil_inf[i] = t_inf
                tercil_sup[i] = t_sup
                data_obs[i] = obs

            # Calcula anomalias com base na média removendo o ano atual
            anomalias = data_array - mean_loo

            # Armazena os resultados
            stats[label] = {
                'total': data_obs,
                'mean': mean_loo,      
                'mediana': mediana_loo,
                'std': std_loo,  
                'variance': var_loo,      
                'anomaly': anomalias,   
                'tercilinf': tercil_inf,
                'tercilsup': tercil_sup
            }

        return stats

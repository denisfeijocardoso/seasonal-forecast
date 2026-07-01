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
from src.forecast.forecast import Forecast
from src.hindcast.hindcast import Hindcast
from src.observation.observation import Observation
from src.config.config_models import ConfigModelos
from src.config.paths import path_hcst, path_fcst, path_obs
from scipy.stats import gamma, norm
from scipy.stats import pearsonr 
from joblib import Parallel, delayed
from lifelines import CoxPHFitter

##################################################
#CLASSE COM A FUNÇÃO PARA CALCULAR AS CALIBRAÇÕES#
##################################################

hcst = Hindcast(...)
obs = Observation(...)
fcst = Forecast(...)

hcst_stats = {
    model: hcst.compute_statistics(model)
    for model in models
}

LinearRegression.fit(
    obs_stats,
    hcst_stats["ecmwf"]
)

RandomForest.fit(
    obs_stats,
    hcst_stats["ecmwf"]
)

XGBoost.fit(
    obs_stats,
    hcst_stats["ecmwf"]
)

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
                
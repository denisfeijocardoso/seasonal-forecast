import os
import xarray as xr
import numpy as np
import netCDF4 as nc
import matplotlib.pyplot as plt
from scipy.io import netcdf_file
from netCDF4 import Dataset
from scipy.stats import linregress
from src.forecast.forecast_sazonal import Forecast
from src.hindcast.hindcast_sazonal import Hindcast
from src.observation.observation_sazonal import Observation

##############
#SCATTER PLOT#
##############

path_hcst = "/dados/mmclima/multimodelo/sazonal/hindcast"
path_fcst = "/dados/mmclima/multimodelo/sazonal/forecast"
path_obs = "/dados/mmclima/multimodelo/sazonal/obs"
outdir = "/dados/mmclima/multimodelo/sazonal/figures/artigo"

base = "nmme"
month_fcst = 2
year_fcst = 2025
var = "prec"
model = "multimodel"

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

print(model_hcst.shape)
print(obs_total.shape)

pontos_2025 = {
    "Venezuela": (38, 118),  # lat_obs[36], lon_obs[119] → ( 1.25 , -61.25 )
    "Chile": (19, 114),  # lat_obs[23], lon_obs[115] → (-28.75, -71.25)
    "SC":    (25, 123),  # lat_obs[25], lon_obs[123] → (-26.25, -51.25)
    "riogrande": (23, 123)  # lat_obs[25], lon_obs[123] → (-26.25, -51.25)        
}

obs = xr.open_dataset("/dados/mmclima/multimodelo/sazonal/obs/gpcp/obs_gpcp_pr_mon_mean_1979-2025.nc")
lat_obs = obs["lat"].values
lon_obs = obs["lon"].values

def format_coord(lat, lon):
    # Latitude
    if lat >= 0:
        lat_str = f"{abs(lat):.2f}N"
    else:
        lat_str = f"{abs(lat):.2f}S"
        
    # Longitude
    if lon >= 0:
        lon_str = f"{abs(lon):.2f}E"
    else:
        lon_str = f"{abs(lon):.2f}W"
        
    return lat_str, lon_str

def lon360_to_180(lon):
    return ((lon + 180) % 360) - 180

for nome, (lat_idx, lon_idx) in pontos_2025.items():

    lat_real = lat_obs[lat_idx]
    lon_real = lon360_to_180(lon_obs[lon_idx])   

    lat_str, lon_str = format_coord(lat_real, lon_real)

    serie_hcst = model_hcst[:, 6, lat_idx, lon_idx]
    serie_obs  = obs_total[6, :, lat_idx, lon_idx]

    result = linregress(serie_hcst, serie_obs)

    alpha = result.intercept
    beta  = result.slope

    plt.figure(figsize=(8,8))
    plt.scatter(serie_hcst, serie_obs, s=60, color='black')

    x_line = np.linspace(serie_hcst.min(), serie_hcst.max(), 100)
    y_line = alpha + beta * x_line

    plt.plot(x_line, y_line, color='red', linewidth=2)

    if nome == "riogrande":
        plt.title(
            f"a) Relationship btw hcst. and obs. precip.  Lat:{lat_str} Lon:{lon_str}\n"
            f"Calibrated Multi-Model: GPCP (1991-2020)  Issued: Feb Valid for MAM"
            ,fontsize=18, fontweight='bold')

    # if nome == "SC":
    #     plt.title(
    #         f"a) Relationship btw hcst. and obs. precip.  Lat:{lat_str} Lon:{lon_str}\n"
    #         f"Calibrated Multi-Model: GPCP (1991-2020)  Issued: Feb Valid for MAM"
    #         ,fontsize=18, fontweight='bold')

    elif nome == "Chile":
        plt.title(
            f"b) Relationship btw hcst. and obs. precip.  Lat:{lat_str} Lon:{lon_str}\n"
            f"Calibrated Multi-Model: GPCP (1991-2020)  Issued: Feb Valid for MAM"
            ,fontsize=18, fontweight='bold')            

    elif nome == "Venezuela":
        plt.title(
            f"c) Relationship btw hcst. and obs. precip.  Lat:{lat_str} Lon:{lon_str}\n"
            f"Calibrated Multi-Model: GPCP (1991-2020)  Issued: Feb Valid for MAM"
            ,fontsize=18, fontweight='bold')  

    plt.xlabel("HINDCAST PRECIPITATION (mm)",fontsize=16)
    plt.ylabel("OBSERVED PRECIPITATION (mm)",fontsize=16)
    plt.tick_params(axis='both', labelsize=14)

    plt.savefig(f"{outdir}/scatter_{nome}.png", dpi=300, bbox_inches='tight')

    plt.close()
# var = "prec"
# months = [2,3,4,5]
# model = "multimodel"

# artigo_dir = "/dados/mmclima/multimodelo/subsazonal/posproc/subc/artigo/"

# for month in months:
#     file_hcst = f"{artigo_dir}/hcst_total_{model}_{var}_{month:02d}.nc"
#     file_obs  = f"{artigo_dir}/obs_total_{var}_{month:02d}.nc"
#     file_alpha = f"{artigo_dir}/alpha_multimodel_{var}_{month:02d}.nc"
#     file_beta  = f"{artigo_dir}/beta_multimodel_{var}_{month:02d}.nc"

#     hcst_ds = xr.open_dataset(file_hcst)
#     obs_ds = xr.open_dataset(file_obs)
#     alpha_ds = xr.open_dataset(file_alpha)
#     beta_ds = xr.open_dataset(file_beta)

#     lat = hcst_ds['lon']

#     hcst_total = hcst_ds['hcst_total'].values
#     obs_total = obs_ds['obs_total'].values
#     alpha = alpha_ds['alpha'].values
#     beta = beta_ds['beta'].values


#     month_clim_hcst = np.zeros((10, 51, 180, 360))
#     month_clim_obs = np.zeros((10, 51, 180, 360))

#     for p in range(10):
#         #for w in range(4):
#             #for k in range(1):        
#         #month_mean_hcst = np.zeros((wk, years, lat, lon))

#         #HINDCAST
#         month_hcst1 = np.delete(hcst_total[p, 0, 0,...], 0, axis=0)
#         month_hcst2 = np.delete(hcst_total[p, 0, 1,...], 0, axis=0)
#         month_hcst3 = np.delete(hcst_total[p, 0, 2,...], 0, axis=0)
#         month_clim_hcst[p,...] = np.concatenate((month_hcst1, month_hcst2, month_hcst3), axis=0)    

#         #OBS.
#         month_obs1 = np.delete(obs_total[p, 0, 0,...], 0, axis=0)
#         month_obs2 = np.delete(obs_total[p, 0, 1,...], 0, axis=0)
#         month_obs3 = np.delete(obs_total[p, 0, 2,...], 0, axis=0)
#         month_clim_obs[p,...] = np.concatenate((month_obs1, month_obs2, month_obs3), axis=0)


#     serie_hcst = month_clim_hcst[0, :, 95, 321]
#     serie_obs = month_clim_obs[0, :, 95, 321]
#     corr = np.corrcoef(serie_hcst, serie_obs)[0, 1]
#     alpha_reta = alpha[0, 0, 0, 95, 321]
#     beta_reta = beta[0, 0, 0, 95, 321]

#     #Plotar
#     periods = [
#         'week01','week02','week03','week04',
#         'fort01','fort02','3wks01','mnth01',
#         'fort03','ds4401'
#     ]

#     period_labels = {
#         "week01": "WEEK-1",
#         "week02": "WEEK-2",
#         "week03": "WEEK-3",
#         "week04": "WEEK-4",
#         "fort01": "FORTNIGHT-1",
#         "fort02": "FORTNIGHT-2",
#         "fort03": "FORTNIGHT-3",
#         "mnth01": "30 DAYS",
#         "ds4401": "44 DAYS",
#     }

#     path = "/dados/mmclima/multimodelo/subsazonal/figures/subc/artigo/"
#     mes_str = f"{month:02d}"  

#     for p in range(10):

#         # Extrai as séries do ponto (94,321)
#         serie_hcst = month_clim_hcst[p, :, 94, 321]
#         serie_obs  = month_clim_obs[p,  :, 94, 321]
#         print(len(serie_hcst))
#         quit()
#         # Figura
#         fig, ax = plt.subplots(figsize=(10, 9))

#         # Engrossar a caixa
#         for spine in ax.spines.values():
#             spine.set_linewidth(3)  

#         ax.scatter(serie_hcst,serie_obs, s=80, color='black')

#         ax.set_ylabel("OBSERVED PRECIPITATION (mm)", fontsize=38)
#         ax.set_xlabel("HINDCAST PRECIPITATION (mm)", fontsize=38)

#         if p == 0:
#             month_names = {2: "FEBRUARY", 3: "MARCH", 4: "APRIL", 5: "MAY"}
#             if month in month_names:
#                 ax.set_title(month_names[month], fontsize=68)

#         x_min = serie_hcst.min()
#         x_max = serie_hcst.max()

#         # === Reta da regressão (alpha + beta*x) ===
#         x_line = np.linspace(x_min, x_max, 100)
#         y_line = alpha_reta + beta_reta * x_line
#         ax.plot(x_line, y_line, color="black", linewidth=3)

#         # === Escrever correlação ===
#         corr = np.corrcoef(serie_hcst, serie_obs)[0, 1]
#         # ax.text(
#         #     0.03, 0.97,                  
#         #     f"corr = {corr:.2f}",
#         #     transform=ax.transAxes,
#         #     fontsize=35,
#         #     fontweight="bold",
#         #     ha="left",                   
#         #     va="top"                  
#         # )

#         ax.tick_params(axis='both', labelsize=29)

#         period = periods[p]
#         if month == 5 and period in period_labels:
#             #fig.subplots_adjust(right=0.85)
#             fontsize = 67 if period in ["fort01", "fort02", "fort03"] else 69
#             fig.text(0.94, 0.5, period_labels[period],
#                     fontsize=fontsize, rotation=270,
#                     va='center', ha='center')

#         plt.subplots_adjust(left=0.18, right=0.89)
#         # Nome do arquivo
#         period = periods[p]
#         file = f"scatterplot_{mes_str}_{period}.png"
#         fig.savefig(path + file, dpi=150)
#         print(f"Figura salva: {path}{file}")

#         plt.close(fig)

# ##(6°S, 39°W – CE)
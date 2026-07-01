import xarray as xr
import numpy as np
import logging
from src.config.loader import get_climatology_period
from src.config.paths import PATH_FCST, PATH_HCST, PATH_OBS
from src.config.config_models import build_model_dir_name, get_dim_names

logger = logging.getLogger(__name__)

#Os dados das previsões e observações do ERA5 serão interpolados para a grade dos dados do GPCP
LAT_GPCP = np.arange(-88.75, 91.25, 2.5)
LON_GPCP = np.arange(1.25, 361.25, 2.5)

def interpolation_hindcast_model(
        base: str,
        model: str,
        var: str,
        month_hcst: int
) -> None:
    
    start_year, end_year = get_climatology_period(base)
    years_climatology = range(start_year, end_year + 1)

    month_hcst = f"{month_hcst:02d}"

    name_model_dir = build_model_dir_name(model)

    dims_model = get_dim_names(
        base,
        model
    )

    dim_lat = dims_model["lat"]
    dim_lon = dims_model["lon"]
    
    for year in years_climatology:

        year_dir = (
            PATH_HCST /
            base /
            name_model_dir /
            str(year) 
        )

        path_hcst_file = (
            year_dir /
            f"{var}_monthly_{name_model_dir}_hcst_{year}{month_hcst}01.nc"
        )

        path_interp_file = (
            year_dir /
            f"{var}_monthly_{name_model_dir}_hcst_interp_{year}{month_hcst}01.nc"
        )

        if path_interp_file.exists():

            logger.info(
                f"Arquivo já interpolado: {path_interp_file} — pulando."
            )

            continue

        try:

            with xr.open_dataset(
                path_hcst_file, 
                decode_times=False                
            ) as hcst:

            
                if hcst[dim_lat].values[0] > hcst[dim_lat].values[-1]:
                    hcst = hcst.sortby(dim_lat)
                
                ds_interp = hcst.interp(

                    {
                        dim_lat: LAT_GPCP,
                        dim_lon: LON_GPCP
                    },

                    method = "linear"
                )
                        
                # Salva o arquivo interpolado
                ds_interp.to_netcdf(path_interp_file)
                ds_interp.close()

                logger.info(
                    f"Arquivo interpolado: {path_interp_file}"
                    )
                
        except Exception:
            logger.exception(
                f"Erro ao interpolar {path_hcst_file}"
            )

def interpolation_forecast_model(
        base: str,
        model: str,
        var: str,
        year_fcst: int,
        month_fcst: int
) -> None:

    month_fcst = f"{month_fcst:02d}"

    name_model_dir = build_model_dir_name(model)

    dims_model = get_dim_names(
        base,
        model
    )

    dim_lat = dims_model["lat"]
    dim_lon = dims_model["lon"]

    year_dir = (
        PATH_FCST /
        base /
        name_model_dir /
        str(year_fcst) 
    )

    path_fcst_file = (
        year_dir /
        f"{var}_monthly_{name_model_dir}_fcst_{year_fcst}{month_fcst}01.nc"
    )

    path_interp_file = (
        year_dir /
        f"{var}_monthly_{name_model_dir}_fcst_interp_{year_fcst}{month_fcst}01.nc"
    )

    if path_interp_file.exists():

        logger.info(
            f"Arquivo já interpolado: {path_interp_file} — pulando."
        )

        return

    try:

        with xr.open_dataset(
            path_fcst_file, 
            decode_times=False                
        ) as fcst:

        
            if fcst[dim_lat].values[0] > fcst[dim_lat].values[-1]:
                fcst = fcst.sortby(dim_lat)
            
            ds_interp = fcst.interp(

                {
                    dim_lat: LAT_GPCP,
                    dim_lon: LON_GPCP
                },

                method = "linear"
            )
                    
            # Salva o arquivo interpolado
            ds_interp.to_netcdf(path_interp_file)
            ds_interp.close()

            logger.info(
                f"Arquivo interpolado: {path_interp_file}"
                )
            
    except Exception:
        logger.exception(
            f"Erro ao interpolar {path_fcst_file}"
        )


#def interp_echam():
#     # Abrir o arquivo NetCDF da observação (referencia para interpolar)
#     file_obs = PATH_OBS + "/gpcp/obs_gpcp_pr_mon_mean_1979-2025.nc"
#     obs = xr.open_dataset(file_obs)
#     lat_new = obs["lat"] #resolução 2.5° 
#     lon_new = obs["lon"] #resolução 2.5° 

#     #Abrir arquivo ECHAM 
#     file_echam = path_fcst + "/echam46/pcp-seasonacc-echam46-hind9120-fev2025_2025MAM_1p0.nc"
#     data_echam = xr.open_dataset(file_echam, decode_times=False)
#     anos = range(1991,2021)

#     #for t, ano in enumerate(anos):
#     da_t = data_echam
#     file_out = f"{path_fcst}/echam46/prec_seasonaly_echam46_hcst_MAM_2025.nc"
#     file_interp = f"{path_fcst}/echam46/prec_seasonaly_echam46_hcst_interp_MAM_2025.nc"
#     da_t.to_netcdf(file_out)
#     print(f"Salvo: {file_out}")

#     #Interpolação
#     if os.path.exists(file_interp):
#         print(f"Arquivo já interpolado: {file_interp} — pulando.")
# #continue

#     try:
#         # Tenta abrir o arquivo
#         hcst = xr.open_dataset(file_out, decode_times=False)
        
#         ds_interp = hcst.interp(lat=lat_new, lon=lon_new, method="linear")  
                
#         # Salva o arquivo interpolado
#         ds_interp.to_netcdf(file_interp)
#         print(f"Arquivo interpolado: {file_interp}")
#         hcst.close()

#     except FileNotFoundError:
#         # Caso o arquivo não exista, imprime a mensagem e continua o loop
#         print(f"O arquivo {file_out} não foi baixado...")

# def interp_era5():
#     # Abrir o arquivo NetCDF da observação (referencia para interpolar)
#     file_obs = PATH_OBS + "/gpcp/obs_gpcp_pr_mon_mean_1979-2025.nc"
#     obs = xr.open_dataset(file_obs)
#     lat_new = obs["lat"] #resolução 2.5° 
#     lon_new = obs["lon"] #resolução 2.5° 

#     #Abrir o arquivo de Hindcast (Resolução 1°)
#     path_era5 = "/dados/mmclima/multimodelo/seasonal/obs/era5"    
#     meses = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
#     periodo_climatologia = range(1979, 2024)

#     for ano in periodo_climatologia:
#         for mes in meses:
#             file_era5 = f"{path_era5}/era5obs_t2mt_monthly_{mes}_{ano}.nc"
            
#             try:
#                 # Tenta abrir o arquivo
#                 obs = xr.open_dataset(file_era5, decode_times=False)
                
#                 if obs.latitude[0] > obs.latitude[-1]:
#                     obs = obs.sortby("latitude")
#                     print(obs.latitude)
#                     ds_interp = obs.interp(latitude=lat_new, longitude=lon_new, method="linear")
#                 # Salva o arquivo interpolado
#                 ds_interp.to_netcdf(f"{path_era5}/obs_era5_t2mt_monthly_interp_{mes}_{ano}.nc")
#                 print(f"Arquivo interpolado: obs_era5_t2mt_monthly_interp_{mes}_{ano}.nc")
#                 obs.close()
        
#             except FileNotFoundError:
#                 # Caso o arquivo não exista, imprime a mensagem e continua o loop
#                 print(f"O arquivo {file_era5} não foi baixado...")
#                 continue  # Continua para o próximo mês/ano/modelo
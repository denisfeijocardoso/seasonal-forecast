import xarray as xr
import netCDF4
import calendar
import os
from src.config.config_models import ConfigModelos
from src.config.config_path import path_hcst, path_fcst, path_obs


def interp_echam():

    # Abrir o arquivo NetCDF da observação (referencia para interpolar)
    file_obs = path_obs + "/gpcp/obs_gpcp_pr_mon_mean_1979-2025.nc"
    obs = xr.open_dataset(file_obs)
    lat_new = obs["lat"] #resolução 2.5° 
    lon_new = obs["lon"] #resolução 2.5° 

    #Abrir arquivo ECHAM 
    file_echam = path_fcst + "/echam46/pcp-seasonacc-echam46-hind9120-fev2025_2025MAM_1p0.nc"
    data_echam = xr.open_dataset(file_echam, decode_times=False)
    anos = range(1991,2021)

    #for t, ano in enumerate(anos):
    da_t = data_echam
    file_out = f"{path_fcst}/echam46/prec_seasonaly_echam46_hcst_MAM_2025.nc"
    file_interp = f"{path_fcst}/echam46/prec_seasonaly_echam46_hcst_interp_MAM_2025.nc"
    da_t.to_netcdf(file_out)
    print(f"Salvo: {file_out}")

    #Interpolação
    if os.path.exists(file_interp):
        print(f"Arquivo já interpolado: {file_interp} — pulando.")
#continue

    try:
        # Tenta abrir o arquivo
        hcst = xr.open_dataset(file_out, decode_times=False)
        
        ds_interp = hcst.interp(lat=lat_new, lon=lon_new, method="linear")  
                
        # Salva o arquivo interpolado
        ds_interp.to_netcdf(file_interp)
        print(f"Arquivo interpolado: {file_interp}")
        hcst.close()

    except FileNotFoundError:
        # Caso o arquivo não exista, imprime a mensagem e continua o loop
        print(f"O arquivo {file_hcst} não foi baixado...")

#    continue  # Continua para o próximo mês/ano/modelo        

interp_echam()
quit()

def interp_hcst(base, month):
    # Abrir o arquivo NetCDF da observação (referencia para interpolar)
    file_obs = path_obs + "/gpcp/obs_gpcp_pr_mon_mean_1979-2025.nc"
    obs = xr.open_dataset(file_obs)
    lat_new = obs["lat"] #resolução 2.5° 
    lon_new = obs["lon"] #resolução 2.5° 

    meses = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    varis = ["prec","t2mt"]

    if base == "nmme":
        periodo_climatologia = range(1991, 2021)
        models = ["canesm5", "ccsm4","cesm1", "cfsv2", "gem52nemo", "geos5v2", "spear", "bam12"]        
    elif base == "copernicus":
        periodo_climatologia = range(1993, 2017)
        models = ["ecmwf", "ukmo","meteo_france","dwd","cmcc","ncep","jma","eccc4","eccc5","bom","bam12"]

    for model in models:
        for var in varis:
            #
            name_model_dir = model if base == "nmme" else ConfigModelos.get_model_dir_c3s(model)
            #
            for ano in periodo_climatologia:
                month_fcst = f"{month:02d}"
                file_hcst = f"{path_hcst}/{base}/{name_model_dir}/{ano}/{var}_monthly_{name_model_dir}_hcst_{ano}{month_fcst}01.nc"
                file_interp = f"{path_hcst}/{base}/{name_model_dir}/{ano}/{var}_monthly_{name_model_dir}_hcst_interp_{ano}{month_fcst}01.nc"
                
                # Verifica se já existe o arquivo interpolado
                if os.path.exists(file_interp):
                    print(f"Arquivo já interpolado: {file_interp} — pulando.")
                    continue

                try:
                    # Tenta abrir o arquivo
                    hcst = xr.open_dataset(file_hcst, decode_times=False)
                    
                    # Realiza a interpolação
                    if base == "nmme" and model != "bam12":
                        ds_interp = hcst.interp(Y=lat_new, X=lon_new, method="linear")
                    elif base == "nmme" and model == "bam12":
                        ds_interp = hcst.interp(lat=lat_new, lon=lon_new, method="linear")                            
                    elif base == "copernicus" and model !="bam12":
                        if hcst.latitude[0] > hcst.latitude[-1]:
                            hcst = hcst.sortby("latitude")
                        ds_interp = hcst.interp(latitude=lat_new, longitude=lon_new, method="linear")
                    elif base == "copernicus" and model =="bam12":
                        ds_interp = hcst.interp(lat=lat_new, lon=lon_new, method="linear")  
                            
                    # Salva o arquivo interpolado
                    ds_interp.to_netcdf(file_interp)
                    print(f"Arquivo interpolado: {var}_monthly_{name_model_dir}_hcst_interp_{ano}{month_fcst}01.nc")
                    hcst.close()
                
                except FileNotFoundError:
                    # Caso o arquivo não exista, imprime a mensagem e continua o loop
                    print(f"O arquivo {file_hcst} não foi baixado...")
                    continue  # Continua para o próximo mês/ano/modelo


def interp_era5():
    # Abrir o arquivo NetCDF da observação (referencia para interpolar)
    file_obs = path_obs + "/gpcp/obs_gpcp_pr_mon_mean_1979-2025.nc"
    obs = xr.open_dataset(file_obs)
    lat_new = obs["lat"] #resolução 2.5° 
    lon_new = obs["lon"] #resolução 2.5° 

    #Abrir o arquivo de Hindcast (Resolução 1°)
    path_era5 = "/dados/mmclima/multimodelo/seasonal/obs/era5"    
    meses = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    periodo_climatologia = range(1979, 2024)

    for ano in periodo_climatologia:
        for mes in meses:
            file_era5 = f"{path_era5}/era5obs_t2mt_monthly_{mes}_{ano}.nc"
            
            try:
                # Tenta abrir o arquivo
                obs = xr.open_dataset(file_era5, decode_times=False)
                
                if obs.latitude[0] > obs.latitude[-1]:
                    obs = obs.sortby("latitude")
                    print(obs.latitude)
                    ds_interp = obs.interp(latitude=lat_new, longitude=lon_new, method="linear")
                # Salva o arquivo interpolado
                ds_interp.to_netcdf(f"{path_era5}/obs_era5_t2mt_monthly_interp_{mes}_{ano}.nc")
                print(f"Arquivo interpolado: obs_era5_t2mt_monthly_interp_{mes}_{ano}.nc")
                obs.close()
        
            except FileNotFoundError:
                # Caso o arquivo não exista, imprime a mensagem e continua o loop
                print(f"O arquivo {file_era5} não foi baixado...")
                continue  # Continua para o próximo mês/ano/modelo

def interp_fcst(base, year, month_num, var):
    monthstr = calendar.month_abbr[month_num].capitalize()  # Ex: 4 → 'Apr' 
    month_fcst = f"{month_num:02d}"
    # Abrir o arquivo NetCDF da observação (referencia para interpolar)
    file_obs = path_obs + "/gpcp/obs_gpcp_pr_mon_mean_1979-2025.nc"
    obs = xr.open_dataset(file_obs)
    lat_new = obs["lat"] #resolução 2.5° 
    lon_new = obs["lon"] #resolução 2.5° 

    #Abrir o arquivo de Hindcast (Resolução 1°)
    if base == "nmme":
        path_fcst =  "/dados/mmclima/multimodelo/seasonal/forecast/nmme"
        models = ["canesm5", "ccsm4","cesm1", "cfsv2", "gem52nemo", "geos5v2", "spear", "bam12"] #"canesm5", "ccsm4","cesm1", "cfsv2", "gem52nemo", "geos5v2", "spear"
    elif base == "copernicus":
        path_fcst =  "/dados/mmclima/multimodelo/seasonal/forecast/copernicus"       
        models = ["ecmwf", "ukmo","meteo_france","dwd","cmcc","ncep","jma","eccc4","eccc5","bom","bam12"]

    for model in models:
        name_model_dir = model if base == "nmme" else ConfigModelos.get_model_dir_c3s(model)
        file_fcst = f"{path_fcst}/{name_model_dir}/{year}/{var}_monthly_{name_model_dir}_fcst_{year}{month_fcst}01.nc"
        file_interp = f"{path_fcst}/{name_model_dir}/{year}/{var}_monthly_{name_model_dir}_fcst_interp_{year}{month_fcst}01.nc"

        # Verifica se já existe o arquivo interpolado
        if os.path.exists(file_interp):
            print(f"Arquivo já interpolado: {file_interp} — pulando.")
            continue

        # Checa se o arquivo existe e se não é muito pequeno (corrompido)
        if not os.path.exists(file_fcst):
            print(f"O arquivo {file_fcst} não foi encontrado — pulando.")
            continue

        if os.path.getsize(file_fcst) < 2000:
            print(f"Arquivo provavelmente corrompido: {file_fcst}")
            continue

        try:
            fcst = xr.open_dataset(file_fcst, decode_times=False)

            if base == "nmme" and model != "bam12":
                ds_interp = fcst.interp(Y=lat_new, X=lon_new, method="linear")
            elif base == "nmme" and model == "bam12":
                ds_interp = fcst.interp(lat=lat_new, lon=lon_new, method="linear")

            elif base == "copernicus" and model != "bam12":
                if fcst.latitude[0] > fcst.latitude[-1]:
                    fcst = fcst.sortby("latitude")
                ds_interp = fcst.interp(latitude=lat_new, longitude=lon_new, method="linear")   
            elif base == "copernicus" and model == "bam12":        
                ds_interp = fcst.interp(lat=lat_new, lon=lon_new, method="linear")   

            ds_interp.to_netcdf(file_interp)
            print(f"Arquivo interpolado: {os.path.basename(file_interp)}")
            fcst.close()

        except Exception as e:
            print(f"Erro ao processar arquivo (provavelmente corrompido): {file_fcst}")
            print(e)
            continue

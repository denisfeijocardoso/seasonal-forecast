import os
import numpy as np
import requests
import pandas as pd
import calendar
from bs4 import BeautifulSoup
from tqdm import tqdm
import xarray as xr
import datetime
from pathlib import Path
import cftime 
import cdsapi
from src.config.config_models_seasonal import ConfigModelos
from src.config.config_dir_seasonal import path_hcst, path_fcst, path_obs

# URL base
base_url_obs = "https://www.ncei.noaa.gov/data/global-precipitation-climatology-project-gpcp-daily/access/"

url_gpcp = "https://psl.noaa.gov/thredds/fileServer/Datasets/gpcp/precip.mon.mean.error.nc"
url_cmap = "https://psl.noaa.gov/thredds/fileServer/Datasets/cmap/std/precip.mon.mean.nc"

#############
#OBSERVATION#
#############

# def download_monthly_obs(url):
#     homedir = Path.home()
#     output_path = homedir/"work/projects/seasonal/data/obs"
#     try:
#         # Envia uma solicitação HTTP GET para a URL
#         response = requests.get(url_gpcp, stream=True)
#         # Verifica se a solicitação foi bem-sucedida (status 200)
#         if response.status_code == 200:
#             # Abre o arquivo no modo de escrita binária e grava os dados do arquivo
#             with open(output_path, 'wb') as file:
#                 for chunk in response.iter_content(chunk_size=8192):  # Lê em pedaços de 8KB
#                     file.write(chunk)
#             print(f"Arquivo baixado com sucesso! Salvo em: {output_path}")
#             url.split("/")[5]
#             os.rename(f"{output_path}/precip.mon.mean.{url.split("/")[5]}nc")
#         else:
#             print(f"Falha ao baixar o arquivo. Status Code: {response.status_code}")
#     except Exception as e:
#         print(f"Erro ao tentar baixar o arquivo: {e}")

def transform_and_split_time_obs(file, output_dir):
    #Mudar a coordenada do tempo no NetCDF das observações para a unidade "ano-mes-dia-hora"
    data_obs = xr.open_dataset(f"{path_obs}/gpcp/{file}", decode_times=False)
    dates_obs = cftime.num2date(data_obs['time'].values, data_obs['time'].units)
    new_time = np.array([np.datetime64(d) for d in dates_obs], dtype='datetime64[D]')
    data_obs['time'] = new_time
    # Garante que diretório de saída existe
    os.makedirs(output_dir, exist_ok=True)

    # Itera sobre todos os índices de tempo
    for i, time_val in enumerate(data_obs['time'].values):
        single_time = np.datetime64(time_val, 'D')

        dt = np.datetime64(single_time).astype(object)  # vira datetime.datetime
        month_abbr = calendar.month_abbr[dt.month]
        month_obs =  f"{dt.month:02d}"
        year = dt.year

        # Seleciona o dado correspondente àquele mês/ano
        print(i)
        data_single = data_obs.isel(time=i).expand_dims("time")
        print(data_single)
        exit()

        # Define nome do arquivo
        outname = f"obs_gpcp_prec_mon_mean_{year}{month_obs}01.nc"
        outfile = os.path.join(output_dir, outname)

        # Salva
        data_single.to_netcdf(outfile)
        print(f"✔ Escreveu: {outfile}")
    return data_obs

file = "obs_gpcp_pr_mon_mean_1979-2025.nc"

file = "obs_gpcp_pr_mon_mean_1979-2025.nc"

output_dir = "/dados/mmclima/multimodelo/seasonal/obs"

###########
#HINDCASTS#
###########

#https://forecast.ccsr.columbia.edu/NMME/COLA-RSMAS/CCSM4/prec.icechunk

def download_hcstfile_nmme(init_year, end_year, model, var):
    periods = pd.date_range(start=f"{init_year}-01-01", end=f"{end_year}-12-31", freq='ME')
    months_period = periods.strftime('%b')
    years_period = periods.strftime('%Y')
    nmme_url = "https://iridl.ldeo.columbia.edu/SOURCES/.Models/.NMME"
    base_urls = {
        "cfsv2": f"{nmme_url}/.NCEP-CFSv2/.HINDCAST/.MONTHLY/.{var}/S",
        "cfsv2_fcst": f"{nmme_url}/.NCEP-CFSv2/.FORECAST/.EARLY_MONTH_SAMPLES/.MONTHLY/{var}/S",
        "canesm5": f"{nmme_url}/.CanSIPS-IC4/.CanESM5/.HINDCAST/.MONTHLY/.{var}/S",
        "gem": f"{nmme_url}/.CanSIPS-IC4/.GEM5.2-NEMO/.HINDCAST/.MONTHLY/.{var}/S",
        "gfdl": f"{nmme_url}/.GFDL-SPEAR/.HINDCAST/.MONTHLY/.{var}/S",
        "cesm1": f"{nmme_url}/.COLA-RSMAS-CESM1/.MONTHLY/.{var}/S",  
        "ccsm4": f"{nmme_url}/.COLA-RSMAS-CCSM4/.MONTHLY/.{var}/S",    
        "geos5v2": f"{nmme_url}/.NASA-GEOSS2S/.HINDCAST/.MONTHLY/.{var}/S",  
        "geos5v2_fcst": f"{nmme_url}/.NASA-GEOSS2S/.FORECAST/.MONTHLY/.{var}/S",  
    }
    base_url_hcst = base_urls.get(model)
    for period in periods:
        year = period.year
        monthstr = period.strftime('%b')
        month_hcst =  f"{period.month:02d}"
        http_url = f"{base_url_hcst}/%280000%201%20{monthstr}%20{year}%29VALUES/data.nc"
        year_dir = f"{path_hcst}/nmme/{model}/{str(year)}"
        if not os.path.exists(year_dir):
            os.makedirs(year_dir)

        # '''Nome do arquivo'''
        if var == "prec":
            file_name = f"{var}_monthly_{model}_hcst_{year}{month_hcst}01.nc"  
        elif var == "tref":
            file_name = file_name = f"t2mt_monthly_{model}_hcst_{year}{month_hcst}01.nc"        
        file_path = os.path.join(year_dir, file_name)

        # Baixa o arquivo
        if os.path.exists(({year_dir}/{file_name})):
            print(f"Arquivo já existe, pulando o download: {year_dir}/{file_name}")
            
        else:
            # ''' Baixar o arquivo '''
            try:
                base_url_hcst = base_urls.get(f"{model}_fcst")
                print(base_url_hcst)
                http_url = f"{base_url_hcst}/%280000%201%20{monthstr}%20{year}%29VALUES/data.nc"
                print(http_url)
                download_response = requests.get(http_url, timeout=300)
                with open(file_path, 'wb') as f:
                    f.write(download_response.content)
                    print(f"Arquivo baixado: {file_path}")   
                # elif file_size is None:
                #     print(f"Arquivo não encontrado em: {http_url}")
                #     continue  # Continua para o próximo URL no loop

            except requests.exceptions.RequestException as e:
                print(f"Ocorreu um erro ao tentar acessar o URL {http_url}: {e}")
                continue  # Caso aconteça um erro, continue com o próximo URL no loop

def download_hcstfile_copernicus(init_year, end_year, init_month, end_month, model, var):
    init_month = f"{init_month:02d}"
    end_month = f"{end_month:02d}"
    #periods = pd.date_range(start=f"{init_year}-{init_month}-01", end=f"{end_year}-{end_month}-30", freq='M')
    periods = pd.period_range(start=f"{init_year}-{init_month}", end=f"{end_year}-{end_month}", freq="M")
    lead_time = ["1","2","3","4","5","6"]

    if var == "total_precipitation":
        var_name_file = "prec"
    elif var == "2m_temperature":
        var_name_file = "t2mt"

    # Versão (system_type) e diretório de destino
    system_type = ConfigModelos.get_model_version(model)
    name_model_dir = ConfigModelos.get_model_dir_c3s(model)

    for period in periods:
        # Definir as datas
        year_hcst = period.year
        month_hcst = f"{period.month:02d}"
        monthstr = period.strftime('%b')

        # Configurações do dataset e modelos
        dataset = "seasonal-monthly-single-levels"

        # Diretorio para salvar os arquivos
        if model in ["eccc4", "eccc5"]:
            year_dir = f"{path_hcst}/copernicus/{name_model_dir}/{str(year_hcst)}"
        else:
            year_dir = f"{path_hcst}/copernicus/{name_model_dir}/{str(year_hcst)}"

        os.makedirs(year_dir, exist_ok=True)

        # Centro de origem
        origin_centre = "eccc" if model in ["eccc4", "eccc5"] else model

        # Requisição
        request = {
            "originating_centre": [origin_centre],
            "system": f"{system_type}",
            "variable": [var],
            "product_type": ["monthly_mean"],
            "year": [f"{year_hcst}"],
            "month": [f"{month_hcst}"],
            "leadtime_month": lead_time,
            "data_format": "netcdf"
        }

        output_file = f"{year_dir}/{var_name_file}_monthly_{name_model_dir}_hcst_{str(year_hcst)}{month_hcst}01.nc"  

        # # Nome do arquivo de saída
        # if model == "ukmo":
        #     output_file = f"{year_dir}/{var_name_file}_monthly_ukmos6v{system_type}_hcst_{year_hcst}{month_hcst}01.nc"  
        # elif model == "ecmwf":
        #     output_file = f"{year_dir}/{var_name_file}_monthly_{model}s5_hcst_{year_hcst}{month_hcst}01.nc"  
        # elif model == "meteo_france":
        #     output_file = f"{year_dir}/{var_name_file}_monthly_mfs{system_type}_hcst_{year_hcst}{month_hcst}01.nc"   
        # elif model in ["eccc4", "eccc5"]:
        #     output_file = f"{year_dir}/{var_name_file}_monthly_ecccs{system_type}_hcst_{year_hcst}{month_hcst}01.nc"
        # else:
        #     output_file = f"{year_dir}/{var_name_file}_monthly_{model}s{system_type}_hcst_{year_hcst}{month_hcst}01.nc"

        # Baixa o arquivo
        if os.path.exists(output_file):
            print(f"Arquivo já existe, pulando o download: {output_file}")
        else:
            print(f"Baixando arquivo: {output_file}")
            try:
                client = cdsapi.Client()
                client.retrieve("seasonal-monthly-single-levels", request).download(output_file)
            except Exception as e:
                print(f" Erro ao baixar {model} ({year_hcst}-{month_hcst}): {e}")


##########
#REALTIME#
##########

def download_realtime_nmme(year, month_num, model, var):
    monthstr = calendar.month_abbr[month_num].capitalize()  # Ex: 4 → 'Apr' 
    month_fcst = f"{month_num:02d}"
    nmme_url = "https://iridl.ldeo.columbia.edu/SOURCES/.Models/.NMME"
    base_urls = {
        "cfsv2": f"{nmme_url}/.NCEP-CFSv2/.FORECAST/.EARLY_MONTH_SAMPLES/.MONTHLY/.{var}/S",
        "canesm5": f"{nmme_url}/.CanSIPS-IC4/.CanESM5/.FORECAST/.MONTHLY/.{var}/S",
        "gem52nemo": f"{nmme_url}/.CanSIPS-IC4/.GEM5.2-NEMO/.FORECAST/.MONTHLY/.{var}/S",
        "spear": f"{nmme_url}/.GFDL-SPEAR/.FORECAST/.MONTHLY/.{var}/S",
        "cesm1": f"{nmme_url}/.COLA-RSMAS-CESM1/.MONTHLY/.{var}/S",  
        "ccsm4": f"{nmme_url}/.COLA-RSMAS-CCSM4/.MONTHLY/.{var}/S",    
        "geos5v2": f"{nmme_url}/.NASA-GEOSS2S/.FORECAST/.MONTHLY/.{var}/S"
    }
    year_dir = f"{path_fcst}/nmme/{model}/{year}"

    if not os.path.exists(year_dir):
        os.makedirs(year_dir)

    # '''Nome do arquivo'''
    if var == "prec":
        file_name = f"{var}_monthly_{model}_fcst_{year}{month_fcst}01.nc"  
    elif var == "tref":
        file_name = f"t2mt_monthly_{model}_fcst_{year}{month_fcst}01.nc"  

    file_path = os.path.join(year_dir, file_name)

    # Verifica se o arquivo já existe
    if os.path.exists(file_path):
        print(f"Arquivo já existe, não precisa baixá-lo: {file_path}")
        return
    # ''' Baixar o arquivo '''
    try:
        base_url_fcst = base_urls.get(model)
        http_url = f"{base_url_fcst}/%280000%201%20{monthstr}%20{year}%29VALUES/data.nc"
        print(http_url)
        download_response = requests.get(http_url, timeout=300)
        with open(file_path, 'wb') as f:
            f.write(download_response.content)
            print(f"Arquivo baixado: {file_path}")   

    except requests.exceptions.RequestException as e:
        print(f"Ocorreu um erro ao tentar acessar o URL {http_url}: {e}")


def download_realtime_copernicus(year, month_num, model, var):
    lead_time = ["1","2","3","4","5","6"]

    if var == "total_precipitation":
        var_name_file = "prec"
    elif var == "2m_temperature":
        var_name_file = "t2mt"

    # Versão (system_type) e diretório de destino
    system_type = ConfigModelos.get_model_version(model)
    name_model_dir = ConfigModelos.get_model_dir_c3s(model)

    # Definir as datas
    month_fcst = f"{month_num:02d}"
    monthstr = calendar.month_abbr[month_num].capitalize()
    dataset = "seasonal-monthly-single-levels"

    # Diretorio para salvar os arquivos
    if model in ["eccc4", "eccc5"]:
        year_dir = f"{path_fcst}/copernicus/{name_model_dir}/{str(year)}"
    else:
        year_dir = f"{path_fcst}/copernicus/{name_model_dir}/{str(year)}"

    os.makedirs(year_dir, exist_ok=True)
    
    origin_centre = "eccc" if model in ["eccc4", "eccc5"] else model

    # Request do download
    request = {
        "originating_centre": [origin_centre],
        "system": f"{system_type}",
        "variable": [
            f"{var}",
        ],
        "product_type": ["monthly_mean"],
        "year": [f"{year}"],
        "month": [f"{month_fcst}"],
        "leadtime_month": [
            "1",
            "2",
            "3",
            "4",
            "5",
            "6"
        ],
        "data_format": "netcdf"
    } 

    # Nome do arquivo de saída
    output_file = f"{year_dir}/{var_name_file}_monthly_{name_model_dir}_fcst_{year}{month_fcst}01.nc"  

    # # Nome do arquivo de saída
    # if model == "ukmo":
    #     output_file = f"{year_dir}/{var_name_file}_monthly_ukmos6v{system_type}_fcst_{year}{month_fcst}01.nc"  
    # elif model == "ecmwf":
    #     output_file = f"{year_dir}/{var_name_file}_monthly_{model}s5_fcst_{year}{month_fcst}01.nc"  
    # elif model == "meteo_france":
    #     output_file = f"{year_dir}/{var_name_file}_monthly_mfs{system_type}_fcst_{year}{month_fcst}01.nc"   
    # elif model in ["eccc4", "eccc5"]:
    #     output_file = f"{year_dir}/{var_name_file}_monthly_ecccs{system_type}_fcst_{year}{month_fcst}01.nc"
    # else:
    #     output_file = f"{year_dir}/{var_name_file}_monthly_{model}s{system_type}_fcst_{year}{month_fcst}01.nc"

    # Baixa o arquivo
    if os.path.exists(output_file):
        print(f"Arquivo já existe, pulando o download: {output_file}")
    else:
        print(f"Baixando arquivo: {output_file}")
        try:
            client = cdsapi.Client()
            client.retrieve("seasonal-monthly-single-levels", request).download(output_file)
        except Exception as e:
            print(f" Erro ao baixar {model} ({year}-{month_fcst}): {e}")



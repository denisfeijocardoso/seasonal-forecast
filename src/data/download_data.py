import os
import numpy as np
import requests
import pandas as pd
import calendar
import xarray as xr
import logging
from pathlib import Path
import cftime 
import cdsapi
from src.config.loader import VARIABLES_CONFIG
from src.config.paths import PATH_FCST, PATH_HCST, PATH_OBS
from src.config.config_models import get_model_version, build_model_dir_name

logger = logging.getLogger(__name__)

# URL base
base_url_obs = "https://www.ncei.noaa.gov/data/global-precipitation-climatology-project-gpcp-daily/access/"

url_gpcp = "https://psl.noaa.gov/thredds/fileServer/Datasets/gpcp/precip.mon.mean.error.nc"

url_cmap = "https://psl.noaa.gov/thredds/fileServer/Datasets/cmap/std/precip.mon.mean.nc"

#############
#OBSERVATION#
#############

def download_monthly_obs(url):

    homedir = Path.home()

    output_path = homedir/"work/projects/seasonal/data/obs"
    try:
        # Envia uma solicitação HTTP GET para a URL
        response = requests.get(url_gpcp, stream=True)
        # Verifica se a solicitação foi bem-sucedida (status 200)
        if response.status_code == 200:
            # Abre o arquivo no modo de escrita binária e grava os dados do arquivo
            with open(output_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):  # Lê em pedaços de 8KB
                    file.write(chunk)
            print(f"Arquivo baixado com sucesso! Salvo em: {output_path}")
            url.split("/")[5]
            os.rename(f"{output_path}/precip.mon.mean.{url.split("/")[5]}nc")
        else:
            print(f"Falha ao baixar o arquivo. Status Code: {response.status_code}")
    except Exception as e:
        print(f"Erro ao tentar baixar o arquivo: {e}")

def transform_and_split_time_obs(file, output_dir):
    #Mudar a coordenada do tempo no NetCDF das observações para a unidade "ano-mes-dia-hora"
    data_obs = xr.open_dataset(f"{PATH_OBS}/gpcp/{file}", decode_times=False)
    
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


###########
#HINDCASTS#
###########

def download_hcstfile_nmme(
        init_year: int, 
        end_year: int, 
        model: str, 
        var: str
    ):

    dates_climatology = pd.date_range(start=f"{init_year}-01-01", end=f"{end_year}-12-31", freq='ME')

    nmme_url = "https://iridl.ldeo.columbia.edu/SOURCES/.Models/.NMME"
    
    var_download = VARIABLES_CONFIG[var]["nmme_iri"]["variable"]

    base_urls = {
        "cfs": f"{nmme_url}/.NCEP-CFSv2/.HINDCAST/.MONTHLY/.{var_download}/S",

        "cfs_fcst": f"{nmme_url}/.NCEP-CFSv2/.FORECAST/.EARLY_MONTH_SAMPLES/.MONTHLY/{var_download}/S",

        "canesm": f"{nmme_url}/.CanSIPS-IC4/.CanESM5/.HINDCAST/.MONTHLY/.{var_download}/S",

        "gemnemo": f"{nmme_url}/.CanSIPS-IC4/.GEM5.2-NEMO/.HINDCAST/.MONTHLY/.{var_download}/S",

        "spear": f"{nmme_url}/.GFDL-SPEAR/.HINDCAST/.MONTHLY/.{var_download}/S",

        "cesm": f"{nmme_url}/.COLA-RSMAS-CESM1/.MONTHLY/.{var_download}/S",  

        "ccsm": f"{nmme_url}/.COLA-RSMAS-CCSM4/.MONTHLY/.{var_download}/S",  

        "geos": f"{nmme_url}/.NASA-GEOSS2S/.HINDCAST/.MONTHLY/.{var_download}/S",  

        "geos_fcst": f"{nmme_url}/.NASA-GEOSS2S/.FORECAST/.MONTHLY/.{var_download}/S",  
    }

    base_url_hcst = base_urls.get(model)
    name_model_dir = build_model_dir_name(model)

    for date_clim in dates_climatology:

        year = date_clim.year

        monthstr = date_clim.strftime('%b')

        month_hcst =  f"{date_clim.month:02d}"

        http_url = f"{base_url_hcst}/%280000%201%20{monthstr}%20{year}%29VALUES/data.nc"

        download_path = (
            PATH_HCST/
            "nmme" / 
            name_model_dir /
            str(year)
        )
        
        download_path.mkdir(
            parents=True,
            exist_ok=True
        )

        file_name = f"{var}_monthly_{name_model_dir}_hcst_{year}{month_hcst}01.nc"  

        file_path = (
            download_path / 
            file_name
        )

        if file_path.exists():
            
            logger.info(
                f"NMME: Arquivo já existe, pulando o download: {file_path}"
            )
            
        else:

            base_url_hcst = base_urls.get(f"{model}_fcst")

            http_url = f"{base_url_hcst}/%280000%201%20{monthstr}%20{year}%29VALUES/data.nc"

            try:

                logger.info(
                    f"Baixando {http_url}"
                )

                download_response = requests.get(
                    http_url, 
                    timeout=300
                )

                with open(file_path, "wb") as f:

                    f.write(
                        download_response.content
                    )
                
                # Verifica se o arquivo é um NetCDF válido
                xr.open_dataset(
                    file_path,
                    decode_times=False,
                ).close()

                logger.info(
                    f"NMME: Arquivo baixado: {file_path}"
                )

            except requests.exceptions.RequestException as e:

                logger.error(
                    f"NMME: Erro ao acessar {http_url}: {e}"
                )

            except Exception as e:

                file_path.unlink(
                    missing_ok=True
                )

                logger.warning(
                    f"NMME: Arquivo inválido ou indisponível: {file_path} ({e})"
                )

def download_hcstfile_copernicus(
        init_year: int, 
        end_year: int, 
        init_month: int, 
        end_month: int, 
        model: str, 
        var: str
):
    init_month = f"{init_month:02d}"
    end_month = f"{end_month:02d}"

    dates_climatology = pd.period_range(start=f"{init_year}-{init_month}", end=f"{end_year}-{end_month}", freq="M")

    lead_time =[str(i) for i in range(1, 7)]

    var_download = VARIABLES_CONFIG[var]["copernicus"]["variable"]

    # Versão (system_type) e diretório de destino
    system_type = get_model_version(model)
    name_model_dir = build_model_dir_name(model)

    for date_clim in dates_climatology:

        year_hcst = date_clim.year
        month_hcst = f"{date_clim.month:02d}"
        monthstr = date_clim.strftime('%b')

        # Configurações do dataset e modelos
        dataset = "seasonal-monthly-single-levels"

        download_path = (
            PATH_HCST /
            "copernicus" /
            name_model_dir / 
            str(year_hcst)
        )

        download_path.mkdir(
            parents = True, 
            exist_ok = True
        )

        # Centro de origem
        origin_centre = "eccc" if model in ["eccc4", "eccc5"] else model

        # Requisição
        request = {

            "originating_centre": [origin_centre],

            "system": f"{system_type}",

            "variable": [var_download],

            "product_type": ["monthly_mean"],

            "year": [f"{year_hcst}"],

            "month": [f"{month_hcst}"],

            "leadtime_month": lead_time,

            "data_format": "netcdf"
        }

        file_name = f"{var}_monthly_{name_model_dir}_hcst_{year_hcst}{month_hcst}01.nc"  

        file_path = (
            download_path / 
            file_name
        )

        # Baixa o arquivo
        if file_path.exists():
            logger.info(f"C3S: Arquivo já existe, pulando o download: {file_path}")

        else:
            
            try:

                client = cdsapi.Client()

                client.retrieve(
                    dataset,
                    request
                ).download(file_path)

            except Exception as e:

                logger.error(
                    f"C3S: Erro ao baixar {model} "
                    f"({year_hcst}-{month_hcst}): {e}"
                )

                continue

            try:

                xr.open_dataset(
                    file_path,
                    decode_times=False,
                ).close()

                logger.info(
                    f"C3S: Arquivo baixado: {file_path}"
                )

            except Exception as e:

                file_path.unlink(
                    missing_ok=True
                )

                logger.warning(
                    f"C3S: Arquivo inválido: "
                    f"{file_path} ({e})"
                )


##########
#REALTIME#
##########

def download_realtime_nmme(
        year_fcst: int,
        month_fcst: int,
        model: str,
        var: str
):

    monthstr = calendar.month_abbr[month_fcst].capitalize()

    month_fcst = f"{month_fcst:02d}"

    nmme_url = "https://iridl.ldeo.columbia.edu/SOURCES/.Models/.NMME"

    var_download = VARIABLES_CONFIG[var]["nmme_iri"]["variable"]

    base_urls = {
        "cfs": f"{nmme_url}/.NCEP-CFSv2/.FORECAST/.EARLY_MONTH_SAMPLES/.MONTHLY/.{var_download}/S",

        "canesm": f"{nmme_url}/.CanSIPS-IC4/.CanESM5/.FORECAST/.MONTHLY/.{var_download}/S",

        "gemnemo": f"{nmme_url}/.CanSIPS-IC4/.GEM5.2-NEMO/.FORECAST/.MONTHLY/.{var_download}/S",

        "spear": f"{nmme_url}/.GFDL-SPEAR/.FORECAST/.MONTHLY/.{var_download}/S",

        "cesm": f"{nmme_url}/.COLA-RSMAS-CESM1/.MONTHLY/.{var_download}/S",

        "ccsm": f"{nmme_url}/.COLA-RSMAS-CCSM4/.MONTHLY/.{var_download}/S",

        "geos": f"{nmme_url}/.NASA-GEOSS2S/.FORECAST/.MONTHLY/.{var_download}/S"
    }

    name_model_dir = build_model_dir_name(model)

    download_path = (
        PATH_FCST /
        "nmme" /
        name_model_dir /
        str(year_fcst)
    )

    download_path.mkdir(
        parents=True,
        exist_ok=True
    )

    file_name = (
        f"{var}_monthly_"
        f"{name_model_dir}_fcst_"
        f"{year_fcst}{month_fcst}01.nc"
    )

    file_path = (
        download_path /
        file_name
    )

    # Verifica se o arquivo já existe
    if file_path.exists():

        logger.info(
            f"NMME: Arquivo já existe: {file_path}"
        )

        return

    base_url_fcst = base_urls.get(model)

    http_url = (
        f"{base_url_fcst}/"
        f"%280000%201%20{monthstr}%20{year_fcst}%29VALUES/"
        f"data.nc"
    )

    try:

        logger.info(
            f"NMME: Baixando {http_url}"
        )

        download_response = requests.get(
            http_url,
            timeout=300
        )

        download_response.raise_for_status()

        with open(file_path, "wb") as f:

            f.write(
                download_response.content
            )

        # Verifica se o arquivo é um NetCDF válido
        xr.open_dataset(
            file_path,
            decode_times=False,
        ).close()

        logger.info(
            f"NMME: Arquivo baixado: {file_path}"
        )

    except requests.exceptions.RequestException as e:

        logger.error(
            f"NMME: Erro ao acessar {http_url}: {e}"
        )

    except Exception as e:

        file_path.unlink(
            missing_ok=True
        )

        logger.warning(
            f"NMME: Arquivo inválido ou indisponível: {file_path} ({e})"
        )

def download_realtime_copernicus(
        year_fcst: int, 
        month_fcst: int, 
        model: str, 
        var: str
):

    lead_time = [str(i) for i in range(1, 7)]

    var_download = VARIABLES_CONFIG[var]["copernicus"]["variable"]

    system_type = get_model_version(model)
    name_model_dir = build_model_dir_name(model)

    # Definir as datas
    monthstr = calendar.month_abbr[month_fcst].capitalize()
    month_fcst = f"{month_fcst:02d}"
    dataset = "seasonal-monthly-single-levels"

    # Diretorio para salvar os arquivos
    download_path = (
        PATH_FCST / 
        "copernicus" / 
        name_model_dir /
        str(year_fcst) 
    )

    download_path.mkdir(
        parents = True,
        exist_ok = True
    )
    
    origin_centre = "eccc" if model in ["eccc4", "eccc5"] else model

    # Request do download
    request = {
        "originating_centre": [origin_centre],

        "system": f"{system_type}",

        "variable": [var_download],

        "product_type": ["monthly_mean"],

        "year": [f"{year_fcst}"],

        "month": [f"{month_fcst}"],

        "leadtime_month": lead_time,

        "data_format": "netcdf"
    } 

    file_name = f"{var}_monthly_{name_model_dir}_fcst_{year_fcst}{month_fcst}01.nc"  

    file_path = (
        download_path / 
        file_name
    )
    

    # Baixa o arquivo
    if file_path.exists():
        
        logger.info(f"C3S: Arquivo já existe, pulando o download: {file_path}")

    else:

        try:
            client = cdsapi.Client()

            client.retrieve(
                dataset, 
                request
            ).download(file_path)

        except Exception as e:

            logger.error(
                f"C3S: Erro ao baixar {model} "
                f"({year_fcst}-{month_fcst}): {e}"
            )

            return

        try:

            xr.open_dataset(
                file_path,
                decode_times=False,
            ).close()

            logger.info(
                f"C3S: Arquivo baixado: {file_path}"
            )

        except Exception as e:

            file_path.unlink(
                missing_ok=True
            )

            logger.warning(
                f"C3S: Arquivo inválido: "
                f"{file_path} ({e})"
            )

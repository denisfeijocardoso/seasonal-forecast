from src.data.download_data import download_hcstfile_nmme, download_hcstfile_copernicus
from src.data.download_data import download_realtime_nmme, download_realtime_copernicus


def run_download_forecast(
        base: str,
        model: str,
        var: str,
        year_fcst: int, 
        month_fcst: int, 
    ):
        
        if base == "nmme":
            download_realtime_nmme(
                year_fcst, 
                month_fcst, 
                model, 
                var
            )

        elif base == "copernicus":
            download_realtime_copernicus(
                year_fcst, 
                month_fcst, 
                model, 
                var
            )

        else:
            raise ValueError(f"Base desconhecida: {base}")



def run_download_hindcast_c3s(month_fcst):
    """ Executa o download dos hindcasts do Copernicus Climate Data Store (C3S)
    para um mês de previsão específico.

    Parâmetros
    ----------
    month_fcst : int Mês de inicialização da previsão (1 a 12). """
    
    models = ["ukmo", "ecmwf", "meteo_france", "dwd", "cmcc",
        "ncep", "jma", "eccc4", "eccc5", "bom"]
    
    variables = ["total_precipitation","2m_temperature"]
    
    years = range(1993, 2017)

    for year in years:
        for model in models:
            for var in variables:
                download_hcstfile_copernicus(year, year, month_fcst, month_fcst, model, var)
    #

def run_download_hindcast_nmme(init_year, end_year):
    """ Executa o download dos hindcasts do North American Multi-Model Ensemble (NMME)
    para um mês de previsão específico.

    Parâmetros
    ----------
    init_year : Ano de início do download (ele vai baixar todos os meses)
    end_year : Ano de fim do período de download """

    models_nmme = ["canesm5", "ccsm4", "cesm1", "cfsv2", "gem52nemo", "geos5v2", "spear"] 
    vars_nmme = ["total_precipitation", "2m_temperature"]
    #
    for model in models_nmme:
        for var in vars_nmme:
            download_hcstfile_nmme(init_year, end_year, model, var)
    #

    print("Interpolando os dados de previsão hindcast dos modelos para a mesma grade da observação (GPCP)")  

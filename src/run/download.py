from src.data.download_data import download_hcstfile_nmme, download_hcstfile_copernicus
from src.data.download_data import download_realtime_nmme, download_realtime_copernicus
from src.config.loader import VARIABLES_CONFIG, PARAMETERS_RUN

def run_download_realtime_models(
    base: str,
    models: list[str],
    var: str,
    year_fcst: int,
    month_fcst: int
) -> None:

    for model in models:

        download_realtime_forecast(
            base,
            model,
            var,
            year_fcst,
            month_fcst
        )

def download_realtime_forecast(
        base: str,
        model: str,
        var: str,
        year_fcst: int, 
        month_fcst: int, 
    ) -> None:

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


def download_hindcast_c3s(        
        model: str,
        var: str,
        month_fcst: int, 
    ):
    """ Executa o download dos hindcasts do Copernicus Climate Data Store (C3S),
    para todo o período climatológico, dado um modelo, variável e mês específicos."""
    
    var_name_in_base = VARIABLES_CONFIG[var]["copernicus"]["variable"]

    #Define climatology
    years_climatology = PARAMETERS_RUN["bases"]["copernicus"]["climatology"]
    start_year = years_climatology["start_year"]
    end_year = years_climatology["end_year"]

    for year in range(start_year, end_year + 1):

        download_hcstfile_copernicus(
            year, 
            year, 
            month_fcst, 
            month_fcst, 
            model, 
            var_name_in_base
        )

def download_hindcast_nmme(        
        model: str,
        var: str,
        month_fcst: int, 
    ):
    """ Executa o download dos hindcasts do  North American Multi-Model Ensemble (NMME),
    para todo o período climatológico, dado um modelo, variável e mês específicos."""

    var_name_in_base = VARIABLES_CONFIG[var]["copernicus"]["variable"]

    #Define climatology
    years_climatology = PARAMETERS_RUN["bases"]["copernicus"]["climatology"]
    start_year = years_climatology["start_year"]
    end_year = years_climatology["end_year"]

    for year in range(start_year, end_year + 1):

        download_hcstfile_nmme(
            start_year, 
            end_year, 
            model, 
            var
        )


    # print("Interpolando os dados de previsão hindcast dos modelos para a mesma grade da observação (GPCP)")  

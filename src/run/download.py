from src.data.download_data import download_hcstfile_nmme, download_hcstfile_copernicus
from src.data.download_data import download_realtime_nmme, download_realtime_copernicus
from src.config.loader import PARAMETERS_RUN
from src.config.paths import PATH_HCST
from src.config.config_models import build_model_dir_name, get_list_models


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


def run_download_hindcast_models(
    base: str,
    models: list[str],
    var: str,
    month_hcst: int,
) -> None:
    for model in models:
        download_hindcast(
            base,
            model,
            var,
            month_hcst,
        )


def download_hindcast(
    base: str,
    model: str,
    var: str,
    month_hcst: int,
) -> None:
    if base == "nmme":
        download_hindcast_nmme(
            model,
            var,
            month_hcst,
        )
    elif base == "copernicus":
        download_hindcast_c3s(
            model,
            var,
            month_hcst,
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
            var
        )

def download_hindcast_nmme(        
        model: str,
        var: str,
        month_fcst: int, 
    ):
    """ Executa o download dos hindcasts do  North American Multi-Model Ensemble (NMME),
    para todo o período climatológico, dado um modelo, variável e mês específicos."""

    #Define climatology
    years_climatology = PARAMETERS_RUN["bases"]["nmme"]["climatology"]
    start_year = years_climatology["start_year"]
    end_year = years_climatology["end_year"]

    download_hcstfile_nmme(
        start_year,
        end_year,
        model,
        var,
    )


    # print("Interpolando os dados de previsão hindcast dos modelos para a mesma grade da observação (GPCP)")  


def find_missing_c3s_hindcasts() -> dict[str, dict[str, list[int]]]:
    """Lista meses de hindcast Copernicus faltantes por modelo e variável.

    Checa somente os arquivos originais, sem o sufixo ``_interp``. A interpolação
    deve ser executada depois do download dos NetCDF brutos.
    """

    models = get_list_models("copernicus")
    variables = PARAMETERS_RUN["variables"]

    years_climatology = PARAMETERS_RUN["bases"]["copernicus"]["climatology"]
    start_year = years_climatology["start_year"]
    end_year = years_climatology["end_year"]

    missing: dict[str, dict[str, list[int]]] = {}

    for model in models:
        model_dir = build_model_dir_name(model)

        for var in variables:
            missing_months = []

            for month in range(1, 13):
                month_is_complete = True

                for year in range(start_year, end_year + 1):
                    file_path = (
                        PATH_HCST
                        / "copernicus"
                        / model_dir
                        / str(year)
                        / f"{var}_monthly_{model_dir}_hcst_{year}{month:02d}01.nc"
                    )

                    if not file_path.exists():
                        month_is_complete = False
                        break

                if not month_is_complete:
                    missing_months.append(month)

            if missing_months:
                missing.setdefault(model, {})[var] = missing_months

    return missing


def main() -> None:
    missing = find_missing_c3s_hindcasts()

    if not missing:
        print("Nenhum hindcast Copernicus faltante encontrado.")
        return

    print("Hindcasts Copernicus faltantes:")
    for model, vars_missing in missing.items():
        model_dir = build_model_dir_name(model)
        print(f"\n{model} ({model_dir})")

        for var, months in vars_missing.items():
            months_str = ", ".join(f"{month:02d}" for month in months)
            print(f"  {var}: {months_str}")

    print("\nIniciando downloads...")

    for model, vars_missing in missing.items():
        for var, months in vars_missing.items():
            for month in months:
                print(f"Baixando {model} {var} mes {month:02d}")
                download_hindcast_c3s(
                    model=model,
                    var=var,
                    month_fcst=month,
                )


if __name__ == "__main__":
    main()

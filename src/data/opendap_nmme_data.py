import xarray as xr
from src.config.loader import MODELS_CONFIG, VARIABLES_CONFIG

class NMMEData():

    NMME_OPENDAP_URL  = "https://forecast.ccsr.columbia.edu/data/NMME"

    #Para os modelos abaixo, os dados de hindcast e forecast estão no mesmo diretório
    MODELS_WITH_COMBINED_DATA = {
        "ccsm",
        "cesm"
    }

    VALID_DATA_TYPES = {
        "forecast",
        "hindcast"
    }

    def __init__(
            self,
            model: str,
            var: str,
            year: int,
            month: int,
            data_type: str = "forecast"

    ):
        self.model = model
        self.var = var
        self.year = year
        self.month = month
        self.data_type = data_type
        self.ds = None
        

    def build_nmme_url(self) -> str:
        
        try:

            parameters_opendap = MODELS_CONFIG["models"][self.model]["opendap"]
            
            center_name = parameters_opendap["center"]
            mdl_name = parameters_opendap["directory"]
            var_name = VARIABLES_CONFIG[self.var]["nmme"]["variable"]

            url_parts =[
                self.NMME_OPENDAP_URL,
                center_name,
                mdl_name,
            ]

            if self.model not in self.MODELS_WITH_COMBINED_DATA:
                url_parts.append(self.data_type)  

            url_parts.append(var_name)

            return "/".join(url_parts)      

        except KeyError:
            raise ValueError(f"Modelo não disponível no OpenDAP: {self.model}")


    def open_dataset(self) -> xr.Dataset:
        
        self.ds = xr.open_dataset(
            self.build_nmme_url(), 
            decode_times=True
        )

        return self.ds
    
    def validate_time(self) -> None:
        
        target = f"{self.year}-{self.month:02d}"

        available = self.ds.S.dt.strftime(
            "%Y-%m"
        ).values

        if target not in available:

            raise ValueError(
                f"{target} não disponível em {self.model}"
            )
        
    def select_time(self) -> xr.Dataset:

        if self.ds is None:
            raise ValueError(
                "Dataset ainda não foi aberto."
            )

        self.validate_time()  

        return self.ds.sel(
            S=f"{self.year}-{self.month:02d}"
        )
    
    def write_netcdf(
            self
    ):

        subset = self.select_time()

        subset.to_netcdf(
            f"teste_{self.model}.nc"
        )

        print(f"teste_{self.model}.nc gerado")

    
    
models = list(MODELS_CONFIG["nmme"]["models"].keys())
var = list(VARIABLES_CONFIG.keys())[0]

for mdl in models:

    try:
        nmme = NMMEData(
            mdl,
            var,
            2026,
            5
        )

        nmme.open_dataset()
        nmme.write_netcdf()

    except ValueError as e:
        
        print(e)

        continue

    except Exception as e:

        print(f"Erro inesperado em {mdl}: {e}")

        continue
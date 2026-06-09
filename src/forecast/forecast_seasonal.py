import xarray as xr
from src.config.config_models import build_model_dir_name, get_dim_names
from src.processing.data_processing import build_periods_model
from src.config.loader import PARAMETERS_RUN
from src.config.config_path import PATH_FCST

class Forecast:
     
    def __init__(
            self, 
            base: str, 
            var: str,
            year_fcst: int, 
            month_fcst: int,
            models_available: list[str]
    ):
        
        self.base = base
        self.var = var
        self.year_fcst = year_fcst
        self.month_fcst = month_fcst
        self.models_available = models_available

        self.periods = PARAMETERS_RUN["periods"]

    def load_forecast(
            self, 
            model:str
    ) -> xr.DataArray:
        ''' Carrega os dados das previsões em tempo-real para um modelo específico.'''

        name_model = build_model_dir_name(
            self.base,
            model
        )

        file_path = (
            PATH_FCST /
            self.base /
            name_model /
            str(self.year_fcst) /
            f"{self.var}_monthly_{name_model}_fcst_interp_{self.year_fcst}{self.month_fcst:02d}01.nc"
        )

        ds = xr.open_dataset(file_path, decode_times=False)

        ds = ds.squeeze()
        
        if len(ds.data_vars) != 1:
            raise ValueError(
                f"Esperava 1 variável, encontrei {list(ds.data_vars)}"
            )

        var_name = next(iter(ds.data_vars))
        da = ds[var_name]

        dims = get_dim_names(self.base, model)

        #Média Ensemble
        if model != "echam":
            da = da.mean(dim=dims["member"], skipna=True)

        #Conversão de precipitação (m/s -> mm/dia)
        if (
            self.base == "copernicus" 
            and self.var == "prec"
            and model not in ("bam12","echam")
        ): 
            da = (da * 1000  * 86400)

        return da

    def calculate_periods_forecast(
        self,
        model: str
    ) -> dict[str, xr.DataArray]:
        '''Processa as previsões em tempo-real para um modelo específico
        para todos os períodos de acumulo/média'''

        da = self.load_forecast(model)

        model_fcst = build_periods_model(
                model, 
                self.var,
                self.year_fcst,
                self.month_hcst,
                da
        )

        return model_fcst

    def load_forecast_models_available(self) -> dict[str, dict[str, xr.DataArray]]:    
        '''Processa as previsões em tempo-real para cada modelo disponível
        para todos os períodos de acumulo/média'''

        model_fcsts = {}
        
        for model in self.models_available: 

            model_fcsts[model] = self.calculate_periods_forecast(model)

        return model_fcsts

    def generate_multimodel_forecast(self):
        '''Calcula a média multimodelo para todos os períodos de acúmulo/media
        a partir dos modelos disponíveis'''  

        # Verifica se há mais de um modelo disponível
        if len(self.models_available) < 2:
            raise ValueError(
                "São necessários pelo menos 2 modelos para calcular o multimodelo."
            )
        
        fcst_models = self.load_forecast_models_available()
        
        multimodel = {}
            
        for period in self.periods:
            
            arrays = [
                fcst_models[model][period]
                .expand_dims(model=[model])
                for model in self.models_available
            ]

            multimodel[period] = (
                xr.concat(arrays, dim="model")
                .mean(dim="model", skipna=True)
            )

        return multimodel

    def generate_forecast(
            self,
            model: str
    ):
        if model == "multimodel":
            return self.generate_multimodel_forecast()
            
        return self.calculate_periods_forecast(model)
    
    # def get_periods_fcst(
    #         self, 
    #         model: str,
    #         data: xr.DataArray,
    # ) -> dict[str, xr.DataArray]:
    #     '''Gera os agregados (acumulados/médias) para os trimestres e meses.
    #     Importante: os períodos mensais devem vir antes dos sazonais no arquivo de configuração'''

    #     periods_fcst = {} 

    #     for period, (start, end) in self.periods.items():

    #         is_mensal = period.startswith("mnth") 

    #         if is_mensal:

    #             new_date = date(self.year_fcst, self.month_fcst, 1) + relativedelta(months=start) #soma um mes
                
    #             ndays = calendar.monthrange(
    #                 new_date.year, 
    #                 new_date.month
    #             )[1]

    #             sel = select_month(start, end, data)    

    #             if model != "echam" and self.var == "prec":
    #                 sel = sel * ndays  
    #             elif self.var == "t2mt":
    #                 sel = sel - 273.15 

    #             periods_fcst[period] = sel.squeeze()

    #         else:

    #             if model != "echam" and self.var == "prec":   
    #                 periods_fcst[period] = aggregate_season(
    #                     period,
    #                     periods_fcst
    #                 )        
                    
    #             elif model == "echam" or self.var == "t2mt":
    #                 periods_fcst[period] = aggregate_season(
    #                     period,
    #                     periods_fcst,
    #                     mean = True
    #                 )        

    #     return periods_fcst
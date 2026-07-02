import xarray as xr
from src.config.config_models import build_model_dir_name, get_dim_names
from src.processing.data_processing import build_periods_model
from src.config.loader import get_periods_aggregation, get_climatology_period
from src.config.paths import PATH_HCST

class Hindcast:
    """Dados de previsão retrospectiva (hindcast)."""

    def __init__(
            self, 
            base: str, 
            var: str,
            month_hcst: int,
            models_available: list[str]
    ):
        
        self.base = base
        self.var = var
        self.month_hcst = month_hcst
        self.models_available = models_available

        self.periods = get_periods_aggregation()

    def _standardize_dims(
        self,
        da: xr.DataArray,
        model: str,
        keep_member: bool = False
    ) -> xr.DataArray:

        dims = get_dim_names(self.base, model)

        rename_dims = {}

        if dims["lat"] in da.dims:
            rename_dims[dims["lat"]] = "lat"

        if dims["lon"] in da.dims:
            rename_dims[dims["lon"]] = "lon"

        if keep_member and dims["member"] in da.dims:
            rename_dims[dims["member"]] = "member"

        return da.rename(rename_dims)

    def load_year(
        self, 
        model:str,
        year_hcst: int
    ) -> dict[str, xr.DataArray]:
        ''' Carrega os hindcasts para um determinado modelo e ano de climatologia '''

        name_model = build_model_dir_name(model)       

        file_path = (
            PATH_HCST / 
            self.base / 
            name_model/
            str(year_hcst)/
            f"{self.var}_monthly_{name_model}_hcst_interp_{year_hcst}{self.month_hcst:02d}01.nc"
        )

        with xr.open_dataset(file_path, decode_times=False) as ds:
            #ds = xr.open_dataset(file_path, decode_times=False)
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

            da = self._standardize_dims(da, model)

            periods = build_periods_model(
                model, 
                self.var,
                year_hcst,
                self.month_hcst,
                da
            )

            periods_loaded = {
                k: y.load()
                for k,y in periods.items()
            }

            return periods_loaded

    def load_year_members(
        self, 
        model: str,
        year_hcst: int
    ) -> dict[str, xr.DataArray]:
        '''Carrega hindcast mantendo a dimensão dos membros.'''

        name_model = build_model_dir_name(model)       

        file_path = (
            PATH_HCST / 
            self.base / 
            name_model/
            str(year_hcst)/
            f"{self.var}_monthly_{name_model}_hcst_interp_{year_hcst}{self.month_hcst:02d}01.nc"
        )

        with xr.open_dataset(file_path, decode_times=False) as ds:
            ds = ds.squeeze()

            if len(ds.data_vars) != 1:
                raise ValueError(
                    f"Esperava 1 variável, encontrei {list(ds.data_vars)}"
                )

            var_name = next(iter(ds.data_vars))
            da = ds[var_name]

            if (
                self.base == "copernicus" 
                and self.var == "prec"
                and model not in ("bam12", "echam")
            ): 
                da = da * 1000 * 86400

            da = self._standardize_dims(
                da,
                model,
                keep_member=True
            )

            periods = build_periods_model(
                model, 
                self.var,
                year_hcst,
                self.month_hcst,
                da
            )

            periods_loaded = {
                k: y.load()
                for k,y in periods.items()
            }

            return periods_loaded

    def load_years_climatology(
        self, 
        model: str
    )  -> dict[str, xr.DataArray]:
        '''Carrega os hindcasts de um determinado modelo 
        e gera os agregados para todo período de climatologia'''

        start_year, end_year = get_climatology_period(self.base)

        years_climatology = range(
            start_year, 
            end_year + 1
        )

        periods_by_year = {
            period: []
            for period in self.periods
        }

        for year in years_climatology:

            periods = self.load_year(
                model, 
                year
            )

            for period, da in periods.items():
                
                da = da.expand_dims(year=[year])
                periods_by_year[period].append(da)

        hindcast = {}

        for period, das in periods_by_year.items():

            hindcast[period] = xr.concat(
                das,
                dim="year"
            )

        return hindcast 

    def load_years_climatology_members(
        self,
        model: str
    ) -> dict[str, xr.DataArray]:
        '''Carrega hindcasts com membros para todo o período climatológico.'''

        start_year, end_year = get_climatology_period(self.base)

        years_climatology = range(
            start_year, 
            end_year + 1
        )

        periods_by_year = {
            period: []
            for period in self.periods
        }

        for year in years_climatology:

            periods = self.load_year_members(
                model, 
                year
            )

            for period, da in periods.items():

                if model == "cfs" and "member" in da.dims:
                    da = da.isel(member=slice(0, 24))

                if model == "geos" and "member" in da.dims:
                    da = da.isel(member=slice(0, 4))
                
                da = da.expand_dims(year=[year])
                periods_by_year[period].append(da)

        hindcast = {}

        for period, das in periods_by_year.items():

            hindcast[period] = xr.concat(
                das,
                dim="year"
            )

        return hindcast


    def load_available_models(self) -> dict[str, dict[str, xr.DataArray]]:    
        '''Processa os hindcasts para cada modelo da lista models_available
        para todos os períodos de agregamento'''

        model_hcsts = {}
        
        for model in self.models_available: 

            model_hcsts[model] = self.load_years_climatology(model)

        return model_hcsts

    def build_multimodel(self) -> dict[str, xr.DataArray]:
        '''Calcula a média multimodelo para todos os períodos de agregamento
        a partir dos modelos disponíveis na lista models_available'''  

        if len(self.models_available) < 2:
            raise ValueError(
                "São necessários pelo menos 2 modelos para calcular o multimodelo."
            )
        
        hcst_models = self.load_available_models()
        
        multimodel = {}
            
        for period in self.periods:
            
            arrays = [
                hcst_models[model][period]
                .expand_dims(model=[model])
                for model in self.models_available
            ]

            multimodel[period] = (
                xr.concat(arrays, dim="model")
                .mean(dim="model", skipna=True)
            )

        return multimodel

    def get_hindcast(
        self,
        model: str
    ):
        if model == "multimodel":
            return self.build_multimodel()
            
        return self.load_years_climatology(model)        

    def get_hindcast_target(
        self,
        model: str,
        target_year: int
    ) -> dict[str, xr.DataArray]:

        if model == "multimodel":
            hcst_models = {}

            for available_model in self.models_available:
                hcst_models[available_model] = self.load_year(
                    available_model,
                    target_year
                )

            target = {}

            for period in self.periods:

                arrays = [
                    hcst_models[available_model][period]
                    .expand_dims(model=[available_model])
                    for available_model in self.models_available
                ]

                target[period] = (
                    xr.concat(arrays, dim="model")
                    .mean(dim="model", skipna=True)
                )

            return target

        return self.load_year(
            model,
            target_year
        )

    def compute_statistics(
        self, 
        model: str,
        exclude_year: int | None = None
    ) -> dict[str, dict[str, xr.DataArray]]:
        '''Calcula estatísticas climatológicas dos hindcasts.'''

        hcst = self.get_hindcast(model)

        hcst_statistics = {}

        for period, da in hcst.items():

            climatology = da

            if exclude_year is not None:
                climatology = da.drop_sel(
                    year=exclude_year,
                    errors="ignore"
                )

            mean = climatology.mean("year")

            hcst_statistics[period] ={
                "mean": mean,
                "std": climatology.std("year"),
                "anom": climatology - mean
            }

        return hcst_statistics

    # def mean_std_anom_hindcast_gamma(self, model):
    #     '''Calcula a média e o desvio padrão  da climatologia dos hindcasts'''
    #     if model == "multimodel":
    #         model_hcst = self.hindcast_multimodel(self.base, year_fcst, month_fcst, self.var)
    #         hcst_mean = np.nanmean(model_hcst, axis = 0)
    #         hcst_std = np.nanstd(model_hcst, axis = 0)
    #         hcst_var = np.nanvar(model_hcst, axis = 0)
    #         hcst_anomaly = (model_hcst) - (hcst_mean)
    #     else:
    #         hcst_dict = self.climatology_model_hcst(self.base, month_fcst, model, self.var)
    #         model_hcst = self.dict_to_array(self.base, hcst_dict, ["mnth00","mnth01","mnth02","mnth03","mnth04","seas00","seas01","seas02"], self.var)
    #         hcst_mean = np.nanmean(model_hcst, axis = 0)
    #         hcst_std = np.nanstd(model_hcst, axis = 0)
    #         hcst_anomaly = (model_hcst) - (hcst_mean)        

    #     return model_hcst, hcst_mean, hcst_std, hcst_var, hcst_anomaly


    # def get_periods_hcst(
    #         self, 
    #         model,
    #         data: xr.DataArray,
    #         year_hcst: int
    # ) -> dict[str, xr.DataArray]:
    #     '''Gera os agregados (acumulados/médias) para os trimestres e meses.
    #     Importante: os períodos mensais devem vir antes dos sazonais no arquivo de configuração'''

    #     periods_hcst = {} 

    #     for period, (start, end) in self.periods.items():

    #         is_mensal = period.startswith("mnth") 

    #         if is_mensal:

    #             new_date = date(year_hcst, self.month_hcst, 1) + relativedelta(months=start) #soma um mes
                
    #             ndays = calendar.monthrange(
    #                 new_date.year, 
    #                 new_date.month
    #             )[1]

    #             sel = select_month(start, end, data)    

    #             if model != "echam" and self.var == "prec":
    #                 sel = sel * ndays  
    #             elif self.var == "t2mt":
    #                 sel = sel - 273.15 

    #             periods_hcst[period] = sel.squeeze()

    #         else:

    #             if model != "echam" and self.var == "prec":   
    #                 periods_hcst[period] = aggregate_season(
    #                     period,
    #                     periods_hcst
    #                 )        
                    
    #             elif model == "echam" or self.var == "t2mt":
    #                 periods_hcst[period] = aggregate_season(
    #                     period,
    #                     periods_hcst,
    #                     mean = True
    #                 )        

    #     return periods_hcst

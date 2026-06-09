import numpy as np
import pandas as pd
import xarray as xr
import calendar
from src.config.loader import PARAMETERS_RUN
from src.config.config_path import PATH_OBS
from src.processing.data_processing import build_periods_obs

class Observation:

    def __init__(
        self, 
        base: str, 
        var: str, 
        month_obs: int
    ):
        self.base = base
        self.var = var
        self.month_obs = month_obs

        self.periods = PARAMETERS_RUN["periods"]

        self.climatology_dates = self.get_climatology_dates()

    def get_climatology_dates(self) -> dict[int, list[pd.Timestamp]]:
        '''Gera um dicionário com todas as datas do período climatológico.'''
        
        climatology = PARAMETERS_RUN["bases"][self.base]["climatology"]

        years = range(
            climatology["start_year"], 
            climatology["end_year"] + 1
        )

        dates_by_year = {
            year: []
            for year in years
        }

        for year in years:

            start_date = pd.Timestamp(
                year=year, 
                month=self.month_obs, 
                day=1
            )

            for i in range(5): #5 meses a frente

                dates_by_year[year].append(
                    start_date + pd.DateOffset(months=i)
                )
                
        return dates_by_year

    def load_observation_year(
        self,
        year_climatology: int
    ) -> xr.DataArray:
        ''' Carrega os dados das observações para um determinado ano de climatologia. '''

        obs_config = {

            "prec": { 

                "var_name": "precip",

                "path": lambda year, month:(
                    PATH_OBS /
                    "gpcp"/
                    str(year) / 
                    f"obs_gpcp_prec_mon_mean_{year}{month:02d}01.nc"                
            ),

                "transform": lambda data, ndays: data * ndays
            },

            "t2mt": {

                "var_name": "t2m",

                "path": lambda year, month:(
                    PATH_OBS /
                    "era5"/ 
                    f"obs_era5_t2mt_monthly_interp_{year}{month:02d}01.nc"
                ),

                "transform": lambda data, ndays: data - 273.15                
            }
        }
        
        config = obs_config[self.var]

        monthly_data = []

        for lead, date in enumerate(
            self.climatology_dates[year_climatology]
        ):

            ndays = calendar.monthrange(
                date.year, 
                date.month
            )[1]

            file_name_obs = config["path"](
                date.year,
                date.month
            )

            ds = xr.open_dataset(
                file_name_obs, 
                decode_timedelta=True
            )

            da = ds[config["var_name"]]
            da = da.squeeze()

            da = config["transform"](
                da, 
                ndays
            )

            da = da.expand_dims(
                lead=[lead]
            )

            monthly_data.append(da)

        obs_data_year = xr.concat(
            monthly_data,
            dim="lead"
        )

        return obs_data_year

    def calculate_periods_year(
        self,
        year_climatology: int
    ) -> dict[str, xr.DataArray]:
        ''' Carrega os dados observados para um ano específico e calcula os períodos de agregamento. '''

        data = self.load_observation_year(year_climatology)

        periods = build_periods_obs(
             self.var,
             data
        )

        periods_loaded = {
            k: y.load()
            for k, y in periods.items()
        }

        return periods_loaded

    def calculate_periods_all_years(self)  -> dict[str, xr.DataArray]:
        '''Calcula os agregados para todos os anos da climatologia'''

        periods_all_years = {
            period: []
            for period in self.periods
        }


        for year in self.climatology_dates:

            periods = self.calculate_periods_year(
                year
            )

            for period, da in periods.items():
                
                da = da.expand_dims(year=[year])
                periods_all_years[period].append(da)

        observations = {}

        for period, das in periods_all_years.items():

            observations[period] = xr.concat(
                das,
                dim="year"
            )

        return observations


    def calculate_observation_statistics(self) -> dict[str, dict[str, xr.DataArray]]:
        '''Calcula as estatísticas climatológicas das observações.'''

        obs = self.calculate_periods_all_years()

        total, mean, median, std, tinf, tsup, iqr, anom = (
            {}, {}, {}, {}, {}, {}, {}, {}
        )

        for period, da in obs.items():
            
            total[period] = da
            mean[period] = da.mean("year")
            median[period] = da.median("year")
            std[period] = da.std("year")

            tinf[period] = da.quantile(0.33, "year")
            tsup[period] = da.quantile(0.66, "year")

            q1 = da.quantile(0.25, "year")
            q3 = da.quantile(0.75, "year")

            iqr[period] = q3 - q1

            anom[period] = da - mean[period]

        return {
            "total": total,
            "mean": mean,
            "std": std,
            "tinf": tinf,   
            "tsup": tsup,
            "iqr": iqr,
            "anom": anom,
        }

    def mean_std_anom_obs_gamma(self):
        '''Calcula a média, desvio padrão e anomalia da climatologia das observações'''

        obs_periods = self.calculate_obs_periods() 

        # Períodos que queremos calcular estatísticas
        selected_periods = ['mnth00','mnth01', 'mnth02', 'mnth03', 'mnth04',
                            'seas00', 'seas01', 'seas02']

        stats = {}

        for label in selected_periods:
            data = obs_periods.get(label)
            data_array = np.array(data)

            # Calcula média, desvio padrão e anomalias
            mean = np.nanmean(data_array, axis=0)
            mediana = np.nanmedian(data_array, axis=0)
            variance = np.nanvar(data_array, axis=0)
            std = np.nanstd(data_array, axis=0)
            tercil_inf = np.nanpercentile(data_array, 33.33, axis=0)
            tercil_sup = np.nanpercentile(data_array, 66.66, axis=0)
            quartil_inf = np.nanpercentile(data_array, 25, axis=0)
            quartil_sup = np.nanpercentile(data_array, 75, axis=0) 
            iqr_obs =  quartil_sup - quartil_inf         
            obs_total = data_array      
            anomalias = obs_total - mean     

            # Armazena os resultados
            stats[label] = {
                'total': obs_total,
                'mean': mean,      
                'mediana': mediana,
                'variance': variance,   
                'std': std,        
                'anomaly': anomalias,   
                'tercilinf': tercil_inf,
                'tercilsup': tercil_sup,
                "intqobs": iqr_obs
            }

        return stats

# def get_periods_obs(
#         self, 
#         data: xr.DataArray
# ) -> dict[str, xr.DataArray]:
#     '''Gera os agregados (acumulados/médias) para os trimestres e meses.
#     Importante: os períodos mensais devem vir antes dos sazonais no arquivo de configuração'''

#     periods_obs = {} 

#     for period, (start, end) in self.periods.items():

#         is_mensal = period.startswith("mnth") 

#         if is_mensal:

#             sel = select_month(start, end, data)    
#             periods_obs[period] = sel.squeeze()

#         else: 

#             mean = self.var == "t2mt"

#             periods_obs[period] = aggregate_season(
#                 period,
#                 periods_obs,
#                 mean = mean
#             )        

#     return periods_obs
    
obs = Observation(
    "nmme",
    "prec",
    5
)



dict_obs = obs.calculate_observation_statistics()

print(dict_obs["anom"]['mnth00'].shape)



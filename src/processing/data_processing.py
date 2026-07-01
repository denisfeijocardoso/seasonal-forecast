
import xarray as xr
import calendar
from datetime import date
from dateutil.relativedelta import relativedelta
from src.config.loader import get_periods_aggregation

def select_month(
        start, 
        end,
        ds_forecast
    ):

    time_dim = [
        dim for dim in ds_forecast.dims 
        if dim in [
            "time", 
            "L", 
            "forecastMonth",
            "lead"
        ]
    ][0]

    return ds_forecast.isel({time_dim: slice(start, end)})
    
    
def kelvin_to_celsius(data):
    
    var_name = next(iter(data))   
    
    return (data[var_name] - 273.15).squeeze()

    
def aggregate_season(
        period: str,
        month_dict: dict[str, xr.DataArray],
        mean: bool = False
    ) -> xr.DataArray:

    start = int(period[-2:])

    seasonal = [
        month_dict[f"mnth{i:02d}"] 
        for i in range(start, start +3)
    ]
                            
    if mean:
        return sum(seasonal) / len(seasonal)  
    
    return sum(seasonal)

periods =  get_periods_aggregation()

def build_periods_model(
        model: str,
        var: str,
        year: int,
        month: int,
        data: xr.DataArray        
) -> dict[str, xr.DataArray]:
    '''Gera os agregados (acumulados/médias) para os trimestres e meses.
    Importante: os períodos mensais devem vir antes dos sazonais no arquivo de configuração'''

    periods_model = {} 

    for period, (start, end) in periods.items():

        is_mensal = period.startswith("mnth") 

        if is_mensal:

            new_date = date(year, month, 1) + relativedelta(months=start) #soma um mes
            
            ndays = calendar.monthrange(
                new_date.year, 
                new_date.month
            )[1]

            sel = select_month(start, end, data)    

            if model != "echam" and var == "prec":
                sel = sel * ndays  
            elif var == "t2mt":
                sel = sel - 273.15 

            periods_model[period] = sel.squeeze()

        else:

            if model != "echam" and var == "prec":   
                periods_model[period] = aggregate_season(
                    period,
                    periods_model
                )        
                
            elif model == "echam" or var == "t2mt":
                periods_model[period] = aggregate_season(
                    period,
                    periods_model,
                    mean = True
                )        

    return periods_model

def build_periods_obs(
        var: int,
        data: xr.DataArray
) -> dict[str, xr.DataArray]:
    '''Gera os agregados (acumulados/médias) para os trimestres e meses.
    Importante: os períodos mensais devem vir antes dos sazonais no arquivo de configuração'''

    periods_obs = {} 

    for period, (start, end) in periods.items():

        is_mensal = period.startswith("mnth") 

        if is_mensal:

            sel = select_month(start, end, data)    
            periods_obs[period] = sel.squeeze()

        else: 

            mean = var == "t2mt"

            periods_obs[period] = aggregate_season(
                period,
                periods_obs,
                mean = mean
            )        

    return periods_obs
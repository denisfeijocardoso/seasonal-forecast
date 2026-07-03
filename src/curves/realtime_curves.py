from pathlib import Path

import xarray as xr
import numpy as np
import pandas as pd
import calendar
import time
import matplotlib
import matplotlib.pyplot as plt
from scipy.stats import norm
from tqdm import tqdm
from multiprocessing import Pool

from src.config.config_models import get_multimodel_version
from src.config.loader import get_periods_aggregation
from src.config.paths import PATH_FIG, PATH_POSPROC


matplotlib.use('Agg')

TXT_PATH = Path(__file__).with_name("coords_points_curves.txt")


def _forecast_date(year_fcst: int, month_fcst: int) -> str:
    return f"{year_fcst}{month_fcst:02d}0100"


def _input_dir(base: str, calibration: str, year_fcst: int, month_fcst: int) -> Path:
    return (
        PATH_POSPROC
        / base
        / get_multimodel_version(base)
        / "forecast"
        / calibration
        / "multimodel"
        / str(year_fcst)
        / _forecast_date(year_fcst, month_fcst)
    )


def _curve_output_dir(base: str, calibration: str, year: int, yearmonthday: str) -> Path:
    return (
        PATH_FIG
        / base
        / get_multimodel_version(base)
        / "curves"
        / calibration
        / "multimodel"
        / str(year)
        / yearmonthday
    )


def _save_current_figure(path: Path, *, skip_existing: bool = False) -> None:
    if skip_existing and path.exists():
        print(f"Figura ja existe, pulando: {path}")
        return

    plt.savefig(path, dpi=150)
    print(f"Figura gerada: {path}")


def _file_path(
    base: str,
    calibration: str,
    var: str,
    product: str,
    lead: str,
    year_fcst: int,
    month_fcst: int,
) -> Path:
    fcst_date = _forecast_date(year_fcst, month_fcst)
    return (
        _input_dir(base, calibration, year_fcst, month_fcst)
        / f"fcst_{var}_{product}_{lead}_multimodel_calibrated_{calibration}_{fcst_date}.nc"
    )


def _open_mapped_var(
    base: str,
    var: str,
    lead: str,
    year_fcst: int,
    month_fcst: int,
    candidates: tuple[tuple[str, str], ...],
) -> xr.DataArray:
    tried = []
    for calibration, product in candidates:
        path = _file_path(base, calibration, var, product, lead, year_fcst, month_fcst)
        tried.append(path)
        if path.exists():
            da, _ = Curves.open_var(path)
            da = da.assign_coords(lon=((da.lon + 180) % 360 - 180))
            return da.sortby("lon")

    formatted = "\n".join(str(path) for path in tried)
    raise FileNotFoundError(f"Nenhum NetCDF encontrado para {var} {lead}:\n{formatted}")

class Curves:

    #Criar variáveis global
    DATA_PREC_COX = None 
    DATA_T2MT_COX = None
    DATA_PREC_REGR = None 
    DATA_T2MT_REGR = None

    @staticmethod
    def format_coord(lat, lon):
        # Latitude
        if lat >= 0:
            lat_str = f"{abs(lat):.2f}N"
        else:
            lat_str = f"{abs(lat):.2f}S"
            
        # Longitude
        if lon >= 0:
            lon_str = f"{abs(lon):.2f}E"
        else:
            lon_str = f"{abs(lon):.2f}W"
            
        return lat_str, lon_str

    @staticmethod
    def open_var(path):
        """Abre um netcdf e retorna o DataArray da primeira data variable encontrada."""
        ds = xr.open_dataset(path)
        data_vars = list(ds.data_vars)
        varname = data_vars[0]
        da = ds[varname]
        history = ds.attrs.get("history", "")
        return da, history.upper()

    @staticmethod
    def compute_period_names(year_fcst, month_fcst):
        periods = {
            "mnth00": (0,),
            "mnth01": (1,),
            "mnth02": (2,),
            "mnth03": (3,),
            "mnth04": (4,),
            "seas00": (0, 1, 2),
            "seas01": (1, 2, 3),
            "seas02": (2, 3, 4)
        }

        result = {}

        for period, offsets in periods.items():
            months = []
            for offset in offsets:
                month = month_fcst + offset
                year = year_fcst
                # Ajuste de ano se o mês passar de 12
                if month > 12:
                    month -= 12
                    year += 1
                months.append((month, year))

            if period.startswith("mnth"):
                # Apenas um mês
                m, y = months[0]
                month_abbr = calendar.month_abbr[m]
                result[period] = f"{month_abbr} {y}"
            elif period.startswith("seas"):
                # Três meses
                season_str = ''.join(calendar.month_abbr[m][0].upper() for m, _ in months)
                result[period] = f"{season_str} {months[0][1]}"

        return result

    @staticmethod
    def define_title(fcst_date, base, model, var, calib, period, lat, lon):
        fcst_date = pd.to_datetime(fcst_date, format="%Y%m%d")
        year = fcst_date.year
        monthstr = fcst_date.strftime('%b')
        month = f"{fcst_date.month:02d}"
        day = f"{fcst_date.day:02d}"
        yearmonthday = f"{year}{month}{day}00"

        date_titles = Curves.compute_period_names(year,fcst_date.month)
        periodfcst = date_titles[period]
        
        #Escrever Latitude e Longitude
        if lat >= 0:
            lat_str = f"{abs(lat):.2f}N"
        else:
            lat_str = f"{abs(lat):.2f}S"  
        # Longitude
        if lon >= 0:
            lon_str = f"{abs(lon):.2f}E"
        else:
            lon_str = f"{abs(lon):.2f}W"

        varis = {"prec":"Precip.",
                "t2mt": "2m Temp." }

        bases = {"nmme":"NMME + CPTEC",
                "copernicus": "C3S + CPTEC"}

        if calib == "regr":
            title = (f"{varis[var]} Forecast {bases[base]} Multi-Model Calibrated (Regr.)"
            f"\nfor {periodfcst} issued: {monthstr} {year} - Lat:{lat_str} Lon:{lon_str}")

        elif calib == "cox":
            title = (f"{varis[var]} Forecast {bases[base]} Multi-Model Calibrated (Cox)"
            f"\nfor {periodfcst} issued: {monthstr} {year} - Lat:{lat_str} Lon:{lon_str}")
        
        return title

    @staticmethod
    def open_files(fcst_date, base, model, var, calib):

        fcst_date = pd.to_datetime(fcst_date, format="%Y%m%d")
        month, year, day = fcst_date.month, fcst_date.year, fcst_date.day
        if model != "multimodel":
            raise ValueError("As curvas em tempo-real sao geradas apenas para multimodel.")

        #LISTA DOS ARQUIVOS
        if calib == "regr":
            files = { 
                "obsmean": (("regr", "obsmean"),),
                "fcstmean": (("regr", "total"), ("regr", "acum")),
                "obsstd": (("regr", "obsstd"),),
                "fcststd": (("regr", "stdev"), ("regr", "stdfcst")),
                "obstotal": (("regr", "obstotal"),),
                "obstercinf": (("regr", "obstercinf"),),
                "obstercsup": (("regr", "obstercsup"),),
                "ptercinfabove": (("regr", "above_tinf"), ("regr", "ptercinfabove")),
                "ptercinfbelow": (("regr", "below_tinf"), ("regr", "ptercinfbelow")),
                "ptercsupabove": (("regr", "above_tsup"), ("regr", "ptercsupabove")),
                "ptercsupbelow": (("regr", "below_tsup"), ("regr", "ptercsupbelow")),
                "corr": (("regr", "correlation"), ("regr", "corr")),
            }

        elif calib == "cox": 
            files = { 
                "yfcst": (("cox", "proby_fcst"), ("cox", "probyfcst")),
                "yobs": (("cox", "proby_clim"), ("cox", "probyobs")),
                "varx": (("cox", "varx"),),
                "obsmedian": (("cox", "obsmedian"),),
                "fcstmedian": (("cox", "total"), ("cox", "acum")),
                "obstercinf": (("cox", "obstercinf"), ("regr", "obstercinf")),
                "obstercsup": (("cox", "obstercsup"), ("regr", "obstercsup")),
                "ptercinfabove": (("cox", "above_tinf"), ("cox", "ptercinfabove")),
                "ptercinfbelow": (("cox", "below_tinf"), ("cox", "ptercinfbelow")),
                "ptercsupabove": (("cox", "above_tsup"), ("cox", "ptercsupabove")),
                "ptercsupbelow": (("cox", "below_tsup"), ("cox", "ptercsupbelow")),
                "iqrobs": (("cox", "obsiqr"),),
                "iqrfcst": (("cox", "iqr"), ("cox", "coxiqr")),
                "coef": (("cox", "coef_beta"), ("cox", "coef")),
            }   
        else:
            raise ValueError(f"Calibracao sem suporte para curvas: {calib}")

        data = {}
        leads = list(get_periods_aggregation())

        for lead in leads:
            data[lead] = {}

            for key, candidates in files.items():
                data[lead][key] = _open_mapped_var(
                    base,
                    var,
                    lead,
                    year,
                    month,
                    candidates,
                )
                if calib == "regr" and key.startswith("pterc"):
                    data[lead][key] = data[lead][key] * 100.0

        return data

    @staticmethod
    def get_index(arr, value): #Mapear o indice do lat/lon
        return np.abs(arr - value).argmin()

    @staticmethod
    def init_worker(fcst_date, base, model): #Essa função roda "data" uma vez por processo:

        global DATA_PREC_COX, DATA_T2MT_COX, DATA_PREC_REGR, DATA_T2MT_REGR

        DATA_PREC_COX = Curves.open_files(fcst_date, base, model, "prec", "cox")
        DATA_T2MT_COX = Curves.open_files(fcst_date, base, model, "t2mt", "cox")
        DATA_PREC_REGR = Curves.open_files(fcst_date, base, model, "prec", "regr")
        DATA_T2MT_REGR = Curves.open_files(fcst_date, base, model, "t2mt", "regr")

    @staticmethod
    def process_point(row_tuple):

        global DATA_PREC, DATA_T2MT

        data_prec_cox = DATA_PREC_COX
        data_t2mt_cox = DATA_T2MT_COX
        data_prec_regr = DATA_PREC_REGR
        data_t2mt_regr = DATA_T2MT_REGR

        row, fcst_date, base, model, year, month, day, yearmonthday, skip_existing = row_tuple

        ID = int(row["id"])
        ilat = float(row["lat"])
        ilon = float(row["lon"]) 

        lats = data_prec_cox[list(data_prec_cox.keys())[0]]["varx"].lat.values
        lons = data_prec_cox[list(data_prec_cox.keys())[0]]["varx"].lon.values
        lat_i = Curves.get_index(lats, ilat)
        lon_i = Curves.get_index(lons, ilon)


        #Loop nos leads
        for lead in data_prec_cox:  

            ########################
            #CALIBRAÇÃO: MÉTODO COX#
            ########################   
            calib = "cox"           
            data_prec = data_prec_cox
            data_t2mt = data_t2mt_cox

            ##############
            #PRECIPITAÇÃO#
            ############## 
            var = "prec"

            #Selecionar as variáveis para plotar a curva 
            x_vals = data_prec[lead]["varx"].isel(lat=lat_i, lon=lon_i).values
            y_fcst = data_prec[lead]["yfcst"].isel(lat=lat_i, lon=lon_i).values
            y_obs  = data_prec[lead]["yobs"].isel(lat=lat_i, lon=lon_i).values      
            
            # ===== Valores estatísticos =====
            iqr_fcst_val = data_prec[lead]["iqrfcst"].isel(lat=lat_i, lon=lon_i).item()
            iqr_obs_val  = data_prec[lead]["iqrobs"].isel(lat=lat_i, lon=lon_i).item()

            med_fcst_val = data_prec[lead]["fcstmedian"].isel(lat=lat_i, lon=lon_i).item()
            med_obs_val  = data_prec[lead]["obsmedian"].isel(lat=lat_i, lon=lon_i).item()

            anomaly_val = med_fcst_val - med_obs_val

            beta_val = data_prec[lead]["coef"].isel(lat=lat_i, lon=lon_i).item()

            terc_inf_val = data_prec[lead]["obstercinf"].isel(lat=lat_i, lon=lon_i).item()
            terc_sup_val = data_prec[lead]["obstercsup"].isel(lat=lat_i, lon=lon_i).item()

            p_below_inf = data_prec[lead]["ptercinfbelow"].isel(lat=lat_i, lon=lon_i).item()
            p_below_sup = data_prec[lead]["ptercsupbelow"].isel(lat=lat_i, lon=lon_i).item()
            p_above_inf = data_prec[lead]["ptercinfabove"].isel(lat=lat_i, lon=lon_i).item()
            p_above_sup = data_prec[lead]["ptercsupabove"].isel(lat=lat_i, lon=lon_i).item()

            # =========================
            # ===== CDF ============
            # =========================
            y_fcst_vals = 1 - y_fcst
            y_obs_vals  = 1 - y_obs

            x_plot = np.concatenate(([0], x_vals))
            y_fcst_plot = np.concatenate(([0], y_fcst_vals))
            y_obs_plot  = np.concatenate(([0], y_obs_vals))

            plt.figure(figsize=(6, 6))

            plt.step(x_plot, y_fcst_plot, color="blue", linewidth=2,
                    label="Forecast CDF", where='post')

            plt.step(x_plot, y_obs_plot, color="red", linewidth=2,
                    label="Climatological CDF", where='post')
            
            title = Curves.define_title(fcst_date, base, model, var, calib, lead, ilat, ilon)
            plt.title(title, fontsize=10.2, fontweight='bold', pad=4) 

            y_inf = p_below_inf
            y_sup = p_below_sup

            plt.plot([terc_inf_val, terc_inf_val],[0, y_inf],'--',color='black',linewidth=1)
            plt.plot([plt.gca().get_xlim()[0], terc_inf_val],[y_inf, y_inf],'--',color='black',linewidth=1)

            plt.plot([terc_sup_val, terc_sup_val], [0, y_sup],'--', color='black', linewidth=1)
            plt.plot([plt.gca().get_xlim()[0], terc_sup_val], [y_sup, y_sup],'--', color='black',linewidth=1)

            plt.text(terc_inf_val,0,r"$\mathbf{T\,1}$",ha='center',va='top',fontsize=8.5, fontweight='bold')
            plt.text(terc_sup_val,0.05,r"$\mathbf{T\,2}$",ha='center',va='top',fontsize=8.5, fontweight='bold') 

            if var == "prec":
                plt.xlabel("Precipitation (mm)",fontsize=9.5,fontweight='bold')
            elif var == "t2mt":
                plt.xlabel("2m Temperature (°C)",fontsize=9.5,fontweight='bold')

            plt.ylabel("Cumulative Probability",fontsize=9.5,fontweight='bold')     

            plt.ylim(-0.05, 1.05)
            plt.xlim(left=float(np.nanmin(x_vals)), right=float(np.nanmax(x_vals)))

            leg = plt.legend(loc='upper left', fontsize=7.8)
            leg.get_frame().set_facecolor('white')
            leg.get_frame().set_alpha(1)

            ax = plt.gca()
            for spine in ax.spines.values():
                spine.set_linewidth(1.5)

            text_right = (
                r"$\bf{Forecast\ (x)}$" + "\n\n"
                f"IQRx: {iqr_fcst_val:.1f}mm\n\n"
                f"medianₓ: {med_fcst_val:.1f}mm\n\n\n\n\n"
                r"$\bf{Observation\ (y)}$" + "\n\n"
                f"IQRy: {iqr_obs_val:.1f}mm\n\n"
                f"medianᵧ: {med_obs_val:.1f}mm\n\n\n"
                f"anomaly: {anomaly_val:.2f}mm\n\n"
                f"beta: {beta_val:.2f}\n\n\n\n\n"

                r"$\bf{Forecast}$" + "\n" +
                r"$\bf{Probabilities\ (p)}$" + "\n\n"
                f"P<(T1={terc_inf_val:.1f}mm): {p_below_inf*100:.0f}%\n\n"
                f"P<(T2={terc_sup_val:.1f}mm): {p_below_sup*100:.0f}%")

            plt.subplots_adjust(left=0.09, right=0.78, top=0.93, bottom=0.08)
            plt.gcf().text(0.785, 0.8, text_right, fontsize=7.5, va='top',ha='left')

            #Diretório saida dos arquivos 
            outdir = _curve_output_dir(base, calib, year, yearmonthday)
            outdir.mkdir(parents=True, exist_ok=True)   

            _save_current_figure(
                outdir / f"curve_cdf_{var}_{lead}_{calib}_{yearmonthday}_{ID}.png",
                skip_existing=skip_existing,
            )
            plt.close()

            # =========================
            # ===== EXC ============
            # =========================
            y_fcst_vals = y_fcst
            y_obs_vals  = y_obs

            x_plot = np.concatenate(([0], x_vals))
            y_fcst_plot = np.concatenate(([1], y_fcst_vals))
            y_obs_plot  = np.concatenate(([1], y_obs_vals))

            plt.figure(figsize=(6, 6))

            plt.step(x_plot, y_fcst_plot, color="blue", linewidth=2,
                    label="Forecast EDF", where='post')

            plt.step(x_plot, y_obs_plot, color="red", linewidth=2,
                    label="Climatological EDF", where='post')

            plt.title(title, fontsize=10.2, fontweight='bold', pad=4) 

            y_inf = p_above_inf
            y_sup = p_above_sup

            plt.plot([terc_inf_val, terc_inf_val],[0, y_inf],'--',color='black',linewidth=1)
            plt.plot([plt.gca().get_xlim()[0], terc_inf_val],[y_inf, y_inf],'--',color='black',linewidth=1)

            plt.plot([terc_sup_val, terc_sup_val], [0, y_sup],'--', color='black', linewidth=1)
            plt.plot([plt.gca().get_xlim()[0], terc_sup_val], [y_sup, y_sup],'--', color='black',linewidth=1)

            plt.text(terc_inf_val,0,r"$\mathbf{T\,1}$",ha='center',va='top',fontsize=8.5, fontweight='bold')
            plt.text(terc_sup_val,0.05,r"$\mathbf{T\,2}$",ha='center',va='top',fontsize=8.5, fontweight='bold') 

            if var == "prec":
                plt.xlabel("Precipitation (mm)",fontsize=9.5,fontweight='bold')
            elif var == "t2mt":
                plt.xlabel("2m Temperature (°C)",fontsize=9.5,fontweight='bold')

            plt.ylabel("Exceedance Probability",fontsize=9.5,fontweight='bold')     

            plt.ylim(-0.05, 1.05)
            plt.xlim(left=float(np.nanmin(x_vals)), right=float(np.nanmax(x_vals)))

            leg = plt.legend(loc='upper right', fontsize=7.8)
            leg.get_frame().set_facecolor('white')
            leg.get_frame().set_alpha(1)

            ax = plt.gca()
            for spine in ax.spines.values():
                spine.set_linewidth(1.5)

            text_right = (
                r"$\bf{Forecast\ (x)}$" + "\n\n"
                f"IQRx: {iqr_fcst_val:.1f}mm\n\n"
                f"medianₓ: {med_fcst_val:.1f}mm\n\n\n\n\n"
                r"$\bf{Observation\ (y)}$" + "\n\n"
                f"IQRy: {iqr_obs_val:.1f}mm\n\n"
                f"medianᵧ: {med_obs_val:.1f}mm\n\n\n"
                f"anomaly: {anomaly_val:.2f}mm\n\n"
                f"beta: {beta_val:.2f}\n\n\n\n\n"

                r"$\bf{Forecast}$" + "\n" +
                r"$\bf{Probabilities\ (p)}$" + "\n\n"
                f"P>(T1={terc_inf_val:.1f}mm): {p_above_inf*100:.0f}%\n\n"
                f"P>(T2={terc_sup_val:.1f}mm): {p_above_sup*100:.0f}%")
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        
            plt.subplots_adjust(left=0.09, right=0.78, top=0.93, bottom=0.08)
            plt.gcf().text(0.785, 0.8, text_right, fontsize=7.5, va='top',ha='left')

            #Diretório saida dos arquivos 
            outdir = _curve_output_dir(base, calib, year, yearmonthday)
            outdir.mkdir(parents=True, exist_ok=True)   

            _save_current_figure(
                outdir / f"curve_{var}_exc_{lead}_{calib}_{yearmonthday}_{ID}.png",
                skip_existing=skip_existing,
            )

            plt.close()

            #############
            #TEMPERATURA#
            #############
            var = "t2mt"
            
            #Selecionar as variáveis para plotar a curva 
            x_vals = data_t2mt[lead]["varx"].isel(lat=lat_i, lon=lon_i).values
            y_fcst = data_t2mt[lead]["yfcst"].isel(lat=lat_i, lon=lon_i).values
            y_obs  = data_t2mt[lead]["yobs"].isel(lat=lat_i, lon=lon_i).values      

            # ===== Valores estatísticos =====
            iqr_fcst_val = data_t2mt[lead]["iqrfcst"].isel(lat=lat_i, lon=lon_i).item()
            iqr_obs_val  = data_t2mt[lead]["iqrobs"].isel(lat=lat_i, lon=lon_i).item()

            med_fcst_val = data_t2mt[lead]["fcstmedian"].isel(lat=lat_i, lon=lon_i).item()
            med_obs_val  = data_t2mt[lead]["obsmedian"].isel(lat=lat_i, lon=lon_i).item()

            anomaly_val = med_fcst_val - med_obs_val

            beta_val = data_t2mt[lead]["coef"].isel(lat=lat_i, lon=lon_i).item()

            terc_inf_val = data_t2mt[lead]["obstercinf"].isel(lat=lat_i, lon=lon_i).item()
            terc_sup_val = data_t2mt[lead]["obstercsup"].isel(lat=lat_i, lon=lon_i).item()

            p_below_inf = data_t2mt[lead]["ptercinfbelow"].isel(lat=lat_i, lon=lon_i).item()
            p_below_sup = data_t2mt[lead]["ptercsupbelow"].isel(lat=lat_i, lon=lon_i).item()
            p_above_inf = data_t2mt[lead]["ptercinfabove"].isel(lat=lat_i, lon=lon_i).item()
            p_above_sup = data_t2mt[lead]["ptercsupabove"].isel(lat=lat_i, lon=lon_i).item()

            # =========================
            # ===== CDF ============
            # =========================
            y_fcst_vals = 1 - y_fcst
            y_obs_vals  = 1 - y_obs

            x_plot = np.concatenate(([np.nanmin(x_vals)], x_vals))
            y_fcst_plot = np.concatenate(([np.nanmin(y_fcst_vals)], y_fcst_vals))
            y_obs_plot  = np.concatenate(([np.nanmin(y_obs_vals)], y_obs_vals))

            plt.figure(figsize=(6, 6))

            plt.step(x_plot, y_fcst_plot, color="blue", linewidth=2,
                    label="Forecast CDF", where='post')

            plt.step(x_plot, y_obs_plot, color="red", linewidth=2,
                    label="Climatological CDF", where='post')
            
            title = Curves.define_title(fcst_date, base, model, var, calib, lead, ilat, ilon)
            plt.title(title, fontsize=10.2, fontweight='bold', pad=4) 

            y_inf = p_below_inf
            y_sup = p_below_sup

            plt.plot([terc_inf_val, terc_inf_val],[0, y_inf],'--',color='black',linewidth=1)
            plt.plot([plt.gca().get_xlim()[0], terc_inf_val],[y_inf, y_inf],'--',color='black',linewidth=1)

            plt.plot([terc_sup_val, terc_sup_val], [0, y_sup],'--', color='black', linewidth=1)
            plt.plot([plt.gca().get_xlim()[0], terc_sup_val], [y_sup, y_sup],'--', color='black',linewidth=1)

            plt.text(terc_inf_val,0,r"$\mathbf{T\,1}$",ha='center',va='top',fontsize=8.5, fontweight='bold')
            plt.text(terc_sup_val,0.05,r"$\mathbf{T\,2}$",ha='center',va='top',fontsize=8.5, fontweight='bold') 

            if var == "prec":
                plt.xlabel("Precipitation (mm)",fontsize=9.5,fontweight='bold')
            elif var == "t2mt":
                plt.xlabel("2m Temperature (°C)",fontsize=9.5,fontweight='bold')

            plt.ylabel("Cumulative Probability",fontsize=9.5,fontweight='bold')     

            plt.ylim(-0.05, 1.05)
            plt.xlim(left=float(np.nanmin(x_vals)), right=float(np.nanmax(x_vals)))

            leg = plt.legend(loc='upper left', fontsize=7.8)
            leg.get_frame().set_facecolor('white')
            leg.get_frame().set_alpha(1)

            ax = plt.gca()
            for spine in ax.spines.values():
                spine.set_linewidth(1.5)

            text_right = (
                r"$\bf{Forecast\ (x)}$" + "\n\n"
                f"IQRx: {iqr_fcst_val:.1f}°C\n\n"
                f"medianₓ: {med_fcst_val:.1f}°C\n\n\n\n\n"
                r"$\bf{Observation\ (y)}$" + "\n\n"
                f"IQRy: {iqr_obs_val:.1f}°C\n\n"
                f"medianᵧ: {med_obs_val:.1f}°C\n\n\n"
                f"anomaly: {anomaly_val:.2f}°C\n\n"
                f"beta: {beta_val:.2f}\n\n\n\n\n"

                r"$\bf{Forecast}$" + "\n" +
                r"$\bf{Probabilities\ (p)}$" + "\n\n"
                f"P<(T1={terc_inf_val:.1f}°C): {p_below_inf*100:.0f}%\n\n"
                f"P<(T2={terc_sup_val:.1f}°C): {p_below_sup*100:.0f}%")

            plt.subplots_adjust(left=0.09, right=0.78, top=0.93, bottom=0.08)
            plt.gcf().text(0.785, 0.8, text_right, fontsize=7.5, va='top',ha='left')

            #Diretório saida dos arquivos 
            outdir = _curve_output_dir(base, calib, year, yearmonthday)
            outdir.mkdir(parents=True, exist_ok=True)   

            _save_current_figure(
                outdir / f"curve_{var}_cdf_{lead}_{calib}_{yearmonthday}_{ID}.png",
                skip_existing=skip_existing,
            )

            plt.close()

            # =========================
            # ===== EXC ============
            # =========================
            y_fcst_vals = y_fcst
            y_obs_vals  = y_obs

            x_plot = np.concatenate(([np.nanmin(x_vals)], x_vals))
            y_fcst_plot = np.concatenate(([np.nanmin(y_fcst_vals)], y_fcst_vals))
            y_obs_plot  = np.concatenate(([np.nanmin(y_obs_vals)], y_obs_vals))

            plt.figure(figsize=(6, 6))

            plt.step(x_plot, y_fcst_plot, color="blue", linewidth=2,
                    label="Forecast EDF", where='post')

            plt.step(x_plot, y_obs_plot, color="red", linewidth=2,
                    label="Climatological EDF", where='post')

            plt.title(title, fontsize=10.2, fontweight='bold', pad=4) 

            y_inf = p_above_inf
            y_sup = p_above_sup

            plt.plot([terc_inf_val, terc_inf_val],[0, y_inf],'--',color='black',linewidth=1)
            plt.plot([plt.gca().get_xlim()[0], terc_inf_val],[y_inf, y_inf],'--',color='black',linewidth=1)

            plt.plot([terc_sup_val, terc_sup_val], [0, y_sup],'--', color='black', linewidth=1)
            plt.plot([plt.gca().get_xlim()[0], terc_sup_val], [y_sup, y_sup],'--', color='black',linewidth=1)

            plt.text(terc_inf_val,0,r"$\mathbf{T\,1}$",ha='center',va='top',fontsize=8.5, fontweight='bold')
            plt.text(terc_sup_val,0.05,r"$\mathbf{T\,2}$",ha='center',va='top',fontsize=8.5, fontweight='bold') 

            if var == "prec":
                plt.xlabel("Precipitation (mm)",fontsize=9.5,fontweight='bold')
            elif var == "t2mt":
                plt.xlabel("2m Temperature (°C)",fontsize=9.5,fontweight='bold')

            plt.ylabel("Exceedance Probability",fontsize=9.5,fontweight='bold')     

            plt.ylim(-0.05, 1.05)
            plt.xlim(left=float(np.nanmin(x_vals)), right=float(np.nanmax(x_vals)))

            leg = plt.legend(loc='upper right', fontsize=7.8)
            leg.get_frame().set_facecolor('white')
            leg.get_frame().set_alpha(1)

            ax = plt.gca()
            for spine in ax.spines.values():
                spine.set_linewidth(1.5)

            text_right = (
                r"$\bf{Forecast\ (x)}$" + "\n\n"
                f"IQRx: {iqr_fcst_val:.1f}°C\n\n"
                f"medianₓ: {med_fcst_val:.1f}°C\n\n\n\n\n"
                r"$\bf{Observation\ (y)}$" + "\n\n"
                f"IQRy: {iqr_obs_val:.1f}°C\n\n"
                f"medianᵧ: {med_obs_val:.1f}°C\n\n\n"
                f"anomaly: {anomaly_val:.2f}°C\n\n"
                f"beta: {beta_val:.2f}\n\n\n\n\n"

                r"$\bf{Forecast}$" + "\n" +
                r"$\bf{Probabilities\ (p)}$" + "\n\n"
                f"P>(T1={terc_inf_val:.1f}°C): {p_above_inf*100:.0f}%\n\n"
                f"P>(T2={terc_sup_val:.1f}°C): {p_above_sup*100:.0f}%")


            plt.subplots_adjust(left=0.09, right=0.78, top=0.93, bottom=0.08)
            plt.gcf().text(0.785, 0.8, text_right, fontsize=7.5, va='top',ha='left')

            #Diretório saida dos arquivos 
            outdir = _curve_output_dir(base, calib, year, yearmonthday)
            outdir.mkdir(parents=True, exist_ok=True)   

            _save_current_figure(
                outdir / f"curve_{var}_exc_{lead}_{calib}_{yearmonthday}_{ID}.png",
                skip_existing=skip_existing,
            )
            plt.close()

            #####################################
            #CALIBRAÇÃO: REGRESSÃO LINEAR NORMAL#
            #####################################         
            calib = "regr"
            data_prec = data_prec_regr
            data_t2mt = data_t2mt_regr

            ##############
            #PRECIPITAÇÃO#
            ############## 
            var = "prec"

            #Selecionar as variáveis para plotar a curva 
            obs_mean = data_prec[lead]["obsmean"].isel(lat=lat_i, lon=lon_i).values
            obs_std = data_prec[lead]["obsstd"].isel(lat=lat_i, lon=lon_i).values
            fcst_mean = data_prec[lead]["fcstmean"].isel(lat=lat_i, lon=lon_i).values          
            fcst_std = data_prec[lead]["fcststd"].isel(lat=lat_i, lon=lon_i).values    
            obs_total = data_prec[lead]["obstotal"].isel(lat=lat_i, lon=lon_i).values

            # ===== Valores estatísticos =====
            correlat = data_prec[lead]["corr"].sel(lat=ilat, lon=ilon).item()

            anomaly_val = fcst_mean - obs_mean

            terc_inf_val = data_prec[lead]["obstercinf"].isel(lat=lat_i, lon=lon_i).item()
            terc_sup_val = data_prec[lead]["obstercsup"].isel(lat=lat_i, lon=lon_i).item()

            p_below_inf = data_prec[lead]["ptercinfbelow"].isel(lat=lat_i, lon=lon_i).item()
            p_below_sup = data_prec[lead]["ptercsupbelow"].isel(lat=lat_i, lon=lon_i).item()
            p_above_inf = data_prec[lead]["ptercinfabove"].isel(lat=lat_i, lon=lon_i).item()
            p_above_sup = data_prec[lead]["ptercsupabove"].isel(lat=lat_i, lon=lon_i).item()

            # ============================
            # Séries observadas
            # ============================
            obs_point = obs_total
            obs_point = obs_point[~np.isnan(obs_point)]
            obs_sorted = np.sort(obs_point)
            n = len(obs_sorted)

            if n > 0:
                # Probabilidade acumulada empírica
                y_cdf = np.arange(1, n+1) / n

                # -------------------
                # CDF empírica
                # -------------------
                x_emp_cdf = np.concatenate(([0], obs_sorted, [obs_sorted[-1]]))
                y_emp_cdf = np.concatenate(([0], y_cdf, [1]))

                # -------------------
                # Excedência empírica
                # -------------------
                x_emp_exc = np.concatenate(([0], obs_sorted, [obs_sorted[-1]]))
                y_emp_exc = np.concatenate(([1], 1 - y_cdf, [0]))

            # ============================
            # Curvas Normais
            # ============================
            x_max = np.nanmax([np.max(obs_sorted),
                    terc_inf_val, terc_sup_val])

            x_norm = np.linspace(0, x_max, 200)

            mu_obs  = obs_mean
            sd_obs  = obs_std
            mu_fcst = fcst_mean
            sd_fcst = fcst_std

            # =========================
            # ===== CDF ============
            # =========================
            y_obs_norm  = norm.cdf(x_norm, loc=obs_mean, scale=obs_std)
            y_fcst_norm = norm.cdf(x_norm, loc=fcst_mean, scale=fcst_std)

            # PLOT
            plt.figure(figsize=(6,6))       

            # Linha normal (fit)
            plt.plot(x_norm, y_obs_norm, color="red", linewidth=2, linestyle="--",
                    label="Normal Fit", zorder = 1)

            # empírica em escada, normal em linha
            plt.step(x_emp_cdf, y_emp_cdf, color="red", linewidth=2, where="post",
                    label="Climatological CDF", zorder = 2)
            plt.plot(x_norm, y_fcst_norm, color="blue", linewidth=2,
                    label="Forecast CDF", zorder = 3) 
                    
            #Título do Gráfico
            title = Curves.define_title(fcst_date, base, model, "prec", calib, lead, ilat, ilon)
            plt.title(title, fontsize=10.2, fontweight='bold')
            plt.xlabel("Precipitation (mm)",fontsize=9.5, fontweight='bold')

            plt.ylabel("Cumulative Probability",fontsize=9.5,fontweight='bold')

            #Plotar linha pontilhada dos tercis
            y_inf = p_below_inf/100
            y_sup = p_below_sup/100

            # ---- Linha para terc_inf_val ----
            # vertical
            plt.plot([terc_inf_val, terc_inf_val],[0, y_inf],
                linestyle='--',color='black',linewidth=1)

            # horizontal até limite esquerdo do eixo x
            plt.plot([plt.gca().get_xlim()[0], terc_inf_val],[y_inf, y_inf],
                linestyle='--',color='black',linewidth=1)

            plt.text(terc_inf_val, 0, r"$\mathbf{T\,1}$", ha='center',
                va='top', fontsize=8.5, fontweight='bold')

            # ---- Linha para terc_sup_val ----
            # vertical
            plt.plot([terc_sup_val, terc_sup_val],[0, y_sup],
                linestyle='--',color='black',linewidth=1)

            # horizontal até limite esquerdo do eixo x
            plt.plot([plt.gca().get_xlim()[0], terc_sup_val],[y_sup, y_sup],
                linestyle='--', color='black', linewidth=1)

            plt.text(terc_sup_val,0.05,r"$\mathbf{T\,2}$",
                ha='center', va='top', fontsize=8.5, fontweight='bold')

            plt.xlim(0, x_max)

            #plt.xlim(0, np.max(obs_sorted))
            plt.ylim(-0.05, 1.05)
            plt.grid(False)

            leg = plt.legend(loc='upper left', fontsize=7.8)

            leg.get_frame().set_facecolor('white')
            leg.get_frame().set_alpha(1)

            ax = plt.gca()

            for spine in ax.spines.values():
                spine.set_linewidth(1.5)

            text_right = (
                r"$\bf{Forecast\ (x)}$" + "\n\n"
                f"stdvₓ: {fcst_std:.1f}mm\n\n"
                f"meanₓ: {fcst_mean:.1f}mm\n\n\n\n\n"
                r"$\bf{Observation\ (y)}$" + "\n\n"
                f"stdvᵧ: {obs_std:.1f}mm\n\n"
                f"meanᵧ: {obs_mean:.1f}mm\n\n\n"
                f"anomaly: {anomaly_val:.2f}mm\n\n"
                f"r: {correlat:.2f}\n\n\n\n\n"

                r"$\bf{Forecast}$" + "\n" +
                r"$\bf{Probabilities\ (p)}$" + "\n\n"
                f"P<(T1={terc_inf_val:.1f}mm): {p_below_inf:.0f}%\n\n"
                f"P<(T2={terc_sup_val:.1f}mm): {p_below_sup:.0f}%")

            plt.subplots_adjust(left=0.09, right=0.78, top=0.93, bottom=0.08)

            plt.gcf().text(0.785, 0.8, text_right, fontsize=7.5, va='top',ha='left')

            #Diretório saida dos arquivos 
            outdir = _curve_output_dir(base, calib, year, yearmonthday)
            outdir.mkdir(parents=True, exist_ok=True)            

            _save_current_figure(
                outdir / f"curve_{var}_cdf_{lead}_{calib}_{yearmonthday}_{ID}.png",
                skip_existing=skip_existing,
            )
            plt.close()

            # ======================
            # ===== EXC ============
            # ======================
            y_obs_norm  = 1 - norm.cdf(x_norm, loc=obs_mean, scale=obs_std)
            y_fcst_norm = 1 - norm.cdf(x_norm, loc=fcst_mean, scale=fcst_std)

            # PLOT
            plt.figure(figsize=(6,6))       

            # Linha normal (fit)
            plt.plot(x_norm, y_obs_norm, color="red", linewidth=2, linestyle="--",
                    label="Normal Fit", zorder = 1)

            # empírica em escada, normal em linha
            plt.step(x_emp_exc, y_emp_exc, color="red", linewidth=2, where="post",
                    label="Climatological EDF", zorder = 2)
            plt.plot(x_norm, y_fcst_norm, color="blue", linewidth=2,
                    label="Forecast EDF", zorder = 3) 
                    
            #Título do Gráfico
            title = Curves.define_title(fcst_date, base, model, "t2mt", calib, lead, ilat, ilon)
            plt.title(title, fontsize=10.2, fontweight='bold')
            plt.xlabel("Precipitation (mm)",fontsize=9.5, fontweight='bold')

            plt.ylabel("Exceedance Probability",fontsize=9.5,fontweight='bold')     

            #Plotar linha pontilhada dos tercis
            y_inf = p_above_inf/100
            y_sup = p_above_sup/100

            # ---- Linha para terc_inf_val ----
            # vertical
            plt.plot([terc_inf_val, terc_inf_val],[0, y_inf],
                linestyle='--',color='black',linewidth=1)

            # horizontal até limite esquerdo do eixo x
            plt.plot([plt.gca().get_xlim()[0], terc_inf_val],[y_inf, y_inf],
                linestyle='--',color='black',linewidth=1)

            plt.text(terc_inf_val, 0, r"$\mathbf{T\,1}$", ha='center',
                va='top', fontsize=8.5, fontweight='bold')

            # ---- Linha para terc_sup_val ----
            # vertical
            plt.plot([terc_sup_val, terc_sup_val],[0, y_sup],
                linestyle='--',color='black',linewidth=1)

            # horizontal até limite esquerdo do eixo x
            plt.plot([plt.gca().get_xlim()[0], terc_sup_val],[y_sup, y_sup],
                linestyle='--', color='black', linewidth=1)

            plt.text(terc_sup_val,0.05,r"$\mathbf{T\,2}$",
                ha='center', va='top', fontsize=8.5, fontweight='bold')

            x_max = np.nanmax([np.max(obs_sorted),
                    terc_inf_val, terc_sup_val])

            plt.xlim(0, x_max)

            plt.ylim(-0.05, 1.05)
            plt.grid(False)

            leg = plt.legend(loc='upper right', fontsize=7.8)

            leg.get_frame().set_facecolor('white')
            leg.get_frame().set_alpha(1)

            ax = plt.gca()

            for spine in ax.spines.values():
                spine.set_linewidth(1.5)

            text_right = (
                r"$\bf{Forecast\ (x)}$" + "\n\n"
                f"stdvₓ: {fcst_std:.1f}mm\n\n"
                f"meanₓ: {fcst_mean:.1f}mm\n\n\n\n\n"
                r"$\bf{Observation\ (y)}$" + "\n\n"
                f"stdvᵧ: {obs_std:.1f}mm\n\n"
                f"meanᵧ: {obs_mean:.1f}mm\n\n\n"
                f"anomaly: {anomaly_val:.2f}mm\n\n"
                f"r: {correlat:.2f}\n\n\n\n\n"

                r"$\bf{Forecast}$" + "\n" +
                r"$\bf{Probabilities\ (p)}$" + "\n\n"
                f"P>(T1={terc_inf_val:.1f}mm): {p_above_inf:.0f}%\n\n"
                f"P>(T2={terc_sup_val:.1f}mm): {p_above_sup:.0f}%")

            plt.subplots_adjust(left=0.09, right=0.78, top=0.93, bottom=0.08)

            plt.gcf().text(0.785, 0.8, text_right, fontsize=7.5, va='top',ha='left')

            #Diretório saida dos arquivos 
            outdir = _curve_output_dir(base, calib, year, yearmonthday)
            outdir.mkdir(parents=True, exist_ok=True)            

            _save_current_figure(
                outdir / f"curve_{var}_exc_{lead}_{calib}_{yearmonthday}_{ID}.png",
                skip_existing=skip_existing,
            )
            plt.close()

            ################
            #TEMPERATURA 2m#
            ################
            var = "t2mt"

            #Selecionar as variáveis para plotar a curva 
            obs_mean = data_t2mt[lead]["obsmean"].isel(lat=lat_i, lon=lon_i).values
            obs_std = data_t2mt[lead]["obsstd"].isel(lat=lat_i, lon=lon_i).values
            fcst_mean = data_t2mt[lead]["fcstmean"].isel(lat=lat_i, lon=lon_i).values          
            fcst_std = data_t2mt[lead]["fcststd"].isel(lat=lat_i, lon=lon_i).values    
            obs_total = data_t2mt[lead]["obstotal"].isel(lat=lat_i, lon=lon_i).values

            # ===== Valores estatísticos =====
            correlat = data_t2mt[lead]["corr"].sel(lat=ilat, lon=ilon).item()

            anomaly_val = fcst_mean - obs_mean

            terc_inf_val = data_t2mt[lead]["obstercinf"].isel(lat=lat_i, lon=lon_i).item()
            terc_sup_val = data_t2mt[lead]["obstercsup"].isel(lat=lat_i, lon=lon_i).item()

            p_below_inf = data_t2mt[lead]["ptercinfbelow"].isel(lat=lat_i, lon=lon_i).item()
            p_below_sup = data_t2mt[lead]["ptercsupbelow"].isel(lat=lat_i, lon=lon_i).item()
            p_above_inf = data_t2mt[lead]["ptercinfabove"].isel(lat=lat_i, lon=lon_i).item()
            p_above_sup = data_t2mt[lead]["ptercsupabove"].isel(lat=lat_i, lon=lon_i).item()

            # ============================
            # Séries observadas
            # ============================
            obs_point = obs_total
            obs_point = obs_point[~np.isnan(obs_point)]
            obs_sorted = np.sort(obs_point)
            n = len(obs_sorted)

            if n > 0:
                # Probabilidade acumulada empírica
                y_cdf = np.arange(1, n+1) / n

                # -------------------
                # CDF empírica
                # -------------------

                x_emp_cdf = np.concatenate(([np.min(obs_sorted)], obs_sorted, [np.max(obs_sorted)]))
                #x_emp_cdf = np.concatenate(([0], obs_sorted, [obs_sorted[-1]]))
                y_emp_cdf = np.concatenate(([0], y_cdf, [1]))

                # -------------------
                # Excedência empírica
                # -------------------
                x_emp_exc = np.concatenate(([np.min(obs_sorted)], obs_sorted, [np.max(obs_sorted)]))                   
                #x_emp_exc = np.concatenate(([0], obs_sorted, [obs_sorted[-1]]))
                y_emp_exc = np.concatenate(([1], 1 - y_cdf, [0]))

            # ============================
            # Curvas Normais
            # ============================

            # x_min = np.min(obs_sorted)
            # x_max = np.max(obs_sorted)

            x_min = np.nanmin([
                np.min(obs_sorted),
                terc_inf_val,
                terc_sup_val
            ])

            x_max = np.nanmax([
                np.max(obs_sorted),
                terc_inf_val,
                terc_sup_val
            ])

            x_norm = np.linspace(x_min, x_max, 200)    

            #x_norm = np.linspace(0, np.max(obs_sorted))

            mu_obs  = obs_mean
            sd_obs  = obs_std
            mu_fcst = fcst_mean
            sd_fcst = fcst_std

            # =========================
            # ===== CDF ============
            # =========================
            y_obs_norm  = norm.cdf(x_norm, loc=obs_mean, scale=obs_std)
            y_fcst_norm = norm.cdf(x_norm, loc=fcst_mean, scale=fcst_std)

            # PLOT
            plt.figure(figsize=(6,6))       

            # Linha normal (fit)
            plt.plot(x_norm, y_obs_norm, color="red", linewidth=2, linestyle="--",
                    label="Normal Fit", zorder = 1)

            # empírica em escada, normal em linha
            plt.step(x_emp_cdf, y_emp_cdf, color="red", linewidth=2, where="post",
                    label="Climatological CDF", zorder = 2)
            plt.plot(x_norm, y_fcst_norm, color="blue", linewidth=2,
                    label="Forecast CDF", zorder = 3) 
                    
            #Título do Gráfico
            title = Curves.define_title(fcst_date, base, model, "t2mt", calib, lead, ilat, ilon)
            plt.title(title, fontsize=10.1, fontweight='bold')
            
            plt.xlabel("2m Temperature (°C)",fontsize=9.5,fontweight='bold')

            plt.ylabel("Cumulative Probability",fontsize=9.5,fontweight='bold')

            #Plotar linha pontilhada dos tercis
            y_inf = p_below_inf/100
            y_sup = p_below_sup/100

            # ---- Linha para terc_inf_val ----
            # vertical
            plt.plot([terc_inf_val, terc_inf_val],[0, y_inf],
                linestyle='--',color='black',linewidth=1)

            # horizontal até limite esquerdo do eixo x
            plt.plot([plt.gca().get_xlim()[0], terc_inf_val],[y_inf, y_inf],
                linestyle='--',color='black',linewidth=1)

            plt.text(terc_inf_val, 0, r"$\mathbf{T\,1}$", ha='center',
                va='top', fontsize=8.5, fontweight='bold')

            # ---- Linha para terc_sup_val ----
            # vertical
            plt.plot([terc_sup_val, terc_sup_val],[0, y_sup],
                linestyle='--',color='black',linewidth=1)

            # horizontal até limite esquerdo do eixo x
            plt.plot([plt.gca().get_xlim()[0], terc_sup_val],[y_sup, y_sup],
                linestyle='--', color='black', linewidth=1)

            plt.text(terc_sup_val,0.05,r"$\mathbf{T\,2}$",
                ha='center', va='top', fontsize=8.5, fontweight='bold')

            x_max = np.nanmax([np.max(obs_sorted), np.max(x_norm),
                    terc_inf_val,terc_sup_val])

            x_min = np.nanmin([np.min(obs_sorted), np.min(x_norm),
                    terc_inf_val,terc_sup_val])

            plt.xlim(x_min, x_max)
            plt.ylim(-0.05, 1.05)
            plt.grid(False)

            leg = plt.legend(loc='upper left', fontsize=7.8)

            leg.get_frame().set_facecolor('white')
            leg.get_frame().set_alpha(1)

            ax = plt.gca()

            for spine in ax.spines.values():
                spine.set_linewidth(1.5)

            text_right = (
                r"$\bf{Forecast\ (x)}$" + "\n\n"
                f"stdvₓ: {fcst_std:.1f}°C\n\n"
                f"meanₓ: {fcst_mean:.1f}°C\n\n\n\n\n"
                r"$\bf{Observation\ (y)}$" + "\n\n"
                f"stdvᵧ: {obs_std:.1f}°C\n\n"
                f"meanᵧ: {obs_mean:.1f}°C\n\n\n"
                f"anomaly: {anomaly_val:.2f}°C\n\n"
                f"r: {correlat:.2f}\n\n\n\n\n"

                r"$\bf{Forecast}$" + "\n" +
                r"$\bf{Probabilities\ (p)}$" + "\n\n"
                f"P<(T1={terc_inf_val:.1f}°C): {p_below_inf:.0f}%\n\n"
                f"P<(T2={terc_sup_val:.1f}°C): {p_below_sup:.0f}%")

            plt.subplots_adjust(left=0.09, right=0.78, top=0.93, bottom=0.08)

            plt.gcf().text(0.785, 0.8, text_right, fontsize=7.5, va='top',ha='left')

            #Diretório saida dos arquivos 
            outdir = _curve_output_dir(base, calib, year, yearmonthday)
            outdir.mkdir(parents=True, exist_ok=True)            

            _save_current_figure(
                outdir / f"curve_{var}_cdf_{lead}_{calib}_{yearmonthday}_{ID}.png",
                skip_existing=skip_existing,
            )
            plt.close()

            # ======================
            # ===== EXC ============
            # ======================
            y_obs_norm  = 1 - norm.cdf(x_norm, loc=obs_mean, scale=obs_std)
            y_fcst_norm = 1 - norm.cdf(x_norm, loc=fcst_mean, scale=fcst_std)

            # PLOT
            plt.figure(figsize=(6,6))       

            # Linha normal (fit)
            plt.plot(x_norm, y_obs_norm, color="red", linewidth=2, linestyle="--",
                    label="Normal Fit", zorder = 1)

            # empírica em escada, normal em linha
            plt.step(x_emp_exc, y_emp_exc, color="red", linewidth=2, where="post",
                    label="Climatological EDF", zorder = 2)
            plt.plot(x_norm, y_fcst_norm, color="blue", linewidth=2,
                    label="Forecast EDF", zorder = 3) 
                    
            #Título do Gráfico
            title = Curves.define_title(fcst_date, base, model, "t2mt", calib, lead, ilat, ilon)
            plt.title(title, fontsize=10.1, fontweight='bold')

            plt.xlabel("2m Temperature (°C)",fontsize=9.5,fontweight='bold')

            plt.ylabel("Exceedance Probability",fontsize=9.5,fontweight='bold')     

            #Plotar linha pontilhada dos tercis
            y_inf = p_above_inf/100
            y_sup = p_above_sup/100

            # ---- Linha para terc_inf_val ----
            # vertical
            plt.plot([terc_inf_val, terc_inf_val],[0, y_inf],
                linestyle='--',color='black',linewidth=1)

            # horizontal até limite esquerdo do eixo x
            plt.plot([plt.gca().get_xlim()[0], terc_inf_val],[y_inf, y_inf],
                linestyle='--',color='black',linewidth=1)

            plt.text(terc_inf_val, 0, r"$\mathbf{T\,1}$", ha='center',
                va='top', fontsize=8.5, fontweight='bold')

            # ---- Linha para terc_sup_val ----
            # vertical
            plt.plot([terc_sup_val, terc_sup_val],[0, y_sup],
                linestyle='--',color='black',linewidth=1)

            # horizontal até limite esquerdo do eixo x
            plt.plot([plt.gca().get_xlim()[0], terc_sup_val],[y_sup, y_sup],
                linestyle='--', color='black', linewidth=1)

            plt.text(terc_sup_val,0.05,r"$\mathbf{T\,2}$",
                ha='center', va='top', fontsize=8.5, fontweight='bold')

            x_max = np.nanmax([np.max(obs_sorted), np.max(x_norm),
                    terc_inf_val,terc_sup_val])

            x_min = np.nanmin([np.min(obs_sorted), np.min(x_norm),
                    terc_inf_val,terc_sup_val])

            plt.xlim(x_min, x_max)
            plt.ylim(-0.05, 1.05)
            plt.grid(False)

            leg = plt.legend(loc='upper right', fontsize=7.8)

            leg.get_frame().set_facecolor('white')
            leg.get_frame().set_alpha(1)

            ax = plt.gca()

            for spine in ax.spines.values():
                spine.set_linewidth(1.5)

            text_right = (
                r"$\bf{Forecast\ (x)}$" + "\n\n"
                f"stdvₓ: {fcst_std:.1f}°C\n\n"
                f"meanₓ: {fcst_mean:.1f}°C\n\n\n\n\n"
                r"$\bf{Observation\ (y)}$" + "\n\n"
                f"stdvᵧ: {obs_std:.1f}°C\n\n"
                f"meanᵧ: {obs_mean:.1f}°C\n\n\n"
                f"anomaly: {anomaly_val:.2f}°C\n\n"
                f"r: {correlat:.2f}\n\n\n\n\n"

                r"$\bf{Forecast}$" + "\n" +
                r"$\bf{Probabilities\ (p)}$" + "\n\n"
                f"P>(T1={terc_inf_val:.1f}°C): {p_above_inf:.0f}%\n\n"
                f"P>(T2={terc_sup_val:.1f}°C): {p_above_sup:.0f}%")

            plt.subplots_adjust(left=0.09, right=0.78, top=0.93, bottom=0.08)

            plt.gcf().text(0.785, 0.8, text_right, fontsize=7.5, va='top',ha='left')

            #Diretório saida dos arquivos 
            outdir = _curve_output_dir(base, calib, year, yearmonthday)
            outdir.mkdir(parents=True, exist_ok=True)            

            _save_current_figure(
                outdir / f"curve_{var}_exc_{lead}_{calib}_{yearmonthday}_{ID}.png",
                skip_existing=skip_existing,
            )
            plt.close()


    @staticmethod
    def create_curves(
        fcst_date,
        base,
        model="multimodel",
        workers=8,
        skip_existing=False,
    ):
        if model != "multimodel":
            raise ValueError("As curvas em tempo-real sao geradas apenas para multimodel.")

        #Organiza a data
        fcst_date = pd.to_datetime(fcst_date, format="%Y%m%d")
        month, year, day = fcst_date.month, fcst_date.year, fcst_date.day
        month = f"{month:02d}"
        day = f"{day:02d}"
        yearmonthday = f"{year}{month}{day}00"
        
        # Ler arquivo de coordenadas (cada ponto sobre o globo)
        df_points = pd.read_csv(TXT_PATH, sep=None, engine="python")
        df_points.columns = [c.strip().lower() for c in df_points.columns]

        tasks = [
            (row, fcst_date, base, model, year, month, day, yearmonthday, skip_existing)
            for _, row in df_points.iterrows()
        ]

        n_proc = max(1, int(workers))

        start_time = time.time()
        
        with Pool(
            n_proc,
            initializer=Curves.init_worker,
            initargs=(fcst_date, base, model)
        ) as p:
            list(tqdm(
                p.imap(Curves.process_point, tasks),
                total=len(tasks),
                desc="Processando pontos",
                ncols=100
            ))

        end_time = time.time()

        elapsed = end_time - start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)

        print(f"Tempo total: {hours}h {minutes}min {seconds}s")


def run_realtime_curves(
    base: str,
    year_fcst: int,
    month_fcst: int,
    *,
    workers: int = 8,
    skip_existing: bool = False,
) -> None:
    fcst_date = f"{year_fcst}{month_fcst:02d}01"
    Curves.create_curves(
        fcst_date,
        base,
        "multimodel",
        workers=workers,
        skip_existing=skip_existing,
    )


         

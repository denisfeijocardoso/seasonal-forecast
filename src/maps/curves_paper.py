import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
from scipy.stats import gamma
import os
import calendar

obs = xr.open_dataset("/dados/mmclima/multimodelo/sazonal/obs/gpcp/obs_gpcp_pr_mon_mean_1979-2025.nc")
lat_obs = obs["lat"].values
lon_obs = obs["lon"].values

def lon360_to_180(lon):
    return ((lon + 180) % 360) - 180

print("####### Venezuela:")
print(lat_obs[38])
print(lon360_to_180(lon_obs[118]))

print("####### Chile:")
print(lat_obs[19])
print(lon360_to_180(lon_obs[114]))

print("####### Santa Catarina:")
print(lat_obs[25])
print(lon360_to_180(lon_obs[123]))

print("####### Ceará:")
print(lat_obs[33])
print(lon360_to_180(lon_obs[128]))

print("####### Rio Grande do Sul:")
print(lat_obs[23])
print(lon360_to_180(lon_obs[122]))

print("####### Rio Grande do Sul 2:")
print(lat_obs[23])
print(lon360_to_180(lon_obs[123]))

pontos_2025 = {
    "Venezuela": (38, 118),  # lat_obs[36], lon_obs[119] → ( 1.25 , -61.25 )
    "Chile": (19, 114),  # lat_obs[23], lon_obs[115] → (-28.75, -71.25)
    "SC":    (25, 123),  # lat_obs[25], lon_obs[123] → (-26.25, -51.25)
    "riogrande":    (23, 123),  # lat_obs[25], lon_obs[123] → (-26.25, -51.25)    
}

pontos_2016 = {
    "CE":    (33, 128),  # lat_obs[33], lon_obs[128] → ( -6.25, -38.75)
    "RS":    (23, 122),  # lat_obs[23], lon_obs[122] → (-31.25, -53.75)
}

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

outdir = "/dados/mmclima/multimodelo/sazonal/figures/artigo"

path_obs = "/dados/mmclima/multimodelo/artigo/dados"

#2025
ds_gpcp_mar2025 = xr.open_dataset(f"{path_obs}/GPCP-MAR2025.nc")
ds_gpcp_apr2025 = xr.open_dataset(f"{path_obs}/GPCP-APR2025.nc")
ds_gpcp_may2025 = xr.open_dataset(f"{path_obs}/GPCP-MAY2025.nc")

ndays_mar2025 = calendar.monthrange(2025, 3)[1]
ndays_apr2025 = calendar.monthrange(2025, 4)[1]
ndays_may2025 = calendar.monthrange(2025, 5)[1]

mam2025_obs = (((ds_gpcp_mar2025['precip'].values * ndays_mar2025) + 
            (ds_gpcp_apr2025['precip'].values * ndays_apr2025) + 
            (ds_gpcp_may2025['precip'].values * ndays_may2025)) / 3).squeeze()

#2016 .nc
ds_gpcp_mar2016 = xr.open_dataset(f"{path_obs}/obs_gpcp_prec_mon_mean_20160301.nc")
ds_gpcp_apr2016 = xr.open_dataset(f"{path_obs}/obs_gpcp_prec_mon_mean_20160401.nc")
ds_gpcp_may2016 = xr.open_dataset(f"{path_obs}/obs_gpcp_prec_mon_mean_20160501.nc")

ndays_mar2016 = calendar.monthrange(2016, 3)[1]
ndays_apr2016 = calendar.monthrange(2016, 4)[1]
ndays_may2016 = calendar.monthrange(2016, 5)[1]

mam2016_obs = (((ds_gpcp_mar2016['precip'].values * ndays_mar2016) + 
            (ds_gpcp_apr2016['precip'].values * ndays_apr2016) + 
            (ds_gpcp_may2016['precip'].values * ndays_may2016)) / 3).squeeze()

#####
#COX#
#####

anos = [2025]

for ano in anos:

    if ano == 2025:
        pontos = pontos_2025
        path_base = "/dados/mmclima/multimodelo/sazonal/posproc/nmme/v1/forecast/cox/multimodel/2025/2025020100"
        arq_x = f"{path_base}/fcst_prec_varx_seas01_multimodel_calibrated_cox_2025020100.nc"
        arq_fcst = f"{path_base}/fcst_prec_probyfcst_seas01_multimodel_calibrated_cox_2025020100.nc"
        arq_obs  = f"{path_base}/fcst_prec_probybobs_seas01_multimodel_calibrated_cox_2025020100.nc"

        # ===============================
        # Abrindo arquivos auxiliares
        # ===============================

        ds_p_below_inf = xr.open_dataset(f"{path_base}/fcst_prec_ptercinfbelow_seas01_multimodel_calibrated_cox_2025020100.nc")
        ds_p_above_inf = xr.open_dataset(f"{path_base}/fcst_prec_ptercinfabove_seas01_multimodel_calibrated_cox_2025020100.nc")
        ds_p_below_sup = xr.open_dataset(f"{path_base}/fcst_prec_ptercsupbelow_seas01_multimodel_calibrated_cox_2025020100.nc")
        ds_p_above_sup = xr.open_dataset(f"{path_base}/fcst_prec_ptercsupabove_seas01_multimodel_calibrated_cox_2025020100.nc")

        ds_med_obs  = xr.open_dataset(f"{path_base}/fcst_prec_obsmedian_seas01_multimodel_calibrated_cox_2025020100.nc")
        ds_med_fcst = xr.open_dataset(f"{path_base}/fcst_prec_acum_seas01_multimodel_calibrated_cox_2025020100.nc")

        ds_iqr_obs  = xr.open_dataset(f"{path_base}/fcst_prec_obsiqr_seas01_multimodel_calibrated_cox_2025020100.nc")
        ds_iqr_fcst = xr.open_dataset(f"{path_base}/fcst_prec_coxiqr_seas01_multimodel_calibrated_cox_2025020100.nc")

        ds_coef = xr.open_dataset(f"{path_base}/fcst_prec_coef_seas01_multimodel_calibrated_cox_2025020100.nc")

        # Tercis (outro diretório)
        path_regr = "/dados/mmclima/multimodelo/sazonal/posproc/nmme/v1/forecast/regr/multimodel/2025/2025020100"

        ds_terc_inf = xr.open_dataset(f"{path_regr}/fcst_prec_obstercinf_seas01_multimodel_calibrated_regr_2025020100.nc")
        ds_terc_sup = xr.open_dataset(f"{path_regr}/fcst_prec_obstercsup_seas01_multimodel_calibrated_regr_2025020100.nc")

        #Dados observado (para plotar linha)
        dado_obs = mam2025_obs

    elif ano == 2016:
        pontos = pontos_2016
        path_base = "/dados/mmclima/multimodelo/sazonal/posproc/nmme/v1/forecast/cox/multimodel/2016/2016020100"
        arq_x = f"{path_base}/fcst_prec_varx_seas01_multimodel_calibrated_cox_2016020100.nc"
        arq_fcst = f"{path_base}/fcst_prec_probyfcst_seas01_multimodel_calibrated_cox_2016020100.nc"
        arq_obs  = f"{path_base}/fcst_prec_probybobs_seas01_multimodel_calibrated_cox_2016020100.nc"

        # ===============================
        # Abrindo arquivos auxiliares
        # ===============================

        ds_p_below_inf = xr.open_dataset(f"{path_base}/fcst_prec_ptercinfbelow_seas01_multimodel_calibrated_cox_2016020100.nc")
        ds_p_above_inf = xr.open_dataset(f"{path_base}/fcst_prec_ptercinfabove_seas01_multimodel_calibrated_cox_2016020100.nc")
        ds_p_below_sup = xr.open_dataset(f"{path_base}/fcst_prec_ptercsupbelow_seas01_multimodel_calibrated_cox_2016020100.nc")
        ds_p_above_sup = xr.open_dataset(f"{path_base}/fcst_prec_ptercsupabove_seas01_multimodel_calibrated_cox_2016020100.nc")

        ds_med_obs  = xr.open_dataset(f"{path_base}/fcst_prec_obsmedian_seas01_multimodel_calibrated_cox_2016020100.nc")
        ds_med_fcst = xr.open_dataset(f"{path_base}/fcst_prec_acum_seas01_multimodel_calibrated_cox_2016020100.nc")

        ds_iqr_obs  = xr.open_dataset(f"{path_base}/fcst_prec_obsiqr_seas01_multimodel_calibrated_cox_2016020100.nc")
        ds_iqr_fcst = xr.open_dataset(f"{path_base}/fcst_prec_coxiqr_seas01_multimodel_calibrated_cox_2016020100.nc")

        ds_coef = xr.open_dataset(f"{path_base}/fcst_prec_coef_seas01_multimodel_calibrated_cox_2016020100.nc")

        # Tercis (outro diretório)
        path_regr = "/dados/mmclima/multimodelo/sazonal/posproc/nmme/v1/forecast/regr/multimodel/2016/2016020100"

        ds_terc_inf = xr.open_dataset(f"{path_regr}/fcst_prec_obstercinf_seas01_multimodel_calibrated_regr_2016020100.nc")
        ds_terc_sup = xr.open_dataset(f"{path_regr}/fcst_prec_obstercsup_seas01_multimodel_calibrated_regr_2016020100.nc")

        #Dados observado (para plotar linha)
        dado_obs = mam2016_obs


    ds_x = xr.open_dataset(arq_x)
    ds_fcst = xr.open_dataset(arq_fcst)
    ds_obs  = xr.open_dataset(arq_obs)

    var_x = ds_x["varx"]
    var_fcst = ds_fcst["probyfcst"]
    var_obs  = ds_obs["probybobs"]

    curves_type = ["exc","cdf"]

    for curvetype in curves_type:
        for nome, (ilat, ilon) in pontos.items():
            print(nome)
            lat_real = lat_obs[ilat]
            lon_real = lon360_to_180(lon_obs[ilon])   
            lat_str, lon_str = format_coord(lat_real, lon_real)
            print(lat_str)
            print(lon_str)
            x = var_x[:, ilat, ilon]

            # ===== Valores estatísticos =====
            iqr_fcst_val = float(ds_iqr_fcst["coxiqr"][ilat, ilon])
            iqr_obs_val  = float(ds_iqr_obs["obsiqr"][ilat, ilon])

            med_fcst_val = float(ds_med_fcst["acum"][ilat, ilon])
            med_obs_val  = float(ds_med_obs["obsmedian"][ilat, ilon])

            anomaly_val = med_fcst_val - med_obs_val

            beta_val = float(ds_coef["coef"][ilat, ilon])

            terc_inf_val = float(ds_terc_inf["obstercinf"][ilat, ilon])
            terc_sup_val = float(ds_terc_sup["obstercsup"][ilat, ilon])

            p_below_inf = float(ds_p_below_inf["ptercinfbelow"][ilat, ilon])
            p_below_sup = float(ds_p_below_sup["ptercsupbelow"][ilat, ilon])
            p_above_inf = float(ds_p_above_inf["ptercinfabove"][ilat, ilon])
            p_above_sup = float(ds_p_above_sup["ptercsupabove"][ilat, ilon])

            #Serie
            y_fcst = var_fcst[:, ilat, ilon]
            y_obs  = var_obs[:, ilat, ilon]

            x_vals = x.values

            if curvetype == "cdf":

                y_fcst_vals = 1 - y_fcst.values
                y_obs_vals  = 1 - y_obs.values

                x_plot = np.concatenate(([0], x_vals))
                y_fcst_plot = np.concatenate(([0], y_fcst_vals))
                y_obs_plot  = np.concatenate(([0], y_obs_vals))

            else:

                y_fcst_vals = y_fcst.values
                y_obs_vals  = y_obs.values

                x_plot = np.concatenate(([0], x_vals))
                y_fcst_plot = np.concatenate(([1], y_fcst_vals))
                y_obs_plot  = np.concatenate(([1], y_obs_vals))

            plt.figure(figsize=(6, 6))

            if curvetype == "cdf":
                plt.step(x_plot, y_fcst_plot, color="blue", linewidth=2,
                        label="Forecast CDF", where='post')

                plt.step(x_plot, y_obs_plot, color="red", linewidth=2,
                        label="Climatological CDF", where='post')
            else:
                plt.step(x_plot, y_fcst_plot, color="blue", linewidth=2,
                        label="Forecast EDF", where='post')

                plt.step(x_plot, y_obs_plot, color="red", linewidth=2,
                        label="Climatological EDF", where='post')

            if ano == 2025:
                if curvetype == "cdf":
                    plt.title(f"e) Precip. Fcst. Calibrated Multi-Model (Cox) \nfor MAM 2025 issued: Feb 2025 Lat:{lat_str} Lon:{lon_str}", 
                            fontsize=11, fontweight='bold')
                elif curvetype == "exc":
                    plt.title(f"f) Precip. Fcst. Calibrated Multi-Model (Cox) \nfor MAM 2025 issued: Feb 2025 Lat:{lat_str} Lon:{lon_str}", 
                            fontsize=11, fontweight='bold')                            
                label_obs = "Obs. MAM 2025"
            else:
                if curvetype == "cdf":               
                    plt.title(f"e) Precip. Fcst. Calibrated Multi-Model (Cox) \nfor MAM 2016 issued: Feb 2025 Lat:{lat_str} Lon:{lon_str}", 
                            fontsize=12, fontweight='bold')
                elif curvetype == "exc":
                    plt.title(f"f) Precip. Fcst. Calibrated Multi-Model (Cox) \nfor MAM 2016 issued: Feb 2025 Lat:{lat_str} Lon:{lon_str}", 
                            fontsize=11, fontweight='bold')   
                label_obs = "Obs. MAM 2016"

            #Plotar linha vertical (dado observado atual)
            plt.axvline(x=dado_obs[ilat, ilon], color='black', linewidth=2, label=label_obs)

            #Plotar linha pontilhada dos tercis
            if curvetype == "cdf":
                y_inf = p_below_inf
                y_sup = p_below_sup
            elif curvetype == "exc":
                y_inf = p_above_inf
                y_sup = p_above_sup

            # ---- Linha para terc_inf_val ----
            # vertical
            plt.plot(
                [terc_inf_val, terc_inf_val],
                [-0.05, y_inf],
                linestyle='--',
                color='black',
                linewidth=1
            )

            # horizontal até eixo Y (x=0)
            plt.plot(
                [-0.05, terc_inf_val],
                [y_inf, y_inf],
                linestyle='--',
                color='black',
                linewidth=1
            )

            plt.text(
                terc_inf_val,   # x
                0,              # y
                r"$\mathbf{T\,1}$",
                ha='center',
                va='top',
                fontsize=9, 
                fontweight='bold'
            )

            # ---- Linha para terc_sup_val ----
            # vertical
            plt.plot(
                [terc_sup_val, terc_sup_val],
                [-0.05, y_sup],
                linestyle='--',
                color='black',
                linewidth=1
            )

            # horizontal até eixo Y
            plt.plot(
                [-0.05, terc_sup_val],
                [y_sup, y_sup],
                linestyle='--',
                color='black',
                linewidth=1
            )

            plt.text(
                terc_sup_val,
                0,
                r"$\mathbf{T\,2}$",
                ha='center',
                va='top',
                fontsize=9, 
                fontweight='bold'
            )

            plt.xlabel("Precipitation (mm)",fontsize=15)

            if curvetype == "cdf":
                plt.ylabel("Cumulative Probability",fontsize=15)
            else:
                plt.ylabel("Exceedance Probability",fontsize=15)     


            plt.grid(False)
            #plt.xlim(left=float(x.min()-200))
            plt.ylim(-0.05, 1.05)
            if nome == "CE":
                plt.xlim(left=0, right=x.max())
            elif nome == "Venezuela":
                plt.xlim(left=float(x.min()-200), right=x.max()+350)
            elif nome == "RS":
                plt.xlim(left=float(x.min()-200), right=x.max()+250) 
            # elif nome == "riogrande":
            #     plt.xlim(left=float(x.min()-200), right=x.max()+50)                                              
            else:
                plt.xlim(left=float(x.min()-200), right=x.max())
            if curvetype == "cdf":
                leg = plt.legend(loc='upper left', fontsize=9)
            else:
                leg = plt.legend(loc='upper right', fontsize=9)

            leg.get_frame().set_facecolor('white')
            leg.get_frame().set_alpha(1)

            ax = plt.gca()

            for spine in ax.spines.values():
                spine.set_linewidth(1.5)  

            if curvetype == "cdf":

                # ===== RIGHT (probabilidades) =====
                text_right = (
                    r"$\bf{Forecast\ (x)}$" + "\n"
                    f"IQRx = {iqr_fcst_val:.1f}mm\n"
                    f"medianₓ = {med_fcst_val:.1f}mm\n\n"
                    r"$\bf{Observation\ (y)}$" + "\n"
                    f"IQRy = {iqr_obs_val:.1f}mm\n"
                    f"medianᵧ = {med_obs_val:.1f}mm\n\n"
                    f"anomaly = {anomaly_val:.1f}mm\n"
                    f"beta = {beta_val:.2f}\n\n\n"  

                    r"$\bf{Forecast}$" + "\n" +
                    r"$\bf{Probabilities\ (p)}$" + "\n"
                    f"P<(T1={terc_inf_val:.1f}) = {p_below_inf*100:.0f}%\n"
                    f"P<(T2={terc_sup_val:.1f}) = {p_below_sup*100:.0f}%"
                )

                ax.text(
                    0.98, 0.8, text_right,
                    transform=ax.transAxes,
                    fontsize=9,
                    va='top',
                    ha='right'
                )

            else:  # ===== EXC =====

                # ===== RIGHT (estatísticas) =====
                text_right = (
                    r"$\bf{Forecast\ (x)}$" + "\n"
                    f"IQRx = {iqr_fcst_val:.1f}mm\n"
                    f"medianₓ = {med_fcst_val:.1f}mm\n\n"
                    r"$\bf{Observation\ (y)}$" + "\n"
                    f"IQRy = {iqr_obs_val:.1f}mm\n"
                    f"medianᵧ = {med_obs_val:.1f}mm\n\n"
                    f"anomaly = {anomaly_val:.1f}mm\n"
                    f"beta = {beta_val:.2f}\n\n"

                    r"$\bf{Forecast}$" + "\n" +
                    r"$\bf{Probabilities\ (p)}$" + "\n"
                    f"P>(T1={terc_inf_val:.1f}) = {p_above_inf*100:.0f}%\n"
                    f"P>(T2={terc_sup_val:.1f}) = {p_above_sup*100:.0f}%"                    
                )

                ax.text(
                    0.98, 0.8, text_right,
                    transform=ax.transAxes,
                    fontsize=9,
                    va='top',
                    ha='right'
                )
                
            plt.tight_layout()
            if ano == 2025:
                plt.savefig(f"{outdir}/curve_{curvetype}_cox_2025020100_{nome}.png", dpi=150)
            elif ano == 2016:
                plt.savefig(f"{outdir}/curve_{curvetype}_cox_2016020100_{nome}.png", dpi=150)                
            plt.close()

###########    
#REGRESSÃO#
###########

for ano in anos:

    if ano == 2025:
        pontos = pontos_2025
        path_base = "/dados/mmclima/multimodelo/sazonal/posproc/nmme/v1/forecast/regr/multimodel/2025/2025020100"
        arq_obsmean = f"{path_base}/fcst_prec_obsmean_seas01_multimodel_calibrated_regr_2025020100.nc"
        arq_obsstd  = f"{path_base}/fcst_prec_obsstd_seas01_multimodel_calibrated_regr_2025020100.nc"
        arq_fcstmean = f"{path_base}/fcst_prec_acum_seas01_multimodel_calibrated_regr_2025020100.nc"
        arq_fcststd  = f"{path_base}/fcst_prec_stdfcst_seas01_multimodel_calibrated_regr_2025020100.nc"
        arq_terc  = f"{path_base}/fcst_prec_terc_seas01_multimodel_calibrated_regr_2025020100.nc"

        # ===============================
        # Abrindo arquivos auxiliares
        # ===============================

        ds_p_below_inf = xr.open_dataset(f"{path_base}/fcst_prec_ptercinfbelow_seas01_multimodel_calibrated_regr_2025020100.nc")
        ds_p_above_inf = xr.open_dataset(f"{path_base}/fcst_prec_ptercinfabove_seas01_multimodel_calibrated_regr_2025020100.nc")
        ds_p_below_sup = xr.open_dataset(f"{path_base}/fcst_prec_ptercsupbelow_seas01_multimodel_calibrated_regr_2025020100.nc")
        ds_p_above_sup = xr.open_dataset(f"{path_base}/fcst_prec_ptercsupabove_seas01_multimodel_calibrated_regr_2025020100.nc")

        ds_corr = xr.open_dataset(f"{path_base}/fcst_prec_corr_seas01_multimodel_calibrated_regr_2025020100.nc")

        # Tercis (outro diretório)
        path_regr = "/dados/mmclima/multimodelo/sazonal/posproc/nmme/v1/forecast/regr/multimodel/2025/2025020100"
        ds_terc_inf = xr.open_dataset(f"{path_regr}/fcst_prec_obstercinf_seas01_multimodel_calibrated_regr_2025020100.nc")
        ds_terc_sup = xr.open_dataset(f"{path_regr}/fcst_prec_obstercsup_seas01_multimodel_calibrated_regr_2025020100.nc")

    elif ano == 2016:
        pontos = pontos_2016
        path_base = "/dados/mmclima/multimodelo/sazonal/posproc/nmme/v1/forecast/regr/multimodel/2016/2016020100"
        arq_obsmean = f"{path_base}/fcst_prec_obsmean_seas01_multimodel_calibrated_regr_2016020100.nc"
        arq_obsstd  = f"{path_base}/fcst_prec_obsstd_seas01_multimodel_calibrated_regr_2016020100.nc"
        arq_fcstmean = f"{path_base}/fcst_prec_acum_seas01_multimodel_calibrated_regr_2016020100.nc"
        arq_fcststd  = f"{path_base}/fcst_prec_stdfcst_seas01_multimodel_calibrated_regr_2016020100.nc"
        arq_terc  = f"{path_base}/fcst_prec_terc_seas01_multimodel_calibrated_regr_2016020100.nc"

        # ===============================
        # Abrindo arquivos auxiliares
        # ===============================

        ds_p_below_inf = xr.open_dataset(f"{path_base}/fcst_prec_ptercinfbelow_seas01_multimodel_calibrated_regr_2016020100.nc")
        ds_p_above_inf = xr.open_dataset(f"{path_base}/fcst_prec_ptercinfabove_seas01_multimodel_calibrated_regr_2016020100.nc")
        ds_p_below_sup = xr.open_dataset(f"{path_base}/fcst_prec_ptercsupbelow_seas01_multimodel_calibrated_regr_2016020100.nc")
        ds_p_above_sup = xr.open_dataset(f"{path_base}/fcst_prec_ptercsupabove_seas01_multimodel_calibrated_regr_2016020100.nc")

        ds_corr = xr.open_dataset(f"{path_base}/fcst_prec_corr_seas01_multimodel_calibrated_regr_2016020100.nc")

        # Tercis (outro diretório)
        path_regr = "/dados/mmclima/multimodelo/sazonal/posproc/nmme/v1/forecast/regr/multimodel/2016/2016020100"
        ds_terc_inf = xr.open_dataset(f"{path_regr}/fcst_prec_obstercinf_seas01_multimodel_calibrated_regr_2016020100.nc")
        ds_terc_sup = xr.open_dataset(f"{path_regr}/fcst_prec_obstercsup_seas01_multimodel_calibrated_regr_2016020100.nc")

    ds_obsmean  = xr.open_dataset(arq_obsmean)
    ds_obsstd   = xr.open_dataset(arq_obsstd)
    ds_fcstmean = xr.open_dataset(arq_fcstmean)
    ds_fcststd  = xr.open_dataset(arq_fcststd)
    ds_terc = xr.open_dataset(arq_terc)

    obs_mean  = ds_obsmean[list(ds_obsmean.data_vars)[0]]
    obs_std   = ds_obsstd[list(ds_obsstd.data_vars)[0]]
    correlat = ds_corr[list(ds_corr.data_vars)[0]]

    fcst_mean = ds_fcstmean[list(ds_fcstmean.data_vars)[0]]
    fcst_std  = ds_fcststd[list(ds_fcststd.data_vars)[0]]

    prob_terc = ds_terc[list(ds_terc.data_vars)[0]]

    curves_type = ["exc","cdf"]

    for curvetype in curves_type:
        for nome, (ilat, ilon) in pontos.items():

            #VALORES PARA ESCREVER
            terc_inf_val = float(ds_terc_inf["obstercinf"][ilat, ilon])
            terc_sup_val = float(ds_terc_sup["obstercsup"][ilat, ilon])
            p_below_inf = float(ds_p_below_inf["ptercinfbelow"][ilat, ilon])
            p_below_sup = float(ds_p_below_sup["ptercsupbelow"][ilat, ilon])
            p_above_inf = float(ds_p_above_inf["ptercinfabove"][ilat, ilon])
            p_above_sup = float(ds_p_above_sup["ptercsupabove"][ilat, ilon])
            
            if ano == 2025:
                arq_obstotal = f"{path_base}/fcst_prec_obstotal_seas01_multimodel_calibrated_regr_2025020100.nc"
            else:
                arq_obstotal = f"{path_base}/fcst_prec_obstotal_seas01_multimodel_calibrated_regr_2016020100.nc"

            ds_obstotal = xr.open_dataset(arq_obstotal)
            obs_total = ds_obstotal[list(ds_obstotal.data_vars)[0]]

            lat_real = lat_obs[ilat]
            lon_real = lon360_to_180(lon_obs[ilon])
            lat_str, lon_str = format_coord(lat_real, lon_real)

            # ============================
            # Séries observadas
            # ============================
            obs_point = obs_total[:, ilat, ilon].values
            obs_point = obs_point[~np.isnan(obs_point)]
            obs_sorted = np.sort(obs_point)
            n = len(obs_sorted)

            if n > 0:
                # Probabilidade acumulada empírica
                y_cdf = np.arange(1, n+1) / n

                # -------------------
                # CDF empírica
                # -------------------
                x_emp_cdf = np.concatenate(([0], obs_sorted, [obs_sorted[-1]+200]))
                y_emp_cdf = np.concatenate(([0], y_cdf, [1]))

                # -------------------
                # Excedência empírica
                # -------------------
                x_emp_exc = np.concatenate(([0], obs_sorted, [obs_sorted[-1]+200]))
                y_emp_exc = np.concatenate(([1], 1 - y_cdf, [0]))

            # ============================
            # Curvas Normais
            # ============================
            x_norm = np.linspace(0, np.max(obs_sorted)+200, 200)
            mu_obs  = obs_mean[ilat, ilon]
            sd_obs  = obs_std[ilat, ilon]
            mu_fcst = fcst_mean[ilat, ilon]
            sd_fcst = fcst_std[ilat, ilon]

            if curvetype == "cdf":
                y_obs_norm  = norm.cdf(x_norm, loc=mu_obs, scale=sd_obs)
                y_fcst_norm = norm.cdf(x_norm, loc=mu_fcst, scale=sd_fcst)
            else:
                y_obs_norm  = 1 - norm.cdf(x_norm, loc=mu_obs, scale=sd_obs)
                y_fcst_norm = 1 - norm.cdf(x_norm, loc=mu_fcst, scale=sd_fcst)

            # ============================
            # PLOT
            # ============================
            plt.figure(figsize=(6,6))       

            # Linha normal (fit)
            plt.plot(x_norm, y_obs_norm, color="red", linewidth=2, linestyle="--",
                    label="Normal Fit", zorder = 1)

            if curvetype == "cdf":
                # empírica em escada, normal em linha
                plt.step(x_emp_cdf, y_emp_cdf, color="red", linewidth=2, where="post",
                        label="Climatological CDF", zorder = 2)
                plt.plot(x_norm, y_fcst_norm, color="blue", linewidth=2,
                        label="Forecast CDF", zorder = 3) 
            else:
                plt.step(x_emp_exc, y_emp_exc, color="red", linewidth=2, where="post",
                        label="Climatological EDF", zorder = 2)
                plt.plot(x_norm, y_fcst_norm, color="blue", linewidth=2,
                        label="Forecast EDF", zorder = 3) 

            if ano == 2025:
                if curvetype == "cdf":
                    plt.title(f"a) Precip. Fcst. Calibrated Multi-Model (Normal) \nfor MAM 2025 issued: Feb 2025 Lat:{lat_str} Lon:{lon_str}", 
                            fontsize=11, fontweight='bold')
                elif curvetype == "exc":
                    plt.title(f"b) Precip. Fcst. Calibrated Multi-Model (Normal) \nfor MAM 2025 issued: Feb 2025 Lat:{lat_str} Lon:{lon_str}", 
                            fontsize=11, fontweight='bold')                            
                label_obs = "Obs. MAM 2025"
            else:
                if curvetype == "cdf":                
                    plt.title(f"a) Precip. Fcst. Calibrated Multi-Model (Normal) \nfor MAM 2016 issued: Feb 2025 Lat:{lat_str} Lon:{lon_str}", 
                            fontsize=11, fontweight='bold')
                elif curvetype == "exc":
                    plt.title(f"b) Precip. Fcst. Calibrated Multi-Model (Normal) \nfor MAM 2016 issued: Feb 2025 Lat:{lat_str} Lon:{lon_str}", 
                            fontsize=11, fontweight='bold')   

            #Plotar linha vertical (dado observado atual)
            plt.axvline(x=dado_obs[ilat, ilon], color='black', linewidth=2, label=label_obs)

            # ============================
            # Título e eixos
            # ============================
            plt.xlabel("Precipitation (mm)", fontsize=15)
            plt.ylabel("Cumulative Probability" if curvetype=="cdf" else "Exceedance Probability",
                    fontsize=15)

            #Plotar linha pontilhada dos tercis
            if curvetype == "cdf":
                y_inf = p_below_inf/100
                y_sup = p_below_sup/100
            elif curvetype == "exc":
                y_inf = p_above_inf/100
                y_sup = p_above_sup/100

            # ---- Linha para terc_inf_val ----
            # vertical
            plt.plot(
                [terc_inf_val, terc_inf_val],
                [-0.05, y_inf],
                linestyle='--',
                color='black',
                linewidth=1
            )

            # horizontal até eixo Y (x=0)
            plt.plot(
                [-0.05, terc_inf_val],
                [y_inf, y_inf],
                linestyle='--',
                color='black',
                linewidth=1
            )

            plt.text(
                terc_inf_val,   # x
                0,              # y
                r"$\mathbf{T\,1}$",
                ha='center',
                va='top',
                fontsize=9, 
                fontweight='bold'
            )

            # ---- Linha para terc_sup_val ----
            # vertical
            plt.plot(
                [terc_sup_val, terc_sup_val],
                [-0.05, y_sup],
                linestyle='--',
                color='black',
                linewidth=1
            )

            # horizontal até eixo Y
            plt.plot(
                [-0.05, terc_sup_val],
                [y_sup, y_sup],
                linestyle='--',
                color='black',
                linewidth=1
            )

            plt.text(
                terc_sup_val,
                0,
                r"$\mathbf{T\,2}$",
                ha='center',
                va='top',
                fontsize=9, 
                fontweight='bold'
            )

            plt.xlim(0, np.max(obs_sorted) + 200)
            plt.ylim(-0.05, 1.05)
            plt.grid(False)

            # Legenda fixa
            if curvetype == "cdf":
                leg = plt.legend(loc='upper left', fontsize=9)
            else:
                leg = plt.legend(loc='upper right', fontsize=9)

            leg.get_frame().set_facecolor('white')
            leg.get_frame().set_alpha(1)

            ax = plt.gca()

            for spine in ax.spines.values():
                spine.set_linewidth(1.5)

            # if curvetype == "cdf":

            #         # # ===== LEFT (estatísticas) =====
            #         # text_left = (
            #         #     r"$\bf{Forecast\ (x)}$" + "\n"
            #         #     f"stdvₓ = {fcst_std[ilat,ilon]:.1f}mm\n"
            #         #     f"meanₓ = {fcst_mean[ilat,ilon]:.1f}mm\n\n"
            #         #     r"$\bf{Observation\ (y)}$" + "\n"
            #         #     f"stdvᵧ = {obs_std[ilat,ilon]:.1f}mm\n"
            #         #     f"meanᵧ = {obs_mean[ilat,ilon]:.1f}mm\n\n"
            #         #     f"anomaly = {fcst_mean[ilat,ilon] - obs_mean[ilat,ilon]:.1f}mm\n"
            #         #     f"r = {correlat[ilat,ilon]:.2f}"
            #         # )

            #         # ax.text(
            #         #     0.02, 0.7, text_left,
            #         #     transform=ax.transAxes,
            #         #     fontsize=8,
            #         #     va='top'
            #         # )

            #         # ===== RIGHT (probabilidades) =====
            #         text_right = (
            #             r"$\bf{Forecast\ (x)}$" + "\n"
            #             f"stdvₓ = {fcst_std[ilat,ilon]:.1f}mm\n"
            #             f"meanₓ = {fcst_mean[ilat,ilon]:.1f}mm\n\n"
            #             r"$\bf{Observation\ (y)}$" + "\n"
            #             f"stdvᵧ = {obs_std[ilat,ilon]:.1f}mm\n"
            #             f"meanᵧ = {obs_mean[ilat,ilon]:.1f}mm\n\n"
            #             f"anomaly = {fcst_mean[ilat,ilon] - obs_mean[ilat,ilon]:.1f}mm\n"
            #             f"r = {correlat[ilat,ilon]:.2f}\n\n"    

            #             r"$\bf{Forecast}$" + "\n" +
            #             r"$\bf{Probabilities\ (p)}$" + "\n"
            #             f"P<(T1={terc_inf_val:.1f}) = {p_below_inf:.0f}%\n"
            #             f"P<(T2={terc_sup_val:.1f}) = {p_below_sup:.0f}%"
            #         )

            #         ax.text(
            #             0.98, 0.8, text_right,
            #             transform=ax.transAxes,
            #             fontsize=9,
            #             va='top',
            #             ha='right'
            #         )

            # else:  # ===== EXC =====

            #         # # ===== LEFT (probabilidades) =====
            #         # text_left = (
            #         #     r"$\bf{Forecast}$" + "\n" +
            #         #     r"$\bf{Probabilities\ (p)}$" + "\n"
            #         #     f"P>(T1={terc_inf_val:.1f}) = {p_above_inf:.0f}%\n"
            #         #     f"P>(T2={terc_sup_val:.1f}) = {p_above_sup:.0f}%"
            #         # )

            #         # ax.text(
            #         #     0.02, 0.7, text_left,
            #         #     transform=ax.transAxes,
            #         #     fontsize=8,
            #         #     va='top'
            #         # )

            #         # ===== RIGHT (estatísticas) =====
            #         text_right = (
            #             r"$\bf{Forecast\ (x)}$" + "\n"
            #             f"stdvₓ = {fcst_std[ilat,ilon]:.1f}mm\n"
            #             f"meanₓ = {fcst_mean[ilat,ilon]:.1f}mm\n\n"
            #             r"$\bf{Observation\ (y)}$" + "\n"
            #             f"stdvᵧ = {obs_std[ilat,ilon]:.1f}mm\n"
            #             f"meanᵧ = {obs_mean[ilat,ilon]:.1f}mm\n\n"
            #             f"anomaly = {fcst_mean[ilat,ilon] - obs_mean[ilat,ilon]:.1f}mm\n"
            #             f"r = {correlat[ilat,ilon]:.2f}\n\n"    

            #             r"$\bf{Forecast}$" + "\n" +
            #             r"$\bf{Probabilities\ (p)}$" + "\n"
            #             f"P<(T1={terc_inf_val:.1f}) = {p_below_inf:.0f}%\n"
            #             f"P<(T2={terc_sup_val:.1f}) = {p_below_sup:.0f}%"
            #         )

            #         ax.text(
            #             0.98, 0.8, text_right,
            #             transform=ax.transAxes,
            #             fontsize=9,
            #             va='top',
            #             ha='right'
            #         )

            plt.tight_layout()
            if ano == 2025:
                plt.savefig(f"{outdir}/curve_{curvetype}_regr_2025020100_{nome}.png", dpi=150)
            else:
                plt.savefig(f"{outdir}/curve_{curvetype}_regr_2016020100_{nome}.png", dpi=150)                
            plt.close()


################
#   GAMMA      #
################

for ano in anos:
    
    if ano == 2025:
        pontos = pontos_2025
        path_gamma = "/dados/mmclima/multimodelo/sazonal/posproc/nmme/v1/forecast/gamma/multimodel/2025/2025020100"
        path_regr= "/dados/mmclima/multimodelo/sazonal/posproc/nmme/v1/forecast/regr/multimodel/2025/2025020100"

        arq_fcst_alpha = f"{path_gamma}/fcst_prec_alphafcst_seas01_multimodel_calibrated_gamma_2025020100.nc"
        arq_fcst_beta  = f"{path_gamma}/fcst_prec_betafcst_seas01_multimodel_calibrated_gamma_2025020100.nc"
        arq_obs_alpha = f"{path_gamma}/fcst_prec_alphaobs_seas01_multimodel_calibrated_gamma_2025020100.nc"
        arq_obs_beta  = f"{path_gamma}/fcst_prec_betaobs_seas01_multimodel_calibrated_gamma_2025020100.nc"

        #DATASETS PARA ESCREVER NO GRAFICO
        ds_corr = xr.open_dataset(f"{path_gamma}/fcst_prec_corr_seas01_multimodel_calibrated_gamma_2025020100.nc")
        ds_terc_inf = xr.open_dataset(f"{path_regr}/fcst_prec_obstercinf_seas01_multimodel_calibrated_regr_2025020100.nc")
        ds_terc_sup = xr.open_dataset(f"{path_regr}/fcst_prec_obstercsup_seas01_multimodel_calibrated_regr_2025020100.nc")
        ds_obsmean  = xr.open_dataset(f"{path_regr}/fcst_prec_obsmean_seas01_multimodel_calibrated_regr_2025020100.nc")
        ds_obsstd   = xr.open_dataset(f"{path_regr}/fcst_prec_obsstd_seas01_multimodel_calibrated_regr_2025020100.nc")
        ds_fcstmean = xr.open_dataset(f"{path_gamma}/fcst_prec_acum_seas01_multimodel_calibrated_gamma_2025020100.nc")
        ds_fcststd  = xr.open_dataset(f"{path_gamma}/fcst_prec_stdfcst_seas01_multimodel_calibrated_gamma_2025020100.nc")
        ds_p_below_inf = xr.open_dataset(f"{path_gamma}/fcst_prec_ptercinfbelow_seas01_multimodel_calibrated_gamma_2025020100.nc")
        ds_p_above_inf = xr.open_dataset(f"{path_gamma}/fcst_prec_ptercinfabove_seas01_multimodel_calibrated_gamma_2025020100.nc")
        ds_p_below_sup = xr.open_dataset(f"{path_gamma}/fcst_prec_ptercsupbelow_seas01_multimodel_calibrated_gamma_2025020100.nc")
        ds_p_above_sup = xr.open_dataset(f"{path_gamma}/fcst_prec_ptercsupabove_seas01_multimodel_calibrated_gamma_2025020100.nc")

        ds_corr = xr.open_dataset(f"{path_gamma}/fcst_prec_corr_seas01_multimodel_calibrated_gamma_2025020100.nc")

    elif ano == 2016:
        pontos = pontos_2016
        path_gamma = "/dados/mmclima/multimodelo/sazonal/posproc/nmme/v1/forecast/gamma/multimodel/2016/2016020100"
        path_regr= "/dados/mmclima/multimodelo/sazonal/posproc/nmme/v1/forecast/regr/multimodel/2016/2016020100"

        arq_fcst_alpha = f"{path_gamma}/fcst_prec_alphafcst_seas01_multimodel_calibrated_gamma_2016020100.nc"
        arq_fcst_beta  = f"{path_gamma}/fcst_prec_betafcst_seas01_multimodel_calibrated_gamma_2016020100.nc"
        arq_obs_alpha = f"{path_gamma}/fcst_prec_alphaobs_seas01_multimodel_calibrated_gamma_2016020100.nc"
        arq_obs_beta  = f"{path_gamma}/fcst_prec_betaobs_seas01_multimodel_calibrated_gamma_2016020100.nc"

        #DATASETS PARA ESCREVER NO GRAFICO
        ds_corr = xr.open_dataset(f"{path_gamma}/fcst_prec_corr_seas01_multimodel_calibrated_gamma_2016020100.nc")
        ds_terc_inf = xr.open_dataset(f"{path_regr}/fcst_prec_obstercinf_seas01_multimodel_calibrated_regr_2016020100.nc")
        ds_terc_sup = xr.open_dataset(f"{path_regr}/fcst_prec_obstercsup_seas01_multimodel_calibrated_regr_2016020100.nc")
        ds_obsmean  = xr.open_dataset(f"{path_regr}/fcst_prec_obsmean_seas01_multimodel_calibrated_regr_2016020100.nc")
        ds_obsstd   = xr.open_dataset(f"{path_regr}/fcst_prec_obsstd_seas01_multimodel_calibrated_regr_2016020100.nc")
        ds_fcstmean = xr.open_dataset(f"{path_gamma}/fcst_prec_acum_seas01_multimodel_calibrated_gamma_2016020100.nc")
        ds_fcststd  = xr.open_dataset(f"{path_gamma}/fcst_prec_stdfcst_seas01_multimodel_calibrated_gamma_2016020100.nc")
        ds_p_below_inf = xr.open_dataset(f"{path_gamma}/fcst_prec_ptercinfbelow_seas01_multimodel_calibrated_gamma_2016020100.nc")
        ds_p_above_inf = xr.open_dataset(f"{path_gamma}/fcst_prec_ptercinfabove_seas01_multimodel_calibrated_gamma_2016020100.nc")
        ds_p_below_sup = xr.open_dataset(f"{path_gamma}/fcst_prec_ptercsupbelow_seas01_multimodel_calibrated_gamma_2016020100.nc")
        ds_p_above_sup = xr.open_dataset(f"{path_gamma}/fcst_prec_ptercsupabove_seas01_multimodel_calibrated_gamma_2016020100.nc")

        ds_corr = xr.open_dataset(f"{path_gamma}/fcst_prec_corr_seas01_multimodel_calibrated_gamma_2016020100.nc")


    obs_mean  = ds_obsmean[list(ds_obsmean.data_vars)[0]]
    obs_std   = ds_obsstd[list(ds_obsstd.data_vars)[0]]
    correlat = ds_corr[list(ds_corr.data_vars)[0]]
    fcst_mean = ds_fcstmean[list(ds_fcstmean.data_vars)[0]]
    fcst_std  = ds_fcststd[list(ds_fcststd.data_vars)[0]]

    ds_fcst_alpha = xr.open_dataset(arq_fcst_alpha)
    ds_fcst_beta  = xr.open_dataset(arq_fcst_beta)
    ds_obs_alpha = xr.open_dataset(arq_obs_alpha)
    ds_obs_beta  = xr.open_dataset(arq_obs_beta)

    fcst_alpha = ds_fcst_alpha[list(ds_fcst_alpha.data_vars)[0]]
    fcst_beta  = ds_fcst_beta[list(ds_fcst_beta.data_vars)[0]]

    obs_alpha = ds_obs_alpha[list(ds_obs_alpha.data_vars)[0]]
    obs_beta  = ds_obs_beta[list(ds_obs_beta.data_vars)[0]]

    curves_type = ["exc","cdf"]

    for curvetype in curves_type:
        for nome, (ilat, ilon) in pontos.items():

            #VALORES PARA ESCREVER
            terc_inf_val = float(ds_terc_inf["obstercinf"][ilat, ilon])
            terc_sup_val = float(ds_terc_sup["obstercsup"][ilat, ilon])
            p_below_inf = float(ds_p_below_inf["ptercinfbelow"][ilat, ilon])
            p_below_sup = float(ds_p_below_sup["ptercsupbelow"][ilat, ilon])
            p_above_inf = float(ds_p_above_inf["ptercinfabove"][ilat, ilon])
            p_above_sup = float(ds_p_above_sup["ptercsupabove"][ilat, ilon])

            # ============================
            # Séries observadas
            # ============================
            obs_series = obs_total[:, ilat, ilon].values
            obs_series = obs_series[~np.isnan(obs_series)]
            obs_sorted = np.sort(obs_series)
            n = len(obs_sorted)

            if n > 0:
                # Probabilidade acumulada empírica
                y_cdf = np.arange(1, n+1) / n

                # -------------------
                # CDF empírica
                # -------------------
                x_emp_cdf = np.concatenate(([0], obs_sorted, [obs_sorted[-1]+200]))
                y_emp_cdf = np.concatenate(([0], y_cdf, [1]))

                # -------------------
                # Excedência empírica
                # -------------------
                x_emp_exc = np.concatenate(([0], obs_sorted, [obs_sorted[-1]+200]))
                y_emp_exc = np.concatenate(([1], 1 - y_cdf, [0]))

            # ============================
            # Curvas Gamma
            # ============================
            x_gamma = np.linspace(0, np.max(obs_sorted) + 200)
            a_obs  = obs_alpha[ilat, ilon]
            b_obs  = obs_beta[ilat, ilon]
            a_fcst = fcst_alpha[ilat, ilon]
            b_fcst = fcst_beta[ilat, ilon]

            if curvetype == "cdf":
                y_obs_gamma  = gamma.cdf(x_gamma, a=a_obs,  scale=b_obs)
                y_fcst_gamma = gamma.cdf(x_gamma, a=a_fcst, scale=b_fcst)
            else:
                y_obs_gamma  = 1 - gamma.cdf(x_gamma, a=a_obs,  scale=b_obs)
                y_fcst_gamma = 1 - gamma.cdf(x_gamma, a=a_fcst, scale=b_fcst)

            # ============================
            # PLOT
            # ============================
            plt.figure(figsize=(6,6))

            # Linha da Gamma Fit (observada)
            plt.plot(x_gamma, y_obs_gamma, color="red", linewidth=2, linestyle="--",
                    label="Gamma Fit", zorder = 1)

            if curvetype == "cdf":
                plt.step(x_emp_cdf, y_emp_cdf, color="red", linewidth=2, where="post",
                        label="Climatological CDF", zorder = 2)
                plt.plot(x_gamma, y_fcst_gamma, color="blue", linewidth=2,
                        label="Forecast CDF", zorder = 3)                      
            else:
                plt.step(x_emp_exc, y_emp_exc, color="red", linewidth=2, where="post",
                        label="Climatological EDF", zorder = 2)            
                plt.plot(x_gamma, y_fcst_gamma, color="blue", linewidth=2,
                        label="Forecast EDF", zorder = 3)            

            if ano == 2025:
                if curvetype == "cdf":
                    plt.title(f"c) Precip. Fcst. Calibrated Multi-Model (Gamma) \nfor MAM 2025 issued: Feb 2025 Lat:{lat_str} Lon:{lon_str}", 
                            fontsize=12, fontweight='bold')
                elif curvetype == "exc":
                    plt.title(f"d) Precip. Fcst. Calibrated Multi-Model (Gamma) \nfor MAM 2025 issued: Feb 2025 Lat:{lat_str} Lon:{lon_str}", 
                            fontsize=12, fontweight='bold')                            
                label_obs = "Obs. MAM 2025"
            else:
                if curvetype == "cdf":                
                    plt.title(f"c) Precip. Fcst. Calibrated Multi-Model (Gamma) \nfor MAM 2016 issued: Feb 2025 Lat:{lat_str} Lon:{lon_str}", 
                            fontsize=12, fontweight='bold')
                elif curvetype == "exc":
                    plt.title(f"d) Precip. Fcst. Calibrated Multi-Model (Gamma) \nfor MAM 2016 issued: Feb 2025 Lat:{lat_str} Lon:{lon_str}", 
                            fontsize=12, fontweight='bold')   


            #Plotar linha vertical (dado observado atual)
            plt.axvline(x=dado_obs[ilat, ilon], color='black', linewidth=2, label=label_obs)

            #Plotar linha pontilhada dos tercis
            if curvetype == "cdf":
                y_inf = p_below_inf
                y_sup = p_below_sup
            elif curvetype == "exc":
                y_inf = p_above_inf
                y_sup = p_above_sup

            # ---- Linha para terc_inf_val ----
            # vertical
            plt.plot(
                [terc_inf_val, terc_inf_val],
                [-0.05, y_inf],
                linestyle='--',
                color='black',
                linewidth=1
            )

            # horizontal até eixo Y (x=0)
            plt.plot(
                [-0.05, terc_inf_val],
                [y_inf, y_inf],
                linestyle='--',
                color='black',
                linewidth=1
            )

            plt.text(
                terc_inf_val,   # x
                0,              # y
                r"$\mathbf{T\,1}$",
                ha='center',
                va='top',
                fontsize=9, 
                fontweight='bold'
            )

            # ---- Linha para terc_sup_val ----
            # vertical
            plt.plot(
                [terc_sup_val, terc_sup_val],
                [-0.05, y_sup],
                linestyle='--',
                color='black',
                linewidth=1
            )

            # horizontal até eixo Y
            plt.plot(
                [-0.05, terc_sup_val],
                [y_sup, y_sup],
                linestyle='--',
                color='black',
                linewidth=1
            )

            plt.text(
                terc_sup_val,
                0,
                r"$\mathbf{T\,2}$",
                ha='center',
                va='top',
                fontsize=9, 
                fontweight='bold'
            )

            # ============================
            # Título e eixos
            # ============================
            plt.xlabel("Precipitation (mm)", fontsize=15)
            plt.ylabel("Cumulative Probability" if curvetype=="cdf" else "Exceedance Probability", fontsize=15)

            plt.xlim(0, np.max(obs_sorted) + 200)
            plt.ylim(-0.05, 1.05)
            plt.grid(False)

            # Legenda fixa
            if curvetype == "cdf":
                leg = plt.legend(loc='upper left', fontsize=9)
            else:
                leg = plt.legend(loc='upper right', fontsize=9)

            leg.get_frame().set_facecolor('white')
            leg.get_frame().set_alpha(1)

            ax = plt.gca()

            for spine in ax.spines.values():
                spine.set_linewidth(1.5)            

            # if curvetype == "cdf":

            #         # # ===== LEFT (estatísticas) =====
            #         # text_left = (
            #         #     r"$\bf{Forecast\ (x)}$" + "\n"
            #         #     f"stdvₓ = {fcst_std[ilat,ilon]:.1f}mm\n"
            #         #     f"meanₓ = {fcst_mean[ilat,ilon]:.1f}mm\n\n"
            #         #     r"$\bf{Observation\ (y)}$" + "\n"
            #         #     f"stdvᵧ = {obs_std[ilat,ilon]:.1f}mm\n"
            #         #     f"meanᵧ = {obs_mean[ilat,ilon]:.1f}mm\n\n"
            #         #     f"anomaly = {fcst_mean[ilat,ilon] - obs_mean[ilat,ilon]:.1f}mm\n"
            #         #     f"r = {correlat[ilat,ilon]:.2f}"
            #         # )

            #         # ax.text(
            #         #     0.02, 0.7, text_left,
            #         #     transform=ax.transAxes,
            #         #     fontsize=8,
            #         #     va='top'
            #         # )

            #         # ===== RIGHT (probabilidades) =====
            #         text_right = (
            #             r"$\bf{Forecast\ (x)}$" + "\n"
            #             f"stdvₓ = {fcst_std[ilat,ilon]:.1f}mm\n"
            #             f"meanₓ = {fcst_mean[ilat,ilon]:.1f}mm\n\n"
            #             r"$\bf{Observation\ (y)}$" + "\n"
            #             f"stdvᵧ = {obs_std[ilat,ilon]:.1f}mm\n"
            #             f"meanᵧ = {obs_mean[ilat,ilon]:.1f}mm\n\n"
            #             f"anomaly = {fcst_mean[ilat,ilon] - obs_mean[ilat,ilon]:.1f}mm\n"
            #             f"r = {correlat[ilat,ilon]:.2f}\n\n"                    
            #             r"$\bf{Forecast}$" + "\n" +
            #             r"$\bf{Probabilities\ (p)}$" + "\n"
            #             f"P<(T1={terc_inf_val:.1f}) = {p_below_inf*100:.0f}%\n"
            #             f"P<(T2={terc_sup_val:.1f}) = {p_below_sup*100:.0f}%"
            #         )

            #         ax.text(
            #             0.98, 0.8, text_right,
            #             transform=ax.transAxes,
            #             fontsize=9,
            #             va='top',
            #             ha='right'
            #         )

            # else:  # ===== EXC =====

            #         # # ===== LEFT (probabilidades) =====
            #         # text_left = (
                        
            #         #     r"$\bf{Forecast}$" + "\n" +
            #         #     r"$\bf{Probabilities\ (p)}$" + "\n"
            #         #     f"P>(T1={terc_inf_val:.1f}) = {p_above_inf*100:.0f}%\n"
            #         #     f"P>(T2={terc_sup_val:.1f}) = {p_above_sup*100:.0f}%"
            #         # )

            #         # ax.text(
            #         #     0.02, 0.7, text_left,
            #         #     transform=ax.transAxes,
            #         #     fontsize=8,
            #         #     va='top'
            #         # )

            #         # ===== RIGHT (estatísticas) =====
            #         text_right = (
            #             r"$\bf{Forecast\ (x)}$" + "\n"
            #             f"stdvₓ = {fcst_std[ilat,ilon]:.1f}mm\n"
            #             f"meanₓ = {fcst_mean[ilat,ilon]:.1f}mm\n\n"
            #             r"$\bf{Observation\ (y)}$" + "\n"
            #             f"stdvᵧ = {obs_std[ilat,ilon]:.1f}mm\n"
            #             f"meanᵧ = {obs_mean[ilat,ilon]:.1f}mm\n\n"
            #             f"anomaly = {fcst_mean[ilat,ilon] - obs_mean[ilat,ilon]:.1f}mm\n"
            #             f"r = {correlat[ilat,ilon]:.2f}\n\n"                    
            #             r"$\bf{Forecast}$" + "\n" +
            #             r"$\bf{Probabilities\ (p)}$" + "\n"
            #             f"P<(T1={terc_inf_val:.1f}) = {p_below_inf*100:.0f}%\n"
            #             f"P<(T2={terc_sup_val:.1f}) = {p_below_sup*100:.0f}%"
            #         )

            #         ax.text(
            #             0.98, 0.8, text_right,
            #             transform=ax.transAxes,
            #             fontsize=9,
            #             va='top',
            #             ha='right'
            #         )

            plt.tight_layout()
            if ano == 2025:
                plt.savefig(f"{outdir}/curve_{curvetype}_gamma_2025020100_{nome}.png", dpi=150)
            else:
                plt.savefig(f"{outdir}/curve_{curvetype}_gamma_2016020100_{nome}.png", dpi=150)    
            plt.close()

    # for curvetype in curves_type:
    #     for nome, (ilat, ilon) in pontos.items():
    #         #EMPIRICA OBS
    #         obs_series = obs_total[:, ilat, ilon].values
    #         obs_series = obs_series[~np.isnan(obs_series)]
    #         obs_sorted = np.sort(obs_series)
    #         n = len(obs_sorted)
    #         # Probabilidade empírica acumulada (CDF)
    #         cdf_emp = np.arange(1, n+1) / (n+1)
    #         # Probabilidade de excedência
    #         exc_emp = 1 - cdf_emp

    #         lat_real = lat_obs[ilat]
    #         lon_real = lon360_to_180(lon_obs[ilon])   
    #         lat_str, lon_str = format_coord(lat_real, lon_real)

    #         # eixo x
    #         x = np.linspace(
    #             0.1,
    #             np.max(obs_total[:, ilat, ilon].values),
    #             500
    #         )

    #         # parâmetros Gamma
    #         a_obs  = obs_alpha[ilat, ilon]
    #         b_obs  = obs_beta[ilat, ilon]

    #         a_fcst = fcst_alpha[ilat, ilon]
    #         b_fcst = fcst_beta[ilat, ilon]

    #         # Curvas Gamma (excedência)
    #         if curvetype == "cdf":
    #             y_obs_gamma  = gamma.cdf(x, a=a_obs,  scale=b_obs)
    #             y_fcst_gamma = gamma.cdf(x, a=a_fcst, scale=b_fcst)
    #         else:
    #             y_obs_gamma  = 1 - gamma.cdf(x, a=a_obs,  scale=b_obs)
    #             y_fcst_gamma = 1 - gamma.cdf(x, a=a_fcst, scale=b_fcst)

    #         plt.figure(figsize=(6, 6))


    #         if curvetype == "exc":
    #             plt.plot(x, y_fcst_gamma, color="blue", linewidth=2,
    #                     label="Forecast EDF")
    #             plt.step(obs_sorted, exc_emp,
    #                     color="red",
    #                     linewidth=2,
    #                     where="post",
    #                     label="Climatological EDF")

    #         else:
    #             plt.plot(x, y_fcst_gamma, color="blue", linewidth=2,
    #                     label="Forecast CDF")                
    #             plt.step(obs_sorted, cdf_emp,
    #                     color="red",
    #                     linewidth=2,
    #                     where="post",
    #                     label="Climatological CDF")

    #         plt.plot(x, y_obs_gamma, color="red",  linewidth=2, linestyle="--",
    #                 label="Gamma Fit")

    #         if ano == 2025:
    #             plt.title(f"Precip. fcst. (Gamma) for MAM 2025 issued: Feb 2025, Lat:{lat_str} Lon:{lon_str}", 
    #                     fontsize=9, fontweight='bold')
    #         else:
    #             plt.title(f"Precip. fcst. (Gamma) for MAM 2025 issued: Feb 2025, Lat:{lat_str} Lon:{lon_str}", 
    #                     fontsize=9, fontweight='bold')

    #         plt.xlabel("Precipitation (mm)",fontsize=9)

    #         if curvetype == "cdf":
    #             plt.ylabel("Cumulative Probability",fontsize=9)
    #         else:
    #             plt.ylabel("Exceedance Probability",fontsize=9)     

    #         plt.ylim(-0.05, 1.05)
    #         plt.grid(False)

    #         if curvetype == "cdf":
    #             plt.legend(loc='upper left', fontsize=7)
    #         else:
    #             plt.legend(loc='upper right', fontsize=9)

    #         plt.tight_layout()
    #         if ano == 2025:
    #             plt.savefig(f"{outdir}/curve_{curvetype}_gamma_2025020100_{nome}.png", dpi=150)
    #         plt.close()

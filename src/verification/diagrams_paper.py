import os
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import datetime
import calendar
from src.config.config_models import ConfigModelos
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.calibration import calibration_curve
import matplotlib.patches as patches

# -------------------------
# Gerar o titulo das imagens 
# -------------------------
def get_titles(var: str, product: str, base: str, model: str, calib: str) -> tuple[str, str]:
    """
    Retorna (title1, title2) prontos para o gráfico.
    
    Args:
        var (str): 'prec' ou 't2mt'
        product (str): 'lowertercile', 'uppertercile' ou 'positiveanom'
        base (str): 'nmme' ou 'copernicus'
        calib (str): 'regr', 'cox' ou 'nocalib'
        
    Returns:
        tuple: (title1, title2)
    """
    # --- Mapas auxiliares ---
    var_names = {
        "prec": "PRECIPITATION",
        "t2mt": "2-METRE TEMPERATURE"
    }

    product_suffix = {
        "lowertercile": "IN LOWER TERCILE",
        "uppertercile": "IN UPPER TERCILE",
        "positiveanom": "POS. OR NEG. {var} ANOMALY"
    }

    base_years = {
        "nmme": "(1991 - 2020)",
        "copernicus": "(1993 - 2016)"
    }

    base_labels = {
        "nmme": "MULTIMODEL NMME + CPTEC",
        "copernicus": "MULTIMODEL CS3 + CPTEC"
    }

    if base == "nmme":
        models_labels = {
            "canesm5": "CanESM5 (NMME)",
            "ccsm4": "NCAR_CCSM4 (NMME)",
            "cesm1": "NCAR_CESM1 (NMME)",
            "cfsv2": "CFSv2 (NMME)",
            "gem52nemo": "GEM5.2_NEMO (NMME)",
            "geos5v2": "GEM5.NASA_GEOS5v2 (NMME)",
            "spear": "GFDL_SPEAR (NMME)",
            "bam12": "CPTEC_BAM1.2"
        }

    elif base == "copernicus":
        models_labels = {
            "ecmwf": "ECMWFs5.1 (C3S)",
            "ukmo": "UKMetOffice_s604 (C3S)",
            "meteo_france": "Météo-France_s9 (C3S)",
            "dwd": "DWD_s22 (C3S)",
            "cmcc": "CMCC_s4 (C3S)",
            "ncep": "NCEP_s2 (C3S)",
            "jma": "JMA_s3 (C3S)",
            "eccc4": "ECCC_s4 (C3S)",
            "eccc5": "ECCC_s5 (C3S)",
            "bom": "BOM_s2 (C3S)",
            "bam12": "CPTEC_BAM1.2"
        }
  
    calib_labels = {
        "regr": "Normal",
        "cox": "Cox",
        "gamma": "Gamma"
    }

    ref_labels = {
        "prec": "GPCP",
        "t2mt": "ERA5"
    }

    # --- Title2 ---
    if product == "positiveanom":
        title2 = f"{product_suffix[product].format(var=var_names[var])} {base_years[base]}"
    else:
        title2 = f"{var_names[var]} {product_suffix[product]} {base_years[base]}"

    # --- Title1 ---
    if model == "multimodel":
        title1 = f"{base_labels[base]} ({calib_labels[calib]}) REF:{ref_labels[var]}"
    else:
        title1 = f"{models_labels[model]} ({calib_labels[calib]}) REF:{ref_labels[var]}"
    return title1, title2

# -------------------------
# Gerar o nome dos períodos
# -------------------------
def generate_months_periods(data_verif: str):
    """
    Gera nomes de meses (4) e trimestres sazonais (3) 
    a partir de uma data de verificação no formato 'YYYYMMDD'.
    """
    # Converte string para datetime
    data_date = datetime.datetime.strptime(data_verif, "%Y%m%d")
    start_month = data_date.month

    # Meses individuais
    mnth_seq = [(start_month + i - 1) % 12 + 1 for i in range(4)]
    month_abbr_en = ["", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", 
                 "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    mnth_names = [month_abbr_en[m].upper() for m in mnth_seq]
    mnth_dict = {f"mnth0{i}": mnth_names[i] for i in range(4)}

    # Trimestres
    trimestres = {}
    for i in range(3):
        start = (start_month + i - 1) % 12 + 1
        months_vec = [(start + j - 1) % 12 + 1 for j in range(3)]
        # pega só a inicial de cada mês, maiúscula
        iniciais = "".join([calendar.month_abbr[m][0].upper() for m in months_vec])
        trimestres[f"seas0{i}"] = iniciais

    return {"mnth": mnth_dict, "seas": trimestres}

# -------------------------
# Função para extrair regiões
# -------------------------
def extract_region(var, lat_idx, lon_idx):
    """Recorta lat/lon em array numpy [lon, lat, time]."""
    return var[lon_idx[0]:lon_idx[1]+1, lat_idx[0]:lat_idx[1]+1, :]

# -------------------------
# Definições
# -------------------------
bases = ["nmme"]  # ou ["nmme",""]
calibs = ["regr","gamma","cox"]# ou ["regr","cox"]
periods_list = ["seas01"] #[f"mnth0{i}" for i in range(5)] + [f"seas0{i}" for i in range(3)]
data_verifs_nmme = ["20260201"]
data_verifs_copernicus = ["20250801", "20250901", "20251001", "20251101","20251201"]
models_nmme = ["multimodel"]#,"multimodel","canesm5","ccsm4", "cesm1", "cfsv2", "gem52nemo", "geos5v2", "spear", "bam12"]
varis = ["prec"] 
model = "multimodel"

# Grade
lat = np.arange(-88.75, 88.76, 2.5)
lon = np.arange(1.25, 358.76, 2.5)

# lat_mask = (lat <= 3.75) & (lat >= -18.75)
# lon_mask = (lon >= 311.25) & (lon <= 328.75)

# quit()

# Regiões (em índices da grade)
regions = {
    "as": {"lat": (13, 42), "lon": (109, 132)},
    #"as": {"lat": (5, 45), "lon": (103, 137)},
    #"neb": {"lat": (28, 38), "lon": (124, 132)},
}

#mask_neb = mask_da.sel(Y=slice(3, -19), X=slice(311, 329))

# -------------------------
# Loop principal
# -------------------------
for base in bases:

    if base == "nmme":
        models = models_nmme
        data_verifs = data_verifs_nmme
    elif base == "copernicus":
        models = models_copernicus
        data_verifs = data_verifs_copernicus

    for var in varis:
        for model in models:
            for data_verif in data_verifs:
                    for calib in calibs:
                        for period in periods_list:
                            if model == "multimodel":
                                name_model = "multimodel"
                            else:
                                name_model = model if base == "nmme" else ConfigModelos.get_model_dir(model)
                            periods_dict = generate_months_periods(data_verif)
                            # Nomes dos arquivos
                            if calib == "nocalib":
                                binobstsup_file = f"{var}_binobstsup_{period}_{name_model}_{calib}_{data_verif}00.nc"
                                binobstinf_file = f"{var}_binobstinf_{period}_{name_model}_{calib}_{data_verif}00.nc"
                                #binobsmed_file  = f"{var}_binobsmed_{period}_{name_model}_{calib}_{data_verif}00.nc"

                                probtsup_file = f"{var}_probtsup_{period}_{name_model}_{calib}_{data_verif}00.nc"
                                probtinf_file = f"{var}_probtinf_{period}_{name_model}_{calib}_{data_verif}00.nc"
                                #probmed_file  = f"{var}_probmed_{period}_{name_model}_{calib}_{data_verif}00.nc"
                            else:
                                binobstsup_file = f"{var}_binobstsup_{period}_{name_model}_calibrated_{calib}_{data_verif}00.nc"
                                binobstinf_file = f"{var}_binobstinf_{period}_{name_model}_calibrated_{calib}_{data_verif}00.nc"
                                binobsmed_file  = f"{var}_bionbsmean_{period}_{name_model}_calibrated_{calib}_{data_verif}00.nc"

                                probtsup_file = f"{var}_probtsup_{period}_{name_model}_calibrated_{calib}_{data_verif}00.nc"
                                probtinf_file = f"{var}_probtinf_{period}_{name_model}_calibrated_{calib}_{data_verif}00.nc"
                                probmed_file  = f"{var}_probmean_{period}_{name_model}_calibrated_{calib}_{data_verif}00.nc"

                            # Caminho dos dados
                            if base == "nmme":
                                path_data = f"/dados/mmclima/multimodelo/artigo/dados/"
                                pathfig = f"/dados/mmclima/multimodelo/seasonal/figures/artigo/"
                            else: 
                                path_data = f"/dados/mmclima/multimodelo/artigo/dados/"
                                pathfig = f"/dados/mmclima/multimodelo/seasonal/figures/artigo/"

                            os.makedirs(pathfig, exist_ok=True)

                            #Abrir máscara
                            mask = xr.open_dataset("/dados/mmclima/multimodelo/artigo/dados/landmask_interp.nc")
                            mask_land = mask["land"]

                            # Abrir arquivos NetCDF
                            binobstsup = xr.open_dataset(os.path.join(path_data, binobstsup_file))["binobstsup"]
                            binobstinf = xr.open_dataset(os.path.join(path_data, binobstinf_file))["binobstinf"]
                            binobsmed  = xr.open_dataset(os.path.join(path_data, binobsmed_file))["bionbsmean"]

                            probtsup = xr.open_dataset(os.path.join(path_data, probtsup_file))["probtsup"]
                            probtinf = xr.open_dataset(os.path.join(path_data, probtinf_file))["probtinf"]
                            probmed  = xr.open_dataset(os.path.join(path_data, probmed_file))["probmean"]

                            # # #Aplicar a máscara
                            # binobstsup = binobstsup.where(mask_land == 1)
                            # binobstinf = binobstinf.where(mask_land == 1)

                            # probtsup = probtsup.where(mask_land == 1)
                            # probtinf = probtinf.where(mask_land == 1)

                            # Loop regiões
                            for region_name, coords in regions.items():
                                lat_start, lat_end = coords["lat"]
                                lon_start, lon_end = coords["lon"]
                                
                                # Loop tipos
                                #for product in ["positiveanom"]:       
                                for product in ["lowertercile", "uppertercile","positiveanom"]:                                                                 
                                    if product == "lowertercile":
                                        binobs_data = binobstinf.values
                                        prob_data   = probtinf.values
                                    elif product == "uppertercile":
                                        binobs_data = binobstsup.values
                                        prob_data   = probtsup.values
                                    elif product == "positiveanom":
                                        binobs_data = binobsmed.values
                                        prob_data   = probmed.values

                                    prob_data = prob_data
                                    # print(binobs_data.shape)
                                    # print(prob_data.shape)
                                    
                                    # Seleciona apenas a região usando slicing
                                    binobs_region = binobs_data[:, lat_start:lat_end+1, lon_start:lon_end+1]
                                    prob_region   = prob_data[:, lat_start:lat_end+1, lon_start:lon_end+1]

                                    obs = binobs_region.ravel().astype(int)
                                    prob = prob_region.ravel()  

                                    # Remove NaNs
                                    mask = ~np.isnan(obs) & ~np.isnan(prob)
                                    obs = obs[mask]
                                    prob = prob[mask]

                                    month_issued = periods_dict['mnth']['mnth00']

                                    if period.startswith('mnth'):
                                        if period == "mnth00":
                                            fcst_period = periods_dict['mnth']['mnth00']
                                        elif period == "mnth01":
                                            fcst_period = periods_dict['mnth']['mnth01']           
                                        elif period == "mnth02":
                                            fcst_period = periods_dict['mnth']['mnth02']   
                                        elif period == "mnth03":
                                            fcst_period = periods_dict['mnth']['mnth03']                                                  
                                    elif period.startswith('seas'):
                                        if period == "seas00":
                                            fcst_period = periods_dict['seas']['seas00']
                                        if period == "seas01":
                                            fcst_period = periods_dict['seas']['seas01']         
                                        if period == "seas02":
                                            fcst_period = periods_dict['seas']['seas02']   

                                    title1, title2 = get_titles(var, product, base, model, calib)

                                    # ----------------------------------------------------------
                                    # RELIABILITY DIAGRAM (ARTIGO - SEM INSET)
                                    # ----------------------------------------------------------

                                    nbins = 10
                                    nboot = 1000

                                    bins = np.linspace(0, 1, nbins + 1)
                                    bin_centers = (bins[:-1] + bins[1:]) / 2

                                    # Histogramas
                                    counts, _ = np.histogram(prob, bins=bins)
                                    hits, _   = np.histogram(prob[obs == 1], bins=bins)

                                    with np.errstate(divide='ignore', invalid='ignore'):
                                        observed_freq = hits / counts

                                    obar = np.nanmean(obs)
                                    n = len(prob)

                                    # ----------------------------------------------------------
                                    # BOOTSTRAP
                                    # ----------------------------------------------------------

                                    obariboot = np.full((nboot, nbins), np.nan)

                                    #rng = np.random.default_rng(42)
                                    rng = np.random.default_rng(1)
                                    for i in range(nboot):

                                        idx = rng.choice(np.arange(n), size=n, replace=True)

                                        pf = prob[idx]
                                        bo = obs[idx]

                                        hb, _ = np.histogram(pf, bins=bins)
                                        gb, _ = np.histogram(pf[bo == 1], bins=bins)

                                        # with np.errstate(divide='ignore', invalid='ignore'):
                                        #     ob = gb.astype(float) / hb.astype(float)

                                        # obariboot[i, :] = ob
                                        
                                        ob = np.full(nbins, np.nan)

                                        valid = hb >= 5   # <<< REGRA ESTATÍSTICA PADRÃO

                                        ob[valid] = gb[valid] / hb[valid]

                                        obariboot[i, :] = ob                                        

                                    low = np.nanquantile(obariboot, 0.025, axis=0)
                                    upp = np.nanquantile(obariboot, 0.975, axis=0)

                                    # ----------------------------------------------------------
                                    # BRIER SCORE DECOMPOSITION
                                    # ----------------------------------------------------------

                                    obs_for_bs = np.nan_to_num(observed_freq)

                                    with np.errstate(invalid='ignore'):
                                        reliab = np.nansum(counts * (bin_centers - obs_for_bs) ** 2) / n
                                        resol  = np.nansum(counts * (obs_for_bs - obar) ** 2) / n

                                    uncert = obar * (1 - obar)
                                    bs = reliab - resol + uncert

                                    # ----------------------------------------------------------
                                    # PLOT
                                    # ----------------------------------------------------------

                                    fig, ax = plt.subplots(figsize=(8, 8))

                                    # Moldura grossa (estilo artigo)
                                    for spine in ax.spines.values():
                                        spine.set_linewidth(3)

                                    # ----------------------------------------------------------
                                    # Curva confiabilidade
                                    # ----------------------------------------------------------

                                    mask = ~np.isnan(observed_freq)

                                    ax.plot(
                                        bin_centers[mask] * 100,
                                        observed_freq[mask] * 100,
                                        "-o",
                                        color="black",
                                        linewidth=3,
                                        markersize=8,
                                        zorder=6
                                    )

                                    # ----------------------------------------------------------
                                    # Bootstrap intervals (barras verticais)
                                    # ----------------------------------------------------------

                                    for i in range(nbins):

                                        if np.isnan(low[i]) or np.isnan(upp[i]):
                                            continue

                                        x = bin_centers[i] * 100
                                        y1 = low[i] * 100
                                        y2 = upp[i] * 100

                                        ax.plot([x, x], [y1, y2],
                                                color="black",
                                                linewidth=3,
                                                zorder=7)

                                    # ----------------------------------------------------------
                                    # Linha perfeita + climatologia
                                    # ----------------------------------------------------------

                                    ax.plot([-5, 105], [-5, 105], color="black", linewidth=1.5)
                                    ax.axhline(obar * 100, color="black", linestyle="-", linewidth=1.5)

                                    # ----------------------------------------------------------
                                    # Barras cinzas arredondadas (frequência normalizada)
                                    # ----------------------------------------------------------

                                    counts_norm = counts / np.sum(counts)

                                    bar_width = 50 / nbins   # largura em %

                                    for x, h in zip(bin_centers * 100, counts_norm * 100):

                                        # arredondamento proporcional à altura
                                        rounding = min(2, h / 2)

                                        bar = patches.FancyBboxPatch(
                                            (x - bar_width/2, 0),
                                            bar_width,
                                            h,
                                            boxstyle=f"round,pad=0,rounding_size={rounding}",
                                            linewidth=0,
                                            facecolor="#333333",
                                            alpha=0.5,
                                            zorder=1
                                        )

                                        ax.add_patch(bar)
                                    # ----------------------------------------------------------
                                    # Texto métricas
                                    # ----------------------------------------------------------

                                    textstr = (
                                        f"Rel = {reliab:.3f}\n"
                                        f"Res = {resol:.3f}\n"
                                        f"Unc = {uncert:.3f}\n"
                                        f"BS = {bs:.3f}"                                        
                                    )

                                    ax.text(
                                        0.04,
                                        0.95,
                                        textstr,
                                        transform=ax.transAxes,
                                        fontsize=18,
                                        verticalalignment="top",
                                        linespacing=1.6   # <<< AUMENTA ESPAÇAMENTO ENTRE LINHAS
                                        #bbox=dict(boxstyle="round", facecolor="white", alpha=0.8)
                                    )

                                    # ----------------------------------------------------------
                                    # Eixos
                                    # ----------------------------------------------------------

                                    ax.set_xlim(-3, 105)
                                    ax.set_ylim(-3, 105)

                                    ax.set_xlabel("FORECAST PROBABILITY (%)", fontsize=22)
                                    ax.set_ylabel("OBSERVED RELATIVE FREQUENCY (%)", fontsize=22)

                                    ax.tick_params(axis="both", labelsize=18)

                                    ax.grid(False)

                                    # ----------------------------------------------------------
                                    # TÍTULO
                                    # ----------------------------------------------------------

                                    if calib == "gamma":
                                        name_calib = "Gamma"
                                    elif calib == "regr":
                                        name_calib = "Normal"       
                                    elif calib == "cox":
                                        name_calib = "Cox"

                                    if product == "lowertercile":
                                        title2 = "Event: precip. in lower tercile (below normal):"
                                    elif product == "uppertercile":
                                        title2 = "Event: precip. in upper tercile (above normal):"
                                    elif product == "positiveanom":
                                        title2 = "Event: pos. or neg. precipitation anomaly:"

                                    if calib == "regr" and product == "lowertercile":
                                        ax.set_title(
                                        f"a) Reliability Diagram: Calibrated Multi-Model: GPCP (1991–2020)\n"
                                        f"{title2} {name_calib}\n"
                                        "Issued: Feb  Valid for MAM",
                                        fontsize=25
                                        )     

                                    elif calib == "regr" and product == "uppertercile":
                                        ax.set_title(
                                        f"b) Reliability Diagram: Calibrated Multi-Model: GPCP (1991–2020)\n"
                                        f"{title2} {name_calib}\n"
                                        "Issued: Feb  Valid for MAM",
                                        fontsize=25
                                        )        

                                    elif calib == "regr" and product == "positiveanom":
                                        ax.set_title(
                                        f"a) Reliability Diagram: Calibrated Multi-Model: GPCP (1991–2020)\n"
                                        f"{title2} {name_calib}\n"
                                        "Issued: Feb  Valid for MAM",
                                        fontsize=25
                                        )       

                                    if calib == "gamma" and product == "lowertercile":
                                        ax.set_title(
                                        f"c) Reliability Diagram: Calibrated Multi-Model: GPCP (1991–2020)\n"
                                        f"{title2} {name_calib}\n"
                                        "Issued: Feb  Valid for MAM",
                                        fontsize=25
                                        )     

                                    elif calib == "gamma" and product == "uppertercile":
                                        ax.set_title(
                                        f"d) Reliability Diagram: Calibrated Multi-Model: GPCP (1991–2020)\n"
                                        f"{title2} {name_calib}\n"
                                        "Issued: Feb  Valid for MAM",
                                        fontsize=25

                                        )  
                                    elif calib == "gamma" and product == "positiveanom":
                                        ax.set_title(
                                        f"b) Reliability Diagram: Calibrated Multi-Model: GPCP (1991–2020)\n"
                                        f"{title2} {name_calib}\n"
                                        "Issued: Feb  Valid for MAM",
                                        fontsize=25
                                        )                                              

                                    if calib == "cox" and product == "lowertercile":
                                        ax.set_title(
                                        f"e) Reliability Diagram: Calibrated Multi-Model: GPCP (1991–2020)\n"
                                        f"{title2} {name_calib}\n"
                                        "Issued: Feb  Valid for MAM",
                                        fontsize=25
                                        )     

                                    elif calib == "cox" and product == "uppertercile":
                                        ax.set_title(
                                        f"f) Reliability Diagram: Calibrated Multi-Model: GPCP (1991–2020)\n"
                                        f"{title2} {name_calib}\n"
                                        "Issued: Feb  Valid for MAM",
                                        fontsize=25
                                        )    

                                    elif calib == "cox" and product == "positiveanom":
                                        ax.set_title(
                                        f"c) Reliability Diagram: Calibrated Multi-Model: GPCP (1991–2020)\n"
                                        f"{title2} {name_calib}\n"
                                        "Issued: Feb  Valid for MAM",
                                        fontsize=25
                                        )    

                                    #plt.tight_layout()
                                    plt.subplots_adjust(bottom=0.12)
                                    if base == "nmme":
                                        out_rel = f"{pathfig}{base}_{name_model}_{calib}_reliabilitydiagram_{product}_{var}_{period}_{month_issued}_{region_name}.png"
                                    if base == "copernicus":
                                        out_rel = f"{pathfig}c3s_{name_model}_{calib}_reliabilitydiagram_{product}_{var}_{period}_{month_issued}_{region_name}.png"
                                    plt.savefig(out_rel, dpi=120, bbox_inches="tight", pad_inches=0.25)
                                    plt.close()
                                    print("RELIABILITY salvo:", out_rel)


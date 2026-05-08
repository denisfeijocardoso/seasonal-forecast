import os
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import datetime
import calendar
from src.config.config_models_seasonal import ConfigModelos
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
        "regr": "REGR.",
        "cox": "COX",
        "nocalib": " "
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
        if calib == "nocalib":
            title1 = f"{base_labels[base]} REF:{ref_labels[var]}"
        else:
            title1 = f"{base_labels[base]} ({calib_labels[calib]}) REF:{ref_labels[var]}"                
    else:
        if calib == "nocalib":
            title1 = f"{models_labels[model]} REF:{ref_labels[var]}"
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
calibs = ["nocalib"]# ou ["regr","cox"]
periods_list = [f"mnth0{i}" for i in range(5)] + [f"seas0{i}" for i in range(3)] #[f"mnth0{i}" for i in range(5)] + [f"seas0{i}" for i in range(3)]
#data_verifs_nmme = ["20250201"]
data_verifs_nmme = ["20250101", "20250201", "20250301", "20250401", "20250501", "20250601", "20250701", "20250801", "20250901", "20251001", "20251101","20251201"]
data_verifs_copernicus = ["20250101", "20250201", "20250301", "20250401", "20250501", "20250601", "20250701", "20250801", "20250901", "20251001", "20251101","20251201"]
models_nmme = ["multimodel","canesm5","ccsm4", "cesm1", "cfsv2", "gem52nemo", "geos5v2", "spear", "bam12"]#,"multimodel","canesm5","ccsm4", "cesm1", "cfsv2", "gem52nemo", "geos5v2", "spear", "bam12"]
models_copernicus = ["multimodel","ecmwf","ukmo","meteo_france","dwd","cmcc","ncep","jma","eccc4","eccc5","bom","bam12"] 
varis = ["prec","t2mt"] 
model = "multimodel"

# Grade
lat = np.arange(-88.75, 88.76, 2.5)
lon = np.arange(1.25, 358.76, 2.5)

# Regiões (em índices da grade)
regions = {
    "gl": {"lat": (9, 64), "lon": (1, 144)},
    "af": {"lat": (21, 52), "lon": (24, 132)},
    "aa": {"lat": (33, 68), "lon": (27, 72)},
    "au": {"lat": (17, 46), "lon": (45, 76)},
    "eu": {"lat": (49, 68), "lon": (24, 132)},
    "an": {"lat": (33, 64), "lon": (77, 124)},
    "pa": {"lat": (25, 48), "lon": (42, 114)},
    "as": {"lat": (13, 42), "lon": (109, 132)},
    "ne": {"lat": (45, 68), "lon": (1, 144)},
    "se": {"lat": (5, 29), "lon": (1, 144)},
    "tr": {"lat": (29, 44), "lon": (1, 144)},
    "am": {"lat": (28, 39), "lon": (112, 125)}
}

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
                            version = ConfigModelos.get_model_version(model)
                            periods_dict = generate_months_periods(data_verif)
                            # Nomes dos arquivos
                            if calib == "nocalib":
                                binobstsup_file = f"{var}_binobstsup_{period}_{name_model}_{calib}_{data_verif}00.nc"
                                binobstinf_file = f"{var}_binobstinf_{period}_{name_model}_{calib}_{data_verif}00.nc"
                                binobsmed_file  = f"{var}_binobsmed_{period}_{name_model}_{calib}_{data_verif}00.nc"

                                probtsup_file = f"{var}_probtsup_{period}_{name_model}_{calib}_{data_verif}00.nc"
                                probtinf_file = f"{var}_probtinf_{period}_{name_model}_{calib}_{data_verif}00.nc"
                                probmed_file  = f"{var}_probmed_{period}_{name_model}_{calib}_{data_verif}00.nc"
                            else:
                                binobstsup_file = f"{var}_binobstsup_{period}_{name_model}_calibrated_{calib}_{data_verif}00.nc"
                                binobstinf_file = f"{var}_binobstinf_{period}_{name_model}_calibrated_{calib}_{data_verif}00.nc"
                                binobsmed_file  = f"{var}_binobsmed_{period}_{name_model}_calibrated_{calib}_{data_verif}00.nc"

                                probtsup_file = f"{var}_probtsup_{period}_{name_model}_calibrated_{calib}_{data_verif}00.nc"
                                probtinf_file = f"{var}_probtinf_{period}_{name_model}_calibrated_{calib}_{data_verif}00.nc"
                                probmed_file  = f"{var}_probmed_{period}_{name_model}_calibrated_{calib}_{data_verif}00.nc"
        
                            # Caminho dos dados
                            if base == "nmme":
                                path_data = f"/dados/mmclima/multimodelo/seasonal/posproc/nmme/v1/verification/{calib}/{name_model}/"
                                pathfig = f"/dados/mmclima/multimodelo/seasonal/figures/{base}/v1/verification/{calib}/{name_model}/"
                            else:
                                path_data = f"/dados/mmclima/multimodelo/seasonal/posproc/copernicus/v2/verification/{calib}/{name_model}/"
                                pathfig = f"/dados/mmclima/multimodelo/seasonal/figures/{base}/v2/verification/{calib}/{name_model}/"

                            os.makedirs(pathfig, exist_ok=True)

                            # Abrir arquivos NetCDF
                            binobstsup = xr.open_dataset(os.path.join(path_data, binobstsup_file))["binobstsup"].values
                            binobstinf = xr.open_dataset(os.path.join(path_data, binobstinf_file))["binobstinf"].values
                            binobsmed  = xr.open_dataset(os.path.join(path_data, binobsmed_file))["binobsmed"].values

                            probtsup = xr.open_dataset(os.path.join(path_data, probtsup_file))["probtsup"].values
                            probtinf = xr.open_dataset(os.path.join(path_data, probtinf_file))["probtinf"].values
                            probmed  = xr.open_dataset(os.path.join(path_data, probmed_file))["probmed"].values

                            # Loop regiões
                            for region_name, coords in regions.items():
                                lat_start, lat_end = coords["lat"]
                                lon_start, lon_end = coords["lon"]
                                
                                # Loop tipos
                                #for product in ["positiveanom"]:       
                                for product in ["lowertercile", "uppertercile", "positiveanom"]:                                                                 
                                    if product == "lowertercile":
                                        binobs_data = binobstinf
                                        prob_data   = probtinf
                                    elif product == "uppertercile":
                                        binobs_data = binobstsup
                                        prob_data   = probtsup
                                    elif product == "positiveanom":
                                        binobs_data = binobsmed
                                        prob_data   = probmed   

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

                                    # -------------------------
                                    # ROC diagram
                                    # -------------------------
                                    roc_auc = roc_auc_score(obs, prob)
                                    fpr, tpr, _ = roc_curve(obs, prob)
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

                                    # plot
                                    plt.figure(figsize=(4,4))
                                    plt.plot(fpr, tpr, color='black', lw=1.5)
                                    plt.plot([-0.08,1.08], [-0.08,1.08], color='grey', lw=1)
                                    plt.xlim([-0.08,1.08])
                                    plt.ylim([-0.08,1.08])
                                    plt.xlabel("FALSE ALARM RATE", fontsize=8)
                                    plt.ylabel("HIT RATE", fontsize=8)
                                    title1, title2 = get_titles(var, product, base, model, calib)
                                    plt.title(f"{title1}"
                                                f"\n{title2}\n"
                                                f"ISSUED: {month_issued} VALID FOR {fcst_period}", fontsize=9)
                                    print(month_issued)
                                    plt.text(0.5, 0.2, f"ROC AREA = {roc_auc:.2f}", fontsize=8)
                                    plt.grid(False)
                                    # salvar
                                    if base == "nmme":
                                        figfile = f"{pathfig}{base}_{name_model}_{calib}_rocdiagram_{product}_{var}_{period}_{month_issued}_{region_name}.png"
                                    elif base == "copernicus":
                                        figfile = f"{pathfig}c3s_{name_model}_{calib}_rocdiagram_{product}_{var}_{period}_{month_issued}_{region_name}.png"

                                    plt.savefig(figfile, dpi=120, bbox_inches="tight")
                                    plt.close()
                                    print("ROC salvo:", figfile)

                                    # -------------------------
                                    # Reliability diagram
                                    # -------------------------
                                    # prob e obs já definidos

                                    prob = np.clip(prob, 0, 1)

                                    prob_true, prob_pred = calibration_curve(obs, prob, n_bins=10)

                                    plt.figure(figsize=(4, 4))

                                    # --- Barras cinza (número de ocorrências por bin, arredondadas) ---
                                    if calib == "cox" and product == "positiveanom":
                                        bin_counts, _ = np.histogram(1 - prob, bins=np.linspace(0, 1, 11))
                                    else:
                                        bin_counts, _ = np.histogram(prob, bins=np.linspace(0, 1, 11))
                                    bin_width = 0.0008

                                    ax = plt.gca()
                                    for x, h in zip(prob_pred, bin_counts / bin_counts.sum()):
                                        bar = patches.FancyBboxPatch(
                                            (x - bin_width/2, 0),   # canto inferior esquerdo
                                            bin_width,              # largura
                                            h,                      # altura
                                            boxstyle="round,pad=0.02,rounding_size=0.015",  # arredondado
                                            linewidth=0,
                                            facecolor="gray",
                                            alpha=0.6
                                        )
                                        ax.add_patch(bar)

                                    # --- Curva de confiabilidade ---
                                    plt.plot(prob_pred, prob_true, color="black", linewidth=2)

                                    # --- Linha da confiabilidade perfeita ---
                                    plt.plot([-0.03, 1.03], [-0.03, 1.03], color="black", linestyle="-", linewidth=1)

                                    # --- Eixos e títulos ---
                                    plt.xlabel("FORECAST PROBABILITY", fontsize=8)
                                    plt.ylabel("OBSERVED RELATIVE FREQUENCY", fontsize=8)

                                    plt.title(
                                        f"RELIABILITY DIAGRAM: {title1}\n"
                                        f"{title2}\n"
                                        f"ISSUED: {month_issued}  VALID FOR {fcst_period}",  fontsize=9
                                    )

                                    # Ajustes finais
                                    plt.xlim(-0.03, 1.03)
                                    plt.ylim(-0.03, 1.03)
                                    plt.grid(False)
                                    plt.tight_layout()

                                    if base == "nmme":
                                        out_rel = f"{pathfig}{base}_{name_model}_{calib}_reliabilitydiagram_{product}_{var}_{period}_{month_issued}_{region_name}.png"
                                    if base == "copernicus":
                                        out_rel = f"{pathfig}c3s_{name_model}_{calib}_reliabilitydiagram_{product}_{var}_{period}_{month_issued}_{region_name}.png"
                                    plt.savefig(out_rel, dpi=120, bbox_inches="tight")
                                    plt.close()
                                    print("RELIABILITY salvo:", out_rel)

import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap
import matplotlib.patches as mpatches
import cartopy.io.shapereader as shpreader
import cartopy.feature as cfeature
import cartopy.crs as ccrs
from matplotlib.path import Path
from matplotlib.patches import PathPatch
import cartopy.crs as ccrs
import geopandas as gpd
from matplotlib.patches import Rectangle
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize

def add_dstk_mask_cartopy(ax, geom, color="white", zorder=5):

    # Limites atuais do mapa
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()

    # ---------------------------
    # Retângulo do domínio
    # ---------------------------

    rect_vertices = [
        (x0, y0),
        (x1, y0),
        (x1, y1),
        (x0, y1),
        (x0, y0)
    ]

    rect_codes = [
        Path.MOVETO,
        Path.LINETO,
        Path.LINETO,
        Path.LINETO,
        Path.CLOSEPOLY
    ]

    vertices = rect_vertices.copy()
    codes = rect_codes.copy()

    # ---------------------------
    # Polígonos da América do Sul
    # ---------------------------

    if geom.geom_type == "MultiPolygon":
        polys = geom.geoms
    else:
        polys = [geom]

    for poly in polys:
        x, y = poly.exterior.coords.xy
        poly_vertices = list(zip(x, y))

        poly_codes = [Path.MOVETO] + [Path.LINETO] * (len(poly_vertices) - 2) + [Path.CLOSEPOLY]

        vertices += poly_vertices
        codes += poly_codes

    # ---------------------------
    # Path final
    # ---------------------------

    path = Path(vertices, codes)

    patch = PathPatch(
        path,
        facecolor=color,
        edgecolor="none",
        transform=ccrs.PlateCarree(),
        zorder=zorder
    )

    ax.add_patch(patch)


def setup_map_sam(ax):

    lat_south = -60
    lat_north = 15
    lon_west = -90
    lon_east = -30

    # =========================
    # REGIÃO
    # =========================
    ax.set_extent(
        [lon_west, lon_east, lat_south, lat_north],
        crs=ccrs.PlateCarree()
    )

    # =========================
    # COSTA E FRONTEIRAS
    # =========================
    ax.coastlines(resolution="10m", linewidth=1.2, zorder=10)

    ax.add_feature(
        cfeature.BORDERS.with_scale("10m"),
        linewidth=1.2,
        edgecolor="black"
    )

    # =========================
    # ESTADOS DO BRASIL
    # =========================
    shp_estados = "/scripts/clima/denis/sazonal/src/maps/BR_UF_2022/BR_UF_2022.shp"

    reader = shpreader.Reader(shp_estados)

    ax.add_geometries(
        reader.geometries(),
        crs=ccrs.PlateCarree(),
        facecolor="none",
        edgecolor="black",
        linewidth=1.2
    )

    # =========================
    # PARALELOS / MERIDIANOS
    # =========================
    parallels = [-60, -55, -50, -45, -40, -35, -30, -25,
                 -20, -15, -10, -5, 0, 5, 10, 15]

    meridians = [-90, -80, -70, -60, -50, -40, -30]

    ax.set_yticks(parallels, crs=ccrs.PlateCarree())
    ax.set_yticklabels(
        ["60°S","55°S","50°S","45°S","40°S","35°S","30°S","25°S",
         "20°S","15°S","10°S","5°S","EQ","5°N","10°N","15°N"],
        fontsize=14
    )

    ax.set_xticks(meridians, crs=ccrs.PlateCarree())
    ax.set_xticklabels(
        ["90°W","80°W","70°W","60°W","50°W","40°W","30°W"],
        fontsize=14
    )

    # ==================================================
    # SHAPE AMÉRICA DO SUL — NATURAL EARTH
    # ==================================================

    shp_sa = shpreader.natural_earth(
        resolution="10m",
        category="cultural",
        name="admin_0_countries"
    )

    gdf = gpd.read_file(shp_sa).to_crs("EPSG:4326")

    sa_countries = [
        "Brazil", "Argentina", "Uruguay", "Paraguay",
        "Bolivia", "Peru", "Chile", "Colombia",
        "Venezuela", "Guyana", "Suriname", "Ecuador",
        "French Guiana", "France"
    ]

    gdf_sa = gdf[gdf["ADMIN"].isin(sa_countries)]

    geom_sa = gdf_sa.unary_union

    # ==================================================
    # DSTK MASK — OCEANO BRANCO
    # ==================================================

    add_dstk_mask_cartopy(
        ax,
        geom_sa,
        color="white",
        zorder=5
    )


# =====================================================
# INPUT
# =====================================================

year = 2025
month = 2

base_path = "/dados/mmclima/multimodelo/artigo/dados"

file_anom = f"{base_path}/GPCP_trimestral_anom_{year}{month:02d}.nc"
file_terc = f"{base_path}/GPCP_trimestral_tercile_{year}{month:02d}.nc"

file_pksobs = "/dados/mmclima/multimodelo/sazonal/posproc/nmme/v1/forecast/gamma/multimodel/2025/2025020100/fcst_prec_pksobs_seas02_multimodel_calibrated_gamma_2025020100.nc"
file_pkshcst = "/dados/mmclima/multimodelo/sazonal/posproc/nmme/v1/forecast/gamma/multimodel/2025/2025020100/fcst_prec_pkshcst_seas02_multimodel_calibrated_gamma_2025020100.nc"

var_anom = "precip_anomaly"
var_terc = "tercile_class"
var_pksobs = "pksobs"
var_pkshcst = "pkshcst"

# =====================================================
# ABRE OS DADOS
# =====================================================

da_anom = xr.open_dataset(file_anom)[var_anom]
da_terc = xr.open_dataset(file_terc)[var_terc]
da_pksobs = xr.open_dataset(file_pksobs)[var_pksobs]
da_pkshcst = xr.open_dataset(file_pkshcst)[var_pkshcst]

# =====================================================
# CONVERSÃO LONGITUDE (0–360 → -180–180)
# =====================================================

def convert_lon(da):
    if da.lon.max() > 180:
        da = da.assign_coords(
            lon=((da.lon + 180) % 360) - 180
        )
        da = da.sortby("lon")
    return da

da_anom = convert_lon(da_anom)
da_terc = convert_lon(da_terc)
da_pksobs = convert_lon(da_pksobs)
da_pkshcst = convert_lon(da_pkshcst)

# =====================================================
# RECORTE AMÉRICA DO SUL
# =====================================================

lon_min, lon_max = -90, -30
lat_min, lat_max = -60, 15

da_anom = da_anom.sel(
    lon=slice(lon_min, lon_max),
    lat=slice(lat_min, lat_max)
)

da_terc = da_terc.sel(
    lon=slice(lon_min, lon_max),
    lat=slice(lat_min, lat_max)
)

da_pksobs = da_pksobs.sel(
    lon=slice(lon_min, lon_max),
    lat=slice(lat_min, lat_max)
)

da_pkshcst = da_pkshcst.sel(
    lon=slice(lon_min, lon_max),
    lat=slice(lat_min, lat_max)
)

da_sig_obs  = xr.where(da_pksobs  < 0.05, -1, 1)
da_sig_hcst = xr.where(da_pkshcst < 0.05, -1, 1)

# =====================================================
# MAPAS SIGNIFICÂNCIA KS (p < 0.05)
# =====================================================

# 1) Criar máscaras binárias
da_sig_obs  = xr.where(da_pksobs  < 0.05, -1, 1)
da_sig_hcst = xr.where(da_pkshcst < 0.05, -1, 1)

# 2) Colormap (sem branco)
cmap_sig = ListedColormap(["red", "blue"])
bounds = [-1.5, 0, 1.5]
norm_sig = BoundaryNorm(bounds, cmap_sig.N)

# 3) Função para plotar
def plot_pks_map(data_array, title, outfile):

    fig = plt.figure(figsize=(5,8))
    ax = fig.add_axes([0,0.01,1,0.83], projection=ccrs.PlateCarree())

    setup_map_sam(ax)
    ax.set_extent([lon_min, lon_max, lat_min, lat_max])

    ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5)

    img = ax.pcolormesh(
        data_array.lon,
        data_array.lat,
        data_array,
        cmap=cmap_sig,
        norm=norm_sig,
        transform=ccrs.PlateCarree()
    )

    legend_elements = [
        mpatches.Patch(facecolor="red",  edgecolor="black", label="p < 0.05"),
        mpatches.Patch(facecolor="blue", edgecolor="black", label="p ≥ 0.05")
    ]

    leg = ax.legend(
        handles=legend_elements,
        loc="lower right",
        frameon=True,
        fontsize=13
    )

    leg.get_frame().set_facecolor("white")
    leg.get_frame().set_alpha(1.0)
    leg.get_frame().set_edgecolor("black")
    leg.set_zorder(100)

    plt.title(title, fontsize=14)

    # Moldura manual
    ax.set_frame_on(False)
    rect = Rectangle(
        (0, 0), 1, 1,
        transform=ax.transAxes,
        fill=False,
        linewidth=2.5,
        edgecolor="black",
        zorder=1000
    )
    ax.add_patch(rect)

    plt.savefig(outfile, dpi=300, bbox_inches='tight', pad_inches=0)
    plt.close()

    print("Mapa salvo:", outfile)


# 4) Gerar mapas OBS e HCST

plot_pks_map(
    da_sig_obs,
    "a) Kolmogorov-Smirnov Test (Obs. GPCP 1991–2020)",
    "/dados/mmclima/multimodelo/sazonal/figures/artigo/PKS_OBS.png"
)

plot_pks_map(
    da_sig_hcst,
    "b) Kolmogorov-Smirnov Test (Hcst. Calibrated Multi-model 1991–2020)",
    "/dados/mmclima/multimodelo/sazonal/figures/artigo/PKS_HCST.png"
)

# # =====================================================
# # MAPA 1 — ANOMALIA
# # =====================================================

# clevs = [-500,-300,-200,-150,-100,-50,-25,
#           25,50,100,150,200,300,500]

# ccols = [

#     # EXTREMO NEGATIVO (abaixo de -500) — flecha
#     "#4A0000",

#     # NEGATIVO — vermelho (chuva abaixo da média)
#     "#7A0000",  # -500 a -300
#     "#AE000C",  # -300 a -200
#     "#FF2E1B",  # -200 a -150
#     "#FF5F26",  # -150 a -100
#     "#FF9D37",  # -100 a -50
#     "#FBE78A",  # -50 a -25

#     # NEUTRO
#     "#FFFFFF",  # -25 a +25

#     # POSITIVO — azul (chuva acima da média)
#     "#99FFFF",  # 25 a 50
#     "#00CCFF",  # 50 a 100
#     "#1199FF",  # 100 a 150
#     "#2A5AEA",  # 150 a 200
#     "#2A2AEA",  # 200 a 300
#     "#00007F",  # 300 a 500

#     # EXTREMO POSITIVO (acima de 500) — flecha
#     "#000033"
# ]
# norm = BoundaryNorm(clevs, len(ccols))

# fig1 = plt.figure(figsize=(10,8))
# ax1 = plt.axes(projection=ccrs.PlateCarree())

# # for spine in ax1.spines.values():
# #     spine.set_linewidth(2.0)

# ax1.patch.set_linewidth(2)
# ax1.patch.set_edgecolor("black")

# setup_map_sam(ax1)

# ax1.set_extent([lon_min, lon_max, lat_min, lat_max])

# ax1.add_feature(cfeature.COASTLINE, linewidth=0.8)
# ax1.add_feature(cfeature.BORDERS, linewidth=0.5)

# img1 = ax1.contourf(
#     da_anom.lon,
#     da_anom.lat,
#     da_anom,
#     levels=clevs,
#     colors=ccols,
#     norm=norm,
#     extend="both",
#     transform=ccrs.PlateCarree()
# )

# cb1 = plt.colorbar(img1, pad=0.03, shrink=0.85)
# cb1.set_label("PRECIPITATION ANOMALY (mm)", fontsize=12)
# cb1.set_ticks(clevs)
# cb1.set_ticklabels([str(v) for v in clevs])

# if month == 8:
#     plt.title(f"OBSERVED ANOMALY: SON 2025", fontsize=14)
# elif month == 2:
#     plt.title(f"OBSERVED ANOMALY: MAM 2025", fontsize=14)
# elif month == 11:
#     plt.title(f"OBSERVED ANOMALY: DJF 24/25", fontsize=14)

# outfile_anom = f"/dados/mmclima/multimodelo/sazonal/figures/artigo/GPCP_ANOM_MAP_AS_{year}{month:02d}.png"

# plt.savefig(outfile_anom, dpi=300, bbox_inches="tight")
# plt.close()

# print("Mapa anomalia salvo:", outfile_anom)

# =====================================================
# MAPA 2 — TERCIL
# =====================================================

cmap_terc = ListedColormap(["red", "white", "blue"])
bounds = [-1.5, -0.5, 0.5, 1.5]
norm_terc = BoundaryNorm(bounds, cmap_terc.N)

#fig2 = plt.figure(figsize=(10,8))
# fig2 = plt.figure(figsize=(9,7))
# ax2 = plt.axes(projection=ccrs.PlateCarree())

fig2 = plt.figure(figsize=(5,8))

# ax2 = fig2.add_axes([0, 0.25, 0.93, 0.70],
#                     projection=ccrs.PlateCarree())

ax2 = fig2.add_axes([0,0.01,1,0.83], projection=ccrs.PlateCarree())

setup_map_sam(ax2)
ax2.set_extent([lon_min, lon_max, lat_min, lat_max])

ax2.add_feature(cfeature.COASTLINE, linewidth=0.8)
ax2.add_feature(cfeature.BORDERS, linewidth=0.5)

img2 = ax2.pcolormesh(
    da_terc.lon,
    da_terc.lat,
    da_terc,
    cmap=cmap_terc,
    norm=norm_terc,
    transform=ccrs.PlateCarree()
)

# ------------------
# LEGENDA INTERNA
# ------------------

legend_elements = [
    mpatches.Patch(facecolor="red",   edgecolor="black", label="Below"),
    mpatches.Patch(facecolor="white", edgecolor="black", label="Normal"),
    mpatches.Patch(facecolor="blue",  edgecolor="black", label="Above")
]

leg = ax2.legend(
    handles=legend_elements,
    loc="lower right",
    frameon=True,
    fontsize=13
)

leg.get_frame().set_facecolor("white")   # fundo branco
leg.get_frame().set_alpha(1.0)           # sem transparência
leg.get_frame().set_edgecolor("black")   # borda preta (opcional)
leg.set_zorder(100)

if month == 8:
    plt.title(f"d) OBSERVED TERCILE CATEGORY: SON 2025", fontsize=14)
elif month == 2:
    plt.title(f"         d) Observed Tercile Category: MAM 2025         ", fontsize=14)    
    #plt.title(f"         d) Observed Tercile Category: MAM 2016         ", fontsize=14)    

elif month == 11:
    plt.title(f"d) OBSERVED TERCILE CATEGORY: DJF 25/26", fontsize=14)

outfile_terc = f"/dados/mmclima/multimodelo/sazonal/figures/artigo/GPCP_TERC_MAP_AS_{year}{month:02d}.png"


# Remove frame automático
ax2.set_frame_on(False)

# Cria moldura manual
rect = Rectangle(
    (0, 0), 1, 1,
    transform=ax2.transAxes,
    fill=False,
    linewidth=2.5,
    edgecolor="black",
    zorder=1000
)

ax2.add_patch(rect)

# colormap 100% branca
white_cmap = ListedColormap(["white"])

fake_norm = Normalize(vmin=0, vmax=1)

fake_map = ScalarMappable(norm=fake_norm, cmap=white_cmap)
fake_map.set_array([])

cb_fake = plt.colorbar(
    fake_map,
    ax=ax2,
    orientation="horizontal",
    pad=0.14,
    shrink=0.6,
    aspect=20
)

# Remove tudo
cb_fake.set_ticks([])
cb_fake.outline.set_visible(False)

cb_fake.ax.tick_params(
    left=False,
    right=False,
    bottom=False,
    top=False,
    labelleft=False,
    labelbottom=False
)

# fundo branco explícito
cb_fake.ax.set_facecolor("white")


plt.savefig(outfile_terc,
            dpi=300,
            bbox_inches='tight',
            pad_inches=0)
plt.close()

print("Mapa tercil salvo:", outfile_terc)

##==========================================
##MAPA 3 — MOST LIKELY TERCILE PROBABILITY
##==========================================

# =====================================================
# ARQUIVO PROBABILIDADE
# =====================================================
calibs = ["regr","gamma","cox"]

xr.set_options(use_bottleneck=False)

for calib in calibs:

    # ###########
    # #CASO 2016#
    # ###########
    # path_in = "/dados/mmclima/multimodelo/artigo/dados/"

    # # Tercil inferior
    # file_tinf = f"prec_probtinf_seas01_multimodel_calibrated_{calib}_20250201.nc"
    # ds_tinf = xr.open_dataset(f"{path_in}/{file_tinf}")

    # prob_tinf_2016 = ds_tinf["probtinf"].isel(time=25) * 100


    # # Tercil superior
    # file_tsup = f"prec_probtsup_seas01_multimodel_calibrated_{calib}_20250201.nc"
    # ds_tsup = xr.open_dataset(f"{path_in}/{file_tsup}")

    # prob_tsup_2016 = ds_tsup["probtsup"].isel(time=25) * 100

    # # Categoria central
    # prob_central_2016 = 100 - prob_tinf_2016 - prob_tsup_2016


    # #--- Probabilidade dos tercis mais prováveis
    # stacked = xr.concat(
    # [prob_tinf_2016, prob_central_2016, prob_tsup_2016],
    # dim="category"
    # )


    # stacked["category"] = ["below", "normal", "above"]
    # stacked_filled = stacked.fillna(0)
    # max_idx = stacked_filled.argmax(dim="category", skipna=True)
    # max_val = stacked_filled.max(dim="category", skipna=True)

    # prob_tercile = xr.zeros_like(max_val)

    # prob_tercile = prob_tercile.where(max_idx != 0, -max_val)
    # prob_tercile = prob_tercile.where(max_idx != 2,  max_val)

    # da_prob = prob_tercile

    #####################
    #CASO GERAL - ARTIGO#
    #####################
    path_in = f"/dados/mmclima/multimodelo/sazonal/posproc/nmme/v1/forecast/{calib}/multimodel/2025/2025020100"
    file = f"fcst_prec_terc_seas01_multimodel_calibrated_{calib}_2025020100.nc"

    file_prob = f"{path_in}/{file}"
    var_prob  = "terc"

    da_prob = xr.open_dataset(file_prob)[var_prob]

    # =====================================================
    # CONVERSÃO LONGITUDE
    # =====================================================

    da_prob = convert_lon(da_prob)

    # =====================================================
    # RECORTE AMÉRICA DO SUL
    # =====================================================

    da_prob = da_prob.sel(
        lon=slice(lon_min, lon_max),
        lat=slice(lat_min, lat_max)
    )

    # =====================================================
    # NÍVEIS (IGUAL GRADS)
    # =====================================================

    clevs_prob = [-100,-90,-80,-70,-60,-50,-40,
                40,50,60,70,80,90,100]

    # =====================================================
    # CORES (VERMELHO → BRANCO → AZUL)
    # =====================================================

    ccols_prob = [

        # LOWER tercile (vermelho)
        "#7A0000",
        "#AE000C",
        "#FF2E1B",
        "#FF5F26",
        "#FF9D37",
        "#FBE78A",

        # NEUTRO
        "#FFFFFF",

        # UPPER tercile (azul)
        "#99FFFF",
        "#00CCFF",
        "#1199FF",
        "#2A5AEA",
        "#2A2AEA",
        "#00007F"
    ]

    norm_prob = BoundaryNorm(clevs_prob, len(ccols_prob))

    # =====================================================
    # FIGURA
    # =====================================================

    fig3 = plt.figure(figsize=(10,8))
    ax3 = plt.axes(projection=ccrs.PlateCarree())

    setup_map_sam(ax3)

    ax3.set_extent([lon_min, lon_max, lat_min, lat_max])

    ax3.add_feature(cfeature.COASTLINE, linewidth=0.8)
    ax3.add_feature(cfeature.BORDERS, linewidth=0.5)

    # =====================================================
    # PLOT MAPA
    # =====================================================

    img3 = ax3.contourf(
        da_prob.lon,
        da_prob.lat,
        da_prob,
        levels=clevs_prob,
        colors=ccols_prob,
        norm=norm_prob,
        transform=ccrs.PlateCarree()
    )

    # =====================================================
    # COLORBAR
    # =====================================================

    cb3 = plt.colorbar(
        img3,
        ax=ax3,
        orientation="horizontal",
        pad=0.1,      # distância mapa → barra
        shrink=0.6,    # comprimento da barra
        aspect=20     # deixa a barra mais "baixa"
    )

    cb3.set_ticks(clevs_prob)
    cb3.ax.tick_params(labelsize=9.5)
    cb3.outline.set_visible(False)

    # # =====================================================
    # # TEXTOS VERTICAIS (IGUAL GRADS)
    # # =====================================================

    cbax = cb3.ax

    # Lower tercile (lado vermelho — esquerda)
    cbax.text(
        0.05, 1.2,
        "Lower tercile",
        ha="left",
        va="bottom",
        fontsize=13,
        transform=cbax.transAxes
    )

    # Upper tercile (lado azul — direita)
    cbax.text(
        0.95, 1.2,
        "Upper tercile",
        ha="right",
        va="bottom",
        fontsize=13,
        transform=cbax.transAxes
    )

    cbax.text(
        0.5, -1.3,
        "White: equal probability for all categories",
        ha="center",
        va="top",
        fontsize=13,
        transform=cbax.transAxes
    )

    # =====================================================
    # TÍTULO
    # =====================================================
    calibs_name = {
        "gamma": "Gamma",
        "regr":  "Normal",
        "cox":   "Cox"
    }

    calibs_letter = {
        "gamma": "b)",
        "regr":  "a)",
        "cox":   "c)"
    }    

    linha1 = f"{calibs_letter[calib]} Calibrated Multi-Model ({calibs_name[calib]})"
    linha2 = "Prob. most likely precip. tercile(%)"


    def get_forecast_title_line(month, year):

        if month == 8:
            return f"FORECAST ISSUED AUG {year} FOR SON {year}"

        elif month == 2:
            #return f"FORECAST ISSUED FEB {year} FOR MAM {year}"
            #return f"FORECAST ISSUED FEB 2016 FOR MAM 2016"

            return f"Forecast Issued Feb {year} for MAM {year}"
            #return f"Forecast Issued Feb 2016 for MAM 2016"

        elif month == 11:
            return f"FORECAST ISSUED NOV {year} FOR DJF {year}/{str(year+1)[-2:]}"
            
    linha3 = get_forecast_title_line(month, year)

    plt.title(
        f"{linha1}\n{linha2}\n{linha3}",
        fontsize=14
    )

    # =====================================================
    # SALVAR
    # =====================================================

    outfile_prob = f"/dados/mmclima/multimodelo/sazonal/figures/artigo/fcst_prec_terc_{calib}_MAM.png"
    #outfile_prob = f"/dados/mmclima/multimodelo/sazonal/figures/artigo/fcst_prec_terc_{calib}_MAM2016.png"

    # Remove frame automático
    ax3.set_frame_on(False)

    # Cria moldura manual
    rect = Rectangle(
        (0, 0), 1, 1,
        transform=ax3.transAxes,
        fill=False,
        linewidth=2.5,
        edgecolor="black",
        zorder=1000
    )

    ax3.add_patch(rect)

    plt.savefig(outfile_prob, dpi=300, bbox_inches="tight")
    plt.close()

    print("Mapa probabilidade salvo:", outfile_prob)
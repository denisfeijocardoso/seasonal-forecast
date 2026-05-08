import os
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import ListedColormap, BoundaryNorm
import cartopy.io.shapereader as shpreader
from scipy.ndimage import zoom
import geopandas as gpd
from shapely.geometry import Point
import geopandas as gpd
import rasterio
from rasterio import features
import numpy as np
import shapely.geometry as sgeom
from matplotlib.path import Path
from matplotlib.patches import PathPatch
import geopandas as gpd
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

def mask_from_shape(lats, lons, shapefile, all_touched=True, buffer_value=0.08):

    gdf = gpd.read_file(shapefile)
    geom = gdf.geometry.unary_union

    if lats.ndim == 1:
        lats2d, lons2d = np.meshgrid(lats, lons, indexing="ij")
    else:
        lats2d, lons2d = lats, lons

    ny, nx = lats2d.shape
    mask = np.zeros((ny, nx), dtype=bool)

    if all_touched:
        geom_test = geom.buffer(buffer_value)
    else:
        geom_test = geom

    for j in range(ny):
        for i in range(nx):
            pt = Point(lons2d[j, i], lats2d[j, i])
            mask[j, i] = geom_test.intersects(pt)

    return mask

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


def fix_wrapping(lons, cor, sig):
    # Se longitudes forem 0–360
    if lons.max() > 180:
        lons = np.where(lons > 180, lons - 360, lons)

    # Reordenar tudo para ficar crescente
    sort_idx = np.argsort(lons)
    lons = lons[sort_idx]
    cor = cor[:, sort_idx]
    if sig is not None:
        sig = sig[:, sort_idx]

    return lons, cor, sig

def shiftgrid(lon0, datain, lonsin, start=True):
    """
    Replica o shiftgrid do Basemap, mas sem Basemap.
    Reorganiza longitudes para que o grid comece em lon0.
    """
    lonsin = np.asarray(lonsin)
    datain = np.asarray(datain)

    if lonsin.ndim != 1:
        raise ValueError("lonsin deve ser 1D")

    # índice onde ocorre o shift
    i0 = np.argmin(np.abs(lonsin - lon0))

    if start:
        # datain sempre retorna no formato original
        dataout = np.concatenate((datain[..., i0:], datain[..., :i0]), axis=-1)
        lonsout = np.concatenate((lonsin[i0:], lonsin[:i0]))
    else:
        # começa em lon0 mas mantém contiguidade
        dataout = np.concatenate((datain[..., i0:], datain[..., :i0]), axis=-1)
        lonsout = np.concatenate((lonsin[i0:], lonsin[:i0]))

    return dataout, lonsout

def plot_map(cor, sig, lons, lats, lead, month, prod, calib, region):

    if region in ["glb", "neb"]:
        # Ajustar longitude quebrada
        lons, cor, sig = fix_wrapping(lons, cor, sig)

    output_dir = "/dados/mmclima/multimodelo/sazonal/figures/artigo"
    os.makedirs(output_dir, exist_ok=True) 

    # ===================================================
    # 1) GERA FIGURA + AX
    # ===================================================

    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

    # ===================================================
    # 2) GRADE 2D
    # ===================================================
    lon2d, lat2d = np.meshgrid(lons, lats)

    # ===================================================
    # 3) PALETA COM UNDER/OVER
    # ===================================================

    if prod == "corskill":
        core_colors = [
#"#FFFFC5",
            "#fbe78a",
            "#ff9d37",
            "#ff5f26",
            "#ff2e1b",
        ]
        under_color = "#ffffff"
        over_color  = "#ae000c"

        bounds = [0.2, 0.4, 0.6, 0.8]

        cmap = plt.matplotlib.colors.ListedColormap(core_colors)
        norm = plt.matplotlib.colors.BoundaryNorm(bounds, cmap.N)

        cmap.set_under(under_color)
        cmap.set_over(over_color)

    elif prod == "rocsstinf" or prod == "rocsstsup":
#         core_colors = [
# #"#FFFFC5",
#             "#fbe78a",
#             "#ff9d37",
#             "#ff5f26",
#             "#ff2e1b",
#         ]
#         under_color = "#ffffff"
#         over_color  = "#ae000c"

#         bounds = [0.2, 0.4, 0.6, 0.8]  

        core_colors = [
            '#fbe78a', 
            '#ff9d37',
            '#ff5f26',
            '#ff2e1b'
        ]
        under_color = "#ffffff"
        over_color  = "#ae000c"

        bounds = [0.5, 0.6, 0.7, 0.8, 0.9]          

        cmap = plt.matplotlib.colors.ListedColormap(core_colors)
        norm = plt.matplotlib.colors.BoundaryNorm(bounds, cmap.N)

        cmap.set_under(under_color)
        cmap.set_over(over_color)        

    if region == "sam":  
        lat_south = -60
        lat_north = 15
        lon_west = -90
        lon_east = -30

        ax.set_extent([lon_west, lon_east, lat_south, lat_north],
                      crs=ccrs.PlateCarree())

        ax.coastlines(resolution="10m", linewidth=1.2, zorder=10)

        # Fronteiras dos países
        ax.add_feature(
            cfeature.BORDERS.with_scale("10m"),
            linewidth=1.2,
            edgecolor="black"
        )

        # ===== Estados do Brasil =====
        shp_estados = "/scripts/clima/denis/sazonal/src/maps/BR_UF_2022/BR_UF_2022.shp"

        reader = shpreader.Reader(shp_estados)

        ax.add_geometries(
            reader.geometries(),
            crs=ccrs.PlateCarree(),
            facecolor="none",
            edgecolor="black",
            linewidth=1.2
        )

        # Paralelos/meridianos
        parallels = [-60, -55, -50, -45, -40, -35, -30, -25, -20, -15, -10, -5, 0, 5, 10, 15]
        #meridians = [-90, -85, -80, -75, -70, -65, -60, -55, -50, -45, -40, -35, -30]
        meridians = [-90, -80, -70, -60, -50, -40, -30]
        fontsize_ticks = 21

        ax.set_yticks(parallels, crs=ccrs.PlateCarree())
        ax.set_yticklabels(["60°S", "55°S", "50°S", "45°S", "40°S", "35°S", "30°S", "25°S", "20°S", "15°S", "10°S", "5°S", "EQ", "5°N", "10°N", "15°N"], fontsize=14)

        ax.set_xticks(meridians, crs=ccrs.PlateCarree())
        ax.set_xticklabels(["90°W", "80°W", "70°W", "60°W", "50°W", "40°W", "30°W"],
                           fontsize=14)


    elif region == "glb":  
        # GLOBAL
        ax.set_global()
        ax.coastlines(resolution="110m", linewidth=1.2)

        parallels = [-60, -30, 0, 30, 60]
        meridians = [-180, -120, -60, 0, 60, 120, 180]

        ax.set_yticks(parallels, crs=ccrs.PlateCarree())
        ax.set_yticklabels(["60°S", "30°S", "0°", "30°N", "60°N"], fontsize=14)

        ax.set_xticks(meridians, crs=ccrs.PlateCarree())
        ax.set_xticklabels(["180°W", "120°W", "60°W", "0°", "60°E", "120°E", "180°E"],
                           fontsize=14)

    # ==========================================
    # SHAPE AMÉRICA DO SUL (Natural Earth)
    # ==========================================

    shp_sa = shpreader.natural_earth(
        resolution='10m',
        category='cultural',
        name='admin_0_countries'
    )

    gdf = gpd.read_file(shp_sa).to_crs("EPSG:4326")

    # Filtrar só América do Sul
    sa_countries = [
        "Brazil", "Argentina", "Uruguay", "Paraguay",
        "Bolivia", "Peru", "Chile", "Colombia",
        "Venezuela", "Guyana", "Suriname", "Ecuador",
        "France"
    ]

    gdf_sa = gdf[gdf["ADMIN"].isin(sa_countries)]

    geom_sa = gdf_sa.unary_union

    img = ax.contourf(
        lons, lats, cor,
        levels=bounds,
        cmap=cmap,
        norm=norm,
        extend="both",
        transform=ccrs.PlateCarree()
    )

    # ==========================================
    # DSTK MASK — PINTA OCEANO DE BRANCO
    # ==========================================

    if region == "sam":
        add_dstk_mask_cartopy(ax, geom_sa, color="white", zorder=5)

    shpfile = shpreader.natural_earth(
        resolution='10m',
        category='cultural',
        name='admin_0_countries'
    )


    # ===========
    # COLORBAR
    # ===========
    
    #if calib == "cox" and prod == "corskill":
    if prod == "corskill":        
        cax = inset_axes(
            ax,
            width="55%",     # comprimento
            height="3.8%",   # espessura
            loc="lower center",
            bbox_to_anchor=(0, -0.11, 1, 1),  # empurra pra fora do mapa
            bbox_transform=ax.transAxes,
            borderpad=0
        )

        cbar = plt.colorbar(
            img,
            cax=cax,
            orientation="horizontal",
            ticks=bounds
        )

        if prod == "rocsstsup" or prod == "rocsstinf":
            cbar.ax.tick_params(labelsize=18)
        else:
            cbar.ax.tick_params(labelsize=18)

    elif prod == "rocsstsup" or prod == "rocsstinf":
        cax = inset_axes(
            ax,
            width="55%",     # comprimento
            height="3.8%",   # espessura
            loc="lower center",
            bbox_to_anchor=(0, -0.11, 1, 1),  # empurra pra fora do mapa
            bbox_transform=ax.transAxes,
            borderpad=0
        )

        cbar = plt.colorbar(
            img,
            cax=cax,
            orientation="horizontal",
            ticks=bounds
        )

        if prod == "rocsstsup" or prod == "rocsstinf":
            cbar.ax.tick_params(labelsize=18)
        else:
            cbar.ax.tick_params(labelsize=18)

    ##=================
    ## SIGNIFICÂNCIA
    ##=================
    if region == "glb":
        if sig is not None:
            y, x = np.where(sig == 1)
            ax.scatter(
                lon2d[y, x], lat2d[y, x],
                s=5,
                facecolor="black",         # cor branca
                edgecolor="none",          # sem borda
                #alpha=0.4,                   
                #color="#222222",
                transform=ccrs.PlateCarree(),
                linewidth=0
            )


    elif region == "sam" and prod == "corskill":
        if sig is not None:
            y, x = np.where(sig == 1)
            ax.scatter(
                lon2d[y, x], lat2d[y, x],
                s=15,
                facecolor="black",         # cor branca
                edgecolor="none",  
                transform=ccrs.PlateCarree(),
                linewidth=0
            )            

    elif region == "sam" and prod != "corskill":
        if sig is not None:
            y, x = np.where(sig == 1)
            ax.scatter(
                lon2d[y, x], lat2d[y, x],
                s=20,
                facecolor="black",         # cor branca
                edgecolor="none",  
                transform=ccrs.PlateCarree(),
                linewidth=0
            )        

    # =========
    # TÍTULOS 
    # =========    "", "rocsstinf", "rocsstsup"
    if prod == "corskill":

        if calib == "regr":
            title_txt = (
                "b) Correlation btw hcst. and obs. precip. anom.: Normal\n"
                "Calibrated Multi-Model : GPCP (1991–2020)\n"
                "Issued: Feb  Valid for MAM"
            )

        elif calib == "cox":
            title_txt = (
                "\nd) Correlation btw hcst. and obs. precip. anom.: Cox       \n"
                "Calibrated Multi-Model : GPCP (1991–2020)\n"
                "Issued: Feb  Valid for MAM"
            )

        elif calib == "gamma":
            title_txt = (
                "\nc) Correlation btw hcst. and obs. precip. anom.: Gamma\n"
                "Calibrated Multi-Model : GPCP (1991–2020)\n"
                "Issued: Feb  Valid for MAM"
            )

        elif calib == "nocalib":
            title_txt = (
                "      a) Correlation btw hcst. and obs. precip. anom.       \n"
                "Calibrated Multi-Model : GPCP (1991–2020)\n"
                "Issued: Feb  Valid for MAM"
            )

    elif prod == "rocsstinf": 
        if calib == "regr":
            title_txt = (
                "a) ROC Area: Calibrated Multi-Model: GPCP (1991–2020)\n"
                "Event: precip. in lower tercile (below normal): Normal\n"
                "Issued: Feb  Valid for MAM"
            )

        elif calib == "cox":
            title_txt = (
                "c) ROC Area: Calibrated Multi-Model: GPCP (1991–2020)\n"
                "Event: precip. in lower tercile (below normal): Cox\n"
                "Issued: Feb  Valid for MAM"
            )

        elif calib == "gamma":
            title_txt = (
                "e) ROC Area: Calibrated Multi-Model: GPCP (1991–2020)\n"
                "Event: precip. in lower tercile (below normal): Gamma\n"
                "Issued: Feb  Valid for MAM"
            )
            
    elif prod == "rocsstsup": 
        if calib == "regr":
            title_txt = (
                "b) ROC Area: Calibrated Multi-Model: GPCP (1991–2020)\n"
                "Event: precip. in upper tercile (above normal): Normal\n"
                "Issued: Feb  Valid for MAM"
            )

        elif calib == "cox":
            title_txt = (
                "d) ROC Area: Calibrated Multi-Model: GPCP (1991–2020)\n"
                "Event: precip. in upper tercile (above normal): Cox\n"
                "Issued: Feb  Valid for MAM"
            )

        elif calib == "gamma":
            title_txt = (
                "f) ROC Area: Calibrated Multi-Model: GPCP (1991–2020)\n"
                "Event: precip. in upper tercile (above normal): Gamma\n"
                "Issued: Feb  Valid for MAM"
            )


    # ===== aplica no eixo Cartopy =====
    if prod == "rocsstsup" or prod == "rocsstinf":
        ax.set_title(title_txt, fontsize=23)
    else:
        #ax.set_title(title_txt, fontsize=17)
        ax.set_title(title_txt, fontsize=21)

    # sobe um pouco pra não colidir com a figura
    ax.title.set_position([0.5, 1.03])

    # =======
    # SALVAR
    # =======
    fname = f"{output_dir}/{region}_prec_{prod}_{lead}_multimodel_calibrated_{calib}_{month}.png"

    for spine in ax.spines.values():
        spine.set_linewidth(2.0)

    plt.savefig(fname, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"Mapa salvo: {fname}")



#Abrir máscara
mask = xr.open_dataset("/dados/mmclima/multimodelo/artigo/dados/landmask_interp.nc")
mask_land = mask["land"]

# Lista dos leads
lead = "seas01"
region = "sam"
input_dir = "/dados/mmclima/multimodelo/artigo/dados" 

calibrations = ["regr","nocalib","gamma","cox"]#"regr","nocalib","gamma","cox"
month = 2

for calib in calibrations:

    if calib == "nocalib":
        products = ["corskill"]
    else:
        products = ["corskill", "rocsstinf", "rocsstsup"]

    for product in products:

        month_str = f"{month:02d}"

        # ======================================================
        # 1) ABRIR CAMPO PRINCIPAL
        # ======================================================

        if product == "corskill":
            ds_cor = xr.open_dataset(
                f"{input_dir}/prec_corskill_{lead}_multimodel_calibrated_{calib}_2025{month_str}01.nc"
            )
            cor = ds_cor["corskill"]

        elif product == "rocsstinf":
            ds_cor = xr.open_dataset(
                f"{input_dir}/prec_rocsstinf_{lead}_multimodel_calibrated_{calib}_2025{month_str}01.nc"
            )
            cor = ds_cor["rocsstinf"]

        elif product == "rocsstsup":
            ds_cor = xr.open_dataset(
                f"{input_dir}/prec_rocsstsup_{lead}_multimodel_calibrated_{calib}_2025{month_str}01.nc"
            )
            cor = ds_cor["rocsstsup"]

        lats = ds_cor["lat"].values
        lons = ds_cor["lon"].values

        # ======================================================
        # 2) CORRIGIR LONGITUDE 0–360 -> -180–180
        # ======================================================

        lons_fixed = ((lons + 180) % 360) - 180

        idx = np.argsort(lons_fixed)

        lons_fixed = lons_fixed[idx]
        cor = cor.isel(lon=idx)

        # ======================================================
        # 3) GERAR MÁSCARA AMÉRICA DO SUL
        # ======================================================

        mask_sa = mask_from_shape(
            lats,
            lons_fixed,
            "/dados/mmclima/multimodelo/artigo/dados/sa_buffer.shp",
            all_touched=True
        )

        # from scipy.ndimage import binary_dilation
        # mask_sa = binary_dilation(mask_sa, iterations=1)

        # ======================================================
        # 4) APLICAR MÁSCARA NO CAMPO PRINCIPAL
        # ======================================================

        cor_field = cor#.where(mask_sa)

        # ======================================================
        # 5) ABRIR SIGNIFICÂNCIA
        # ======================================================

        if product == "corskill":
            ds_sig = xr.open_dataset(
                f"{input_dir}/prec_sigcorskill_{lead}_multimodel_calibrated_{calib}_2025{month_str}01.nc"
            )
            sig = ds_sig["sigcorskill"]

        elif product == "sigaroctinf":
            ds_sig = xr.open_dataset(
                f"{input_dir}/prec_sigaroctinf_{lead}_multimodel_calibrated_{calib}_2025{month_str}01.nc"
            )
            sig = ds_sig["sigaroctinf"]

        elif product == "sigaroctsup":
            ds_sig = xr.open_dataset(
                f"{input_dir}/prec_sigaroctsup_{lead}_multimodel_calibrated_{calib}_2025{month_str}01.nc"
            )
            sig = ds_sig["sigaroctsup"]

        # ======================================================
        # 6) ALINHAR SIG COM NOVO EIXO DE LON
        # ======================================================

        sig = sig.isel(lon=idx)

        # ======================================================
        # 7) APLICAR MÁSCARA NA SIGNIFICÂNCIA
        # ======================================================

        sig_field = sig#.where(mask_sa)

        # ======================================================
        # 8) PLOT
        # ======================================================

        plot_map(
            cor_field.values,
            sig_field.values,
            lons_fixed,
            lats,
            lead,
            month,
            product,
            calib,
            region
        )

        plt.show()


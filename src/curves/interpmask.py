import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.mpl.ticker as cticker
import pandas as pd
from matplotlib.ticker import FixedLocator

maskpath = '/scripts/clima/denis/sazonal/src/curves/land-sea-mask-nmme.nc'
datapath = '/scripts/clima/denis/sazonal/src/curves/t2mt.nc'

def interpolation_mask(maskpath, datapath):
    mask = xr.open_dataset(maskpath)
    data = xr.open_dataset(datapath)

    # Renomear coordenadas antes da interpolação
    mask = mask.rename({"Y": "lat", "X": "lon"})

    mask_var = mask['land']
    lat_target = data['lat']
    lon_target = data['lon']

    # Interpolação nearest
    mask_regrid = mask_var.interp(lat=lat_target, lon=lon_target, method='nearest')
    mask_regrid = mask_regrid.assign_coords(lat=lat_target, lon=lon_target)
    mask_regrid.attrs.pop("coordinates", None)

    mask_regrid.to_netcdf("land-sea-mask-nmme-regrid.nc")

# --- Ler máscara interpolada ---
mask_regrid = xr.open_dataset('/scripts/clima/denis/sazonal/src/curves/land-sea-mask-nmme-regrid.nc')
land = mask_regrid['land']

# Selecionar apenas os pontos de terra (land == 1)
valid = land.where(land == 1)
valid_points = valid.stack(points=("lat", "lon")).dropna(dim="points")

# Obter as coordenadas
lats = valid_points['lat'].values
lons = valid_points['lon'].values

# Converter longitudes de 0–360 para -180–180
lons = (lons + 180) % 360 - 180

# --- Ordenar do norte para o sul e oeste para leste ---
coords = np.column_stack((lats, lons))
order = np.lexsort((lons, -lats))  # lat decrescente, lon crescente
coords = coords[order]
lats, lons = coords[:, 0], coords[:, 1]

# Criar IDs
ids = np.arange(1, len(lats) + 1)

# --- Salvar as coordenadas em um TXT ---
df = pd.DataFrame({
    'ID': ids,
    'lat': lats,
    'lon': lons
})

txt_path = "/scripts/clima/denis/sazonal/src/curves/coords_points_curves.txt"
df.to_csv(txt_path, sep='\t', index=False, header=True)
print(f" Coordenadas salvas em: {txt_path}")

# --- Plotar o mapa ---
plt.figure(figsize=(30, 15))
ax = plt.axes(projection=ccrs.PlateCarree())

# Apenas o contorno dos continentes
ax.coastlines(linewidth=0.4, color='black')
ax.set_global()

# Adicionar grade de latitude e longitude
gl = ax.gridlines(draw_labels=True, linewidth=0.3, color='gray', alpha=0.5, linestyle='--')
gl.top_labels = False
gl.right_labels = False
gl.xlocator = FixedLocator(np.arange(-180, 181, 30))
gl.ylocator = FixedLocator(np.arange(-90, 91, 15))
gl.xlabel_style = {'size': 14}
gl.ylabel_style = {'size': 14}

# Plotar IDs
for i, (lon, lat) in enumerate(zip(lons, lats), start=1):
    ax.text(lon, lat, str(i), fontsize=4, color='black', fontweight=700,
            transform=ccrs.PlateCarree(), ha='center', va='center', zorder=4)

plt.title("PONTOS DAS CURVAS DE DISTRIBUIÇÃO", fontsize=16)

# --- Salvar figura ---
output_path = "/scripts/clima/denis/sazonal/src/curves/map_points_curves_grid.png"
plt.savefig(output_path, dpi=400, bbox_inches='tight')
print(f" Figura salva em: {output_path}")

plt.show()




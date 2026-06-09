import xarray as xr
import numpy as np

# Abrir arquivos
mask_ds = xr.open_dataset("/dados/mmclima/multimodelo/artigo/dados/land-sea-mask-nmme.nc")
skill_ds = xr.open_dataset("/dados/mmclima/multimodelo/artigo/dados/prec_sigcorskill_seas02_multimodel_calibrated_nocalib_20250201.nc")

# Extrair coordenadas alvo
target_lat = skill_ds["lat"]
target_lon = skill_ds["lon"]

# Corrigir latitude da máscara
mask_lat = mask_ds["Y"]

if mask_lat[0] > mask_lat[-1]:
    print("Invertendo latitude da máscara...")
    mask_ds = mask_ds.sortby("Y")


# Renomear coordenadas (padrão)
mask_ds = mask_ds.rename({"Y": "lat", "X": "lon"})


# Interpolação para grade alvo

mask_interp = mask_ds.interp(
    lat=target_lat,
    lon=target_lon,
    method="nearest"
)

# Extrair máscara final
mask_final = mask_interp["land"]   # ajuste se o nome da variável for outro

print("Shape final:", mask_final.shape)

mask_final.to_netcdf("/dados/mmclima/multimodelo/artigo/dados/landmask_interp.nc")
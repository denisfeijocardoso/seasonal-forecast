from pathlib import Path

''' Nesse script são definidos os diretórios usados na geração 
dos produtos de previsão sazonal do multimodelo e modelos individuais'''

PATH_HCST = Path(
    "/dados/mmclima/multimodelo/seasonal/hindcast"
    )

PATH_FCST = Path(
    "/dados/mmclima/multimodelo/seasonal/forecast"
    )

PATH_OBS  = Path(
    "/dados/mmclima/multimodelo/seasonal/obs"
    )

PATH_POSPROC = Path(
    "/dados/mmclima/multimodelo/seasonal/posproc"
    )

PATH_FIG = Path(
    "/dados/mmclima/multimodelo/seasonal/figures"
    )

PATH_LOG = Path(
    "/scripts/clima/denis/seasonal/src/logs"
)

PATH_GRADS = Path(
    "/scripts/clima/denis/seasonal/src/plotting"
)
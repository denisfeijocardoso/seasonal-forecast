# Visualizadores Streamlit

Execute a partir da raiz do projeto.

## Mapas de forecast

```bash
streamlit run streamlit/app.py
```

O app mostra apenas figuras em caminhos `.../forecast/...`. A pasta pode ser a raiz geral:

```text
/dados/mmclima/multimodelo/seasonal/figures
```

ou um subdiretorio especifico:

```text
/dados/mmclima/multimodelo/seasonal/figures/nmme/v1/forecast
```

## Curvas

```bash
streamlit run streamlit/curves_app.py
```

O app mostra apenas figuras em caminhos `.../curves/...` e usa:

```text
src/curves/coords_points_curves.txt
```

para associar cada numero de ponto a latitude/longitude.

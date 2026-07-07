# Previsao Climatica Sazonal - Multimodelo

Sistema em Python para geracao operacional de previsoes climaticas sazonais, com modelos individuais e multimodelo.

Os multimodelos sao gerados usando as bases NMME e Copernicus/C3S, alem do modelo BAM - Brazilian Global Atmospheric Model, do CPTEC/INPE, e do ECHAM processado na FUNCEME.

O pipeline processa previsoes em tempo real, aplica calibracoes, gera produtos em NetCDF, mapas, curvas por ponto e documentacao da versao do multimodelo.

## Ambiente

Ative o ambiente antes de executar:

```bash
source /scripts/subsaz/miniconda3/etc/profile.d/conda.sh
conda activate /scripts/subsaz/miniconda3/envs/subc
```

Dependencias principais estao em:

```bash
requirements.txt
```

## Estrutura

```text
src/
  calibration/   Metodos de calibracao: regressao, COX e sem calibracao
  config/        Configuracoes de modelos, variaveis, periodos e caminhos
  curves/        Geracao de curvas por ponto para o multimodelo
  data/          Download e interpolacao de dados
  forecast/      Processamento da previsao em tempo real
  hindcast/      Processamento dos hindcasts
  io/            Escrita de NetCDFs, caminhos e README de versao
  observation/   Estatisticas observacionais
  plotting/      Mapas em Python e recursos de plotagem
  processing/    Agregacoes mensais/sazonais e montagem de produtos
  run/           Entrypoints executaveis
  verification/  Rotinas de verificacao

streamlit/
  app.py         Visualizador local das figuras geradas
```

## Configuracao

As principais configuracoes ficam em:

```text
src/config/models.yaml
src/config/parameters_run.yaml
src/config/variables_download.yaml
src/config/paths.py
```

`models.yaml` define modelos, versoes, diretorios e a versao do multimodelo (`multimodel_version`). Essa versao controla a pasta de saida, por exemplo:

```text
/dados/mmclima/multimodelo/seasonal/posproc/nmme/v1
/dados/mmclima/multimodelo/seasonal/figures/nmme/v1
```

Ao mudar a versao do multimodelo no YAML, o pipeline passa a escrever em `v2`, `v3`, etc.

## Pipeline Operacional

O entrypoint recomendado e:

```bash
python -m src.run.operational --base nmme --year 2026 --month 6
```

Ele executa:

1. `realtime`: download, interpolacao, produtos NetCDF, README da versao e mapas;
2. validacao minima dos NetCDFs do multimodelo;
3. `curves`: curvas do multimodelo por ponto.

Opcionalmente, com `--run-verification`, tambem executa `operational_verification`.

Exemplo para uma variavel:

```bash
python -m src.run.operational --base nmme --year 2026 --month 6 --var prec
```

Retomar apenas curvas, usando NetCDFs ja existentes:

```bash
python -m src.run.operational --base nmme --year 2026 --month 6 --skip-realtime
```

Pular curvas:

```bash
python -m src.run.operational --base nmme --year 2026 --month 6 --skip-curves
```

Refazer curvas ja existentes:

```bash
python -m src.run.operational --base nmme --year 2026 --month 6 --overwrite-curves
```

Rodar tambem a verificacao operacional e seus mapas:

```bash
python -m src.run.operational --base nmme --year 2026 --month 6 --run-verification
```

Rodar tambem a verificacao operacional excluindo um modelo apenas da etapa de verificacao:

```bash
python -m src.run.operational --base nmme --year 2026 --month 6 --run-verification --exclude-verification-model cansips
```

Rodar somente verificacao operacional:

```bash
python -m src.run.operational --base nmme --year 2026 --month 6 --skip-realtime --run-verification
```

## Mapas

A geracao de mapas usa Python, e e enfileirada apos a escrita dos NetCDFs. A fila pode rodar em paralelo:

```bash
--map-workers 4
```

Mapas ja existentes sao pulados automaticamente.

## Curvas

As curvas do multimodelo sao geradas por:

```bash
python -m src.run.curves --base nmme --year 2026 --month 6
```

Por padrao, curvas ja existentes sao puladas. Para sobrescrever:

```bash
python -m src.run.curves --base nmme --year 2026 --month 6 --overwrite
```

## Execucao Realtime Direta

Para rodar apenas a etapa realtime:

```bash
python -m src.run.realtime --base nmme --year 2026 --month 6
```

Rodar so uma variavel:

```bash
python -m src.run.realtime --base nmme --year 2026 --month 6 --var t2mt
```

Rodar mapas a partir de NetCDFs ja existentes:

```bash
python -m src.run.realtime --base nmme --year 2026 --month 6 --skip-products
```

## Verificacao Operacional

Para baixar/interpolar hindcasts, rodar a verificacao e gerar mapas das metricas:

```bash
python -m src.run.operational_verification --base nmme --year 2026 --month 6
```

Para reaproveitar hindcasts ja baixados/interpolados:

```bash
python -m src.run.operational_verification --base nmme --year 2026 --month 6 --skip-download --skip-interpolation
```

Para reaproveitar hindcasts ja baixados/interpolados e excluir temporariamente um modelo do multimodelo/verificacao:

```bash
python -m src.run.operational_verification --base nmme --year 2026 --month 6 --skip-download --skip-interpolation --exclude-model cansips
```

Para rodar apenas os mapas a partir dos NetCDFs de verificacao existentes:

```bash
python -m src.run.operational_verification --base nmme --year 2026 --month 6 --only-maps
```

Para rodar apenas os mapas de verificacao de um modelo/calibracao especificos via pipeline operacional:

```bash
python -m src.run.operational --base nmme --year 2026 --month 2 --model canesm --calibration regr --skip-realtime --run-verification --verification-only-maps
```

Para pular mapas:

```bash
python -m src.run.operational_verification --base nmme --year 2026 --month 6 --skip-maps
```

Para rodar apenas o calculo/escrita das metricas, sem download, interpolacao e mapas:

```bash
python -m src.run.verification --base nmme --year 2026 --month 6
```

## Visualizador Streamlit

Para visualizar mapas de forecast:

```bash
streamlit run streamlit/app.py
```

Para visualizar mapas de verificacao:

```bash
streamlit run streamlit/verification_app.py
```

Para visualizar curvas por ponto:

```bash
streamlit run streamlit/curves_app.py
```

O app procura figuras em `PATH_FIG`, definido em:

```text
src/config/paths.py
```

## Saidas Principais

Produtos NetCDF:

```text
/dados/mmclima/multimodelo/seasonal/posproc/<base>/<versao>/forecast/<calibracao>/<modelo>/<ano>/<data>
```

Produtos NetCDF de verificacao:

```text
/dados/mmclima/multimodelo/seasonal/posproc/<base>/<versao>/verification/<calibracao>/<modelo>
```

Figuras:

```text
/dados/mmclima/multimodelo/seasonal/figures/<base>/<versao>/forecast/<calibracao>/<modelo>/<ano>/<data>
```

Figuras de verificacao:

```text
/dados/mmclima/multimodelo/seasonal/figures/<base>/<versao>/verification/<calibracao>/<modelo>
```

README da versao do multimodelo:

```text
/dados/mmclima/multimodelo/seasonal/posproc/<base>/<versao>/README.md
```

## Variaveis e Calibracoes

Variaveis configuradas:

```text
prec
t2mt
```

Calibracoes configuradas:

```text
regr
cox
nocalib
```

Periodos gerados:

```text
mnth00, mnth01, mnth02, mnth03, mnth04
seas00, seas01, seas02
```

## Logs

Logs de execucao sao gerados em:

```text
src/logs/
```

Essa pasta e ignorada pelo Git.

<<<<<<< HEAD
### Previsões Climáticas Sazonais Calibradas - Multimodelo e Modelos Individuais 
### Dois conjuntos de modelos diferentes são usados p/ construir o Multimodelo + CPTEC-BAM1.2
### As duas bases de modelo usadas são: NMME e COPERNICUS

Este projeto realiza a geração de previsões climáticas sazonais utilizando diferentes modelos climáticos, tanto individualmente quanto em conjunto via multimodelo. As previsões são processadas em três versões:

- Modelos e Multimodelo não calibrados
- Modelos calibrados por dois métodos distintos (COX e Regressão)
- Multimodelo calibrado

## Estrutura e Funcionalidades

O código está modularizado e dividido por tipo de dado e função:

### Módulos principais:
- `src`: É onde fica o código-fonte principal do projeto.
- `hindcast`: Tratamento e download dos dados de hindcast dos modelos climáticos
- `forecast`: Manipulação dos dados de previsão em tempo real
- `observation`: Leitura e tratamento das observações
- `calibration`: Aplicação dos métodos de calibração nos dados previstos
- `verification`: Avaliação das previsões calibradas com métricas determinísticas e probabilísticas
- `config`: Gerenciamento das versões dos modelos e nomes de diretórios de forma centralizada
- `data`: Scripts utilitários para download, interpolação e renomeação de arquivos
- `maps`: Scripts utilitários para gerar os mapas de previsão sazonal do multimodelo e modelos individuais
- `figures`: Diretório para onde vão as figuras geradas
---

## Processos principais:

- Download automatizado de hindcasts e forecasts do Copernicus e NMME
- Organização dos dados por modelo e versão
- Aplicação de dois métodos distintos de calibração
- Geração de arquivos de saída com nomes padronizados
- Verificação das previsões calibradas (módulo `verification/`)

---

## Como usar

1. Instale as dependências:

pip install -r requirements.txt 

2. Execute qualquer módulo usando o Python com -m, por exemplo:

python -m src.sazonal.data.download

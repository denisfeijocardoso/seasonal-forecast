import xarray as xr
from src.config.loader import MODELS_CONFIG
from src.config.paths import PATH_FCST

''' Nesse módulo as funções carregam as versões dos modelos, do multimodelo
e também constroem os títulos usados nos nomes dos diretorios e titulo dos mapas.
Além de outras funções adicionais associadas a checagem dos modelos, dimensões etc.'''


#Modelos que o nome do diretório e do título são diferentes dos demais
diferent_name = {
    "geos", 
    "gemnemo",
    "spear", 
    "bam", 
    "echam"
}
    
def get_model_version(model: str) -> str:

    try:
        return MODELS_CONFIG["models"][model]["version"]
    
    except KeyError:
        raise ValueError(f"Modelo inválido: {model}")


def get_multimodel_version(base: str) -> str:
    return MODELS_CONFIG["bases"][base]["multimodel_version"]

def get_dim_names(
        base: str,
        model: str
) -> dict[str, str]:
            
    base_dims = MODELS_CONFIG["bases"][base]["dims"]
    model_dims = MODELS_CONFIG["models"][model].get("dims", {})

    dims = {
        **base_dims,
        **model_dims
    }

    return dims

def get_list_models(base: str) -> list[str]:
        return MODELS_CONFIG["bases"][base]["models"]
    
    
def build_model_title(model: str) -> str:

    try:
        title = MODELS_CONFIG["models"][model]["title"]
        version = get_model_version(model)

        if model not in diferent_name:
            return f"{title}{version}"
        
        else:
            return title
    
    except KeyError:
        raise ValueError(f"Modelo inválido {model}")      


def build_model_dir_name(model: str) -> str:


    dir_name = MODELS_CONFIG["models"][model]["directory"]
    version = get_model_version(model)
    
    try:

        if model not in diferent_name:
            return f"{dir_name}{version}"
        
        elif model == "multimodel":
            return model
        
        else:
            return dir_name
    
    except KeyError:
        raise ValueError(f"Modelo inválido: {model}")

            
def is_all_nan(file_path):
    
    try:
        with xr.open_dataset(file_path, decode_times=False)  as ds:

            data = ds[list(ds.data_vars)[0]]

            return not data.notnull().any().compute().item()

    except Exception as e:
        print(f"Erro em {file_path}: {e}")
        return True
        

def check_models(
        base: str, 
        var: str, 
        year_fcst: int, 
        month_fcst: int
):
    '''Checa quais modelos têm arquivos disponíveis para uma data e variável'''

    month = f"{month_fcst:02d}"
    
    models = get_list_models(base)

    models_available = []

    for mdl in models:

        name_model_dir = build_model_dir_name(mdl)

        print(name_model_dir)

        file_path = (
            PATH_FCST / 
            base / 
            name_model_dir / 
            str(year_fcst) / 
            f"{var}_monthly_{name_model_dir}_fcst_{year_fcst}{month}01.nc"
        )

        if file_path.exists() and file_path.stat().st_size > 2000:

            if not is_all_nan(file_path):         
                models_available.append(mdl)

    return models_available 
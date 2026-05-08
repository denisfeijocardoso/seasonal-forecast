class ConfigModelos:

    ''' NESSE MÓDULO É FEITA A CONFIGURAÇÃO DAS VERSÕES ATIVAS DOS MODELOS
    TANTO DA BASE DE DADOS COPERNICUS QUANTO DOS MODELOS NMME (versions_models_cs3,
    versions_models_nmme). TAMBÉM AQUI É DEFINIDA QUAL A VERSÃO ATIVA NO MOMENTO
    DO MULTIMODELO NMME E COPERNICUS EM versions_multimodel'''
    
    #Versões ativas dos modelos COPERNICUS
    versions_models_cs3 = {"ecmwf": "51",
            "ukmo": "610",
            "meteo_france": "9",
            "dwd": "22",
            "cmcc": "4",
            "ncep": "2",
            "jma": "4",
            "eccc4": "4",
            "eccc5": "5",
            "bom": "2"}
    #

    #Versões ativas dos modelos NMME
    versions_models_nmme = {"cfsv2": "2",
        "canesm5": "5",
        "gem52nemo": "52",
        "spear": "1" ,
        "cesm1": "1",
        "ccsm4": "4",
        "geos5v2": "2"}
    #

    #Versão Conjunto Multimodelo usado no nome do diretorio /dados/mmclima/multimodelo/sazonal/posproc/
    versions_multimodel = {"nmme": "v1", "copernicus": "v3"}
    #
    # Lista completa dos modelos COPERNICUS (CS3)
    name_download_models_cs3 = ["ecmwf", "ukmo","meteo_france","dwd","cmcc","ncep","jma","eccc4","eccc5","bom"] 
    # Lista completa dos modelos NMME
    name_download_models_nmme = ["canesm5", "ccsm4", "cesm1", "cfsv2", "gem52nemo", "geos5v2", "spear"] 
    
    @classmethod
    def get_model_version(cls, model: str) -> str:
        return cls.versions_models_cs3.get(model, "")

    @classmethod
    def get_multimodel_version(cls, base: str) -> str:
        return cls.versions_multimodel[base]
        
    @classmethod
    def get_model_dir_c3s(cls, model: str) -> str:
        version = cls.get_model_version(model)

        #COPERNICUS
        if model == "ecmwf":
            return f"ecmwfs{version}"
        elif model == "ukmo":
            return f"ukmos6v{version}"
        elif model == "meteo_france":
            return f"mfs{version}"
        elif model == "dwd":
            return f"dwds{version}"
        elif model == "cmcc":
            return f"cmccs{version}"
        elif model == "ncep":
            return f"nceps{version}"
        elif model == "jma":
            return f"jmas{version}"
        elif model.startswith("eccc"):
            return f"ecccs{version}"
        elif model == "bom":
            return f"boms{version}"
        elif model == "bam12":
            return f"bam12"    

    @classmethod
    def get_model_title_c3s(cls, model: str) -> str:
        version = cls.get_model_version(model)

        #COPERNICUS
        if model == "ecmwf":
            return f"ECMWF_v{version}"
        elif model == "ukmo":
            return f"UKMetOffice_v{version}"
        elif model == "meteo_france":
            return f"Météo-France_v{version}"
        elif model == "dwd":
            return f"DWD_v{version}"
        elif model == "cmcc":
            return f"CMCC_v{version}"
        elif model == "ncep":
            return f"NCEP_v{version}"
        elif model == "jma":
            return f"JMA_v{version}"
        elif model.startswith("eccc"):
            return f"ECCC_v{version}"
        elif model == "bom":
            return f"BOM_v{version}"
        elif model == "bam12":
            return f"CPTEC_BAM1.2"  

    @classmethod
    def get_model_dir_nmme(cls, model: str) -> str:
        version = cls.get_model_version(model)

        #NMME
        if model == "canesm5":
            return model
        elif model == "ccsm4":
            return model
        elif model == "cesm1":
            return model
        elif model == "cfsv2":
            return model
        elif model == "gem52nemo":
            return model
        elif model == "geos5v2":
            return model
        elif model == "spear":
            return model
        elif model == "bam12":
            return model

    @classmethod
    def get_model_title_nmme(cls, model: str) -> str:
        version = cls.get_model_version(model)

        #NMME
        if model == "canesm5":
            return "CanESM5"
        elif model == "ccsm4":
            return "NCAR_CCSM4"
        elif model == "cesm1":
            return "NCAR_CESM1"
        elif model == "cfsv2":
            return "CFSv2"
        elif model == "gem52nemo":
            return "GEM5.2_NEMO"
        elif model == "geos5v2":
            return "NASA_GEOS5v2"
        elif model == "spear":
            return "GFDL_SPEAR"
        elif model == "bam12":
            return f"CPTEC_BAM1.2"  

    @classmethod
    def get_model_title(cls, model: str) -> str:
        version = cls.get_model_version(model)

        #COPERNICUS
        if model == "ecmwf":
            return f"ECMWF_{version}"
        elif model == "ukmo":
            return f"UK MetOffice_{version}"
        elif model == "meteo_france":
            return f"Météo-France_{version}"
        elif model == "dwd":
            return f"DWD_{version}"
        elif model == "cmcc":
            return f"CMCC_{version}"
        elif model == "ncep":
            return f"NCEP_{version}"
        elif model == "jma":
            return f"JMA_{version}"
        elif model.startswith("eccc"):
            return f"ECCC_{version}"
        elif model == "bom":
            return f"BOM_v{version}" 
        elif model == "bam12":
            return f"CPTEC_BAM1.2" 
            


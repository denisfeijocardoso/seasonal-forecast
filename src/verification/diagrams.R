library(verification)
library(ncdf4)
source("/scripts/clima/denis/sazonal/src/verification/roc.area.eurobrisa.r")
source("/scripts/clima/denis/sazonal/src/verification/attributediagr.r")

library(ncdf4)

# --- Função para gerar meses e trimestres ---
generate_months_periods <- function(data_verif) {
  data_date <- as.Date(data_verif, format="%Y%m%d")
  
  # Meses individuais
  mnth_seq <- seq(from = as.numeric(format(data_date, "%m")), length.out = 4, by = 1)
  mnth_seq <- ((mnth_seq - 1) %% 12) + 1
  mnth_names <- toupper(month.abb[mnth_seq])
  
  # Trimestres sazonais (iniciais)
  trimestres <- lapply(0:2, function(i) {
    start_month <- ((as.numeric(format(data_date, "%m")) + i - 1) %% 12) + 1
    months_vec <- month.abb[((start_month-1 + 0:2) %% 12) + 1]
    paste0(substr(months_vec,1,1), collapse="")  # iniciais maiúsculas
  })
  
  names(trimestres) <- paste0("seas0", 0:2)
  names(mnth_names) <- paste0("mnth0", 0:3)
  
  list(mnth=mnth_names, seas=trimestres)
}

# --- Parâmetros ---
bases <- c("nmme")#,"copernicus")
calibs <- c("regr")#,"cox")
periods_list <- c(paste0("mnth0",0:3), paste0("seas0",0:2))
data_verif <- "20251201"
model <- "multimodel"

# --- Path figuras ---
base <- "nmme"
version <- ifelse(base=="nmme","v1","v2")
pathfig <- paste0("/dados/mmclima/multimodelo/sazonal/figures/", base, "/", version, "/verification/", calib, "/", model, "/")

# --- Gera nomes dos meses e trimestres ---
periods <- generate_months_periods(data_verif)

# Grade nova
lat <- seq(-88.75, 88.75, by=2.5)
lon <- seq(1.25, 358.75, by=2.5)

# Função para pegar índices correspondentes
get_indices <- function(lat_vec, lon_vec, lat_south, lat_north, lon_west, lon_east) {
  lat_idx <- which(lat_vec >= lat_south & lat_vec <= lat_north)
  
  # Ajuste para longitudes que passam de 360
  lon_mod <- lon_west:lon_east
  lon_mod <- ((lon_mod %% 360) + 360) %% 360  # força dentro de [0,360)
  
  lon_idx <- which(lon_vec >= min(lon_mod) & lon_vec <= max(lon_mod))
  
  return(list(lat_idx = lat_idx, lon_idx = lon_idx))
}

# Definições das regiões na grade antiga (1°)
regioes_old <- list(
  gl = c(-70,70,0,359),
  af = c(-40,40,330,420),
  aa = c(-10,80,65,180),
  au = c(-50,25,110,190),
  eu = c(30,80,330,420),
  an = c(-10,70,190,310),
  pa = c(-30,30,100,290),
  as = c(-60,15,270,330),
  ne = c(20,80,0,359),
  se = c(-80,-20,0,359),
  tr = c(-20,20,0,359),
  am = c(-22,6,278,313)
)

# Calcular índices para todas as regiões
indices_regioes <- lapply(regioes_old, function(x){
  get_indices(lat, lon, lat_south=x[1], lat_north=x[2], lon_west=x[3], lon_east=x[4])
})

# --- Criar grade de lat/lon ---
lat <- seq(-90, 90, 2.5)
lon360 <- seq(1.25, 358.75, 2.5)   # 0–360
lon180 <- ifelse(lon360 > 180, lon360 - 360, lon360)  # -180–180

# --- Definição das regiões (lat_min, lat_max, lon_min, lon_max no formato do mapa) ---
regioes_def <- data.frame(
  reg = c("gl","af","aa","au","eu","an","pa","as","ne","se","tr","am"),
  lat_min = c(-68.75,-38.75,-8.75,-48.75, 31.25,-8.75,-28.75,-58.75, 21.25,-78.75,-18.75,-21.25),
  lat_max = c( 68.75, 38.75,78.75, 23.75, 78.75,68.75, 28.75, 13.75, 78.75,-18.75, 18.75,  6.25),
  lon_min = c(   1.25,330.00, 66.25,111.25,330.00,191.25,105.00,271.25,  1.25,  1.25,  1.25,278.75),
  lon_max = c( 358.75, 58.75,178.75,188.75, 58.75,308.75,285.00,328.75,358.75,358.75,358.75,311.25)
)

# --- Função para achar índices ---
get_idx <- function(lat_min, lat_max, lon_min, lon_max, lon_type=c("360","180")){
  lat_i1 <- which.min(abs(lat - lat_min))
  lat_i2 <- which.min(abs(lat - lat_max))
  if(lon_type=="360"){
    lon_i1 <- which.min(abs(lon360 - lon_min))
    lon_i2 <- which.min(abs(lon360 - lon_max))
    return(c(lat_i1, lat_i2, lon_i1, lon_i2))
  } else {
    lon_i1 <- which.min(abs(lon180 - lon_min))
    lon_i2 <- which.min(abs(lon180 - lon_max))
    return(c(lat_i1, lat_i2, lon_i1, lon_i2))
  }
}

# --- Construir tabela final ---
regioes <- regioes_def
res <- data.frame()

for(i in 1:nrow(regioes_def)){
  r <- regioes_def[i,]
  idx360 <- get_idx(r$lat_min, r$lat_max, r$lon_min, r$lon_max, "360")
  idx180 <- get_idx(r$lat_min, r$lat_max, r$lon_min, r$lon_max, "180")
  res <- rbind(res, data.frame(
    reg = r$reg,
    lat_min = r$lat_min, lat_max = r$lat_max,
    lat_i1 = idx360[1], lat_i2 = idx360[2],
    lon_min_360 = r$lon_min, lon_max_360 = r$lon_max,
    lon_i1_360 = idx360[3], lon_i2_360 = idx360[4],
    lon_min_180 = ifelse(r$lon_min>180, r$lon_min-360, r$lon_min),
    lon_max_180 = ifelse(r$lon_max>180, r$lon_max-360, r$lon_max),
    lon_i1_180 = idx180[3], lon_i2_180 = idx180[4]
  ))
}

print(res)

#########
#REGIÕES#
#########
gl_lat <- c(9, 64);   gl_lon <- c(1, 144)
af_lat <- c(21, 52);  af_lon <- c(132, 24)
aa_lat <- c(33, 68);  aa_lon <- c(27, 72)
au_lat <- c(17, 46);  au_lon <- c(45, 76)
eu_lat <- c(49, 68);  eu_lon <- c(132, 24)
an_lat <- c(33, 64);  an_lon <- c(77, 124)
pa_lat <- c(25, 48);  pa_lon <- c(42, 114)
as_lat <- c(13, 42);  as_lon <- c(109, 132)
ne_lat <- c(45, 68);  ne_lon <- c(1, 144)
se_lat <- c(5, 29);   se_lon <- c(1, 144)
tr_lat <- c(29, 44);  tr_lon <- c(1, 144)
am_lat <- c(28, 39);  am_lon <- c(112, 125)

regions <- list(
  gl = list(lat=gl_lat, lon=gl_lon),
  af = list(lat=af_lat, lon=af_lon),
  aa = list(lat=aa_lat, lon=aa_lon),
  au = list(lat=au_lat, lon=au_lon),
  eu = list(lat=eu_lat, lon=eu_lon),
  an = list(lat=an_lat, lon=an_lon),
  pa = list(lat=pa_lat, lon=pa_lon),
  as = list(lat=as_lat, lon=as_lon),
  ne = list(lat=ne_lat, lon=ne_lon),
  se = list(lat=se_lat, lon=se_lon),
  tr = list(lat=tr_lat, lon=tr_lon),
  am = list(lat=am_lat, lon=am_lon)
)

# --- Loop principal ---
for(calib in calibs){
  for(period in periods_list){
    
    # Determina o mes_title para a figura
    if(grepl("mnth", period)){
      monthissued <- periods$mnth[period]
    } else if(grepl("seas", period)){
      monthissued <- periods$seas[period]
    }
    
    # Monta nomes dos arquivos
    binobstsup_file <- paste0("prec_binobstsup_", period, "_", model, "_calibrated_", calib, "_", data_verif, ".nc")
    binobstinf_file <- paste0("prec_binobstinf_", period, "_", model, "_calibrated_", calib, "_", data_verif, ".nc")
    binobsmed_file <- paste0("prec_binobsmed_", period, "_", model, "_calibrated_", calib, "_", data_verif, ".nc")
    
    probtsup_file <- paste0("prec_probtsup_", period, "_", model, "_calibrated_", calib, "_", data_verif, ".nc")
    probtinf_file <- paste0("prec_probtinf_", period, "_", model, "_calibrated_", calib, "_", data_verif, ".nc")
    probmed_file <- paste0("prec_probmed_", period, "_", model, "_calibrated_", calib, "_", data_verif, ".nc")
    
    if(base == "nmme"){
      path_data <- file.path("/dados/mmclima/multimodelo/sazonal/posproc/nmme/v1/verification", calib, model)
    } else if(base == "copernicus"){
      path_data <- file.path("/dados/mmclima/multimodelo/sazonal/posproc/copernicus/v2/verification", calib, model)
    }

    pathfig <- paste0("/dados/mmclima/multimodelo/sazonal/figures/", base, "/", version, "/verification/", calib, "/", model, "/")

    # --- Abrir arquivos ---
    binobstsup <- nc_open(file.path(path_data, binobstsup_file))
    binobstinf <- nc_open(file.path(path_data, binobstinf_file))
    binobsmed <- nc_open(file.path(path_data, binobsmed_file))
    print(binobstsup)
    #
    binobstsup_data <- ncvar_get(binobstsup, "binobstsup") 
    binobstinf_data <- ncvar_get(binobstinf, "binobstinf") 
    binobsmed_data <- ncvar_get(binobsmed, "binobsmed") 

    probtsup <- nc_open(file.path(path_data, probtsup_file))
    probtinf <- nc_open(file.path(path_data, probtinf_file))
    probmed <- nc_open(file.path(path_data, probmed_file))
    #
    probtsup_data <- ncvar_get(probtsup, "probtsup") 
    probtinf_data <- ncvar_get(probtinf, "probtinf") 
    probmed_data <- ncvar_get(probmed, "probmed") 
    
    # --- Loop sobre regiões usando a lista regions ---
    for(region_name in names(regions)){
      lat_idx <- regions[[region_name]]$lat[1]:regions[[region_name]]$lat[2]
      lon_idx <- regions[[region_name]]$lon[1]:regions[[region_name]]$lon[2]
      # Função para extrair a fatia da região
      extract_region <- function(var, region_name){
        if(length(lon_idx) == 1){
          var[lon_idx, lat_idx, , drop=FALSE]
        } else {
          var[lon_idx, lat_idx, ]
        }
      }
      
      # Loop sobre tipos (tercil inferior, superior, anomalia)
      for(type in c("lowertercile","uppertercile","positiveanom")){
        print(paste("Processando", region_name, type))
        print(type)
        if(type=="lowertercile"){
          binobs_data <- extract_region(binobstinf_data, region_name)
          prob_data   <- extract_region(probtinf_data, region_name)
        } else if(type=="uppertercile"){
          binobs_data <- extract_region(binobstsup_data, region_name)
          prob_data   <- extract_region(probtsup_data, region_name)
        } else if(type=="positiveanom"){
          binobs_data <- extract_region(binobsmed_data, region_name)
          prob_data   <- extract_region(probmed_data, region_name)
        }
        print(lon[lon_idx])
        print(lat[lat_idx])
        print(dim(probmed_data))
        print(dim(prob_data))
        print(dim(binobs_data))

        # # --- ROC diagram ---
        # rainf <- roc.area.eurobrisa(binobs_data, prob_data)$A
        # png(paste0(pathfig, base,"_",model,"_",calib,"_rocdiagram_",type,"_",period,"_",monthissued,"_",region_name,".png"),
        #     width=600, height=600)
        # par(las=1.5, pty='s', cex=1.5, cex.main=1, mar=c(4.5,4,1,0.5))
        # roc.plot(binobs_data, prob_data, 
        #          main=paste("ROC DIAGRAM:", toupper(model), "CALIBRATED (", toupper(calib), ")",
        #                     "REF: GPCP","\nPRECIPITATION -", type, "\nISSUED:", monthissued),
        #          show.thres=F)
        # text(0.7,0.15,paste("ROC AREA =", round(rainf,2)))
        # dev.off()
        

                  # # -------------------------
                  # # Reliability diagram
                  # # -------------------------
                  # # prob e obs já definidos
                  # prob_true, prob_pred = calibration_curve(obs, prob, n_bins=10)

                  # plt.figure(figsize=(5, 5))

                  # # --- Barras cinza (número de ocorrências por bin) ---
                  # bin_counts, _ = np.histogram(prob, bins=np.linspace(0, 1, 11))
                  # bin_width = 0.09
                  # plt.bar(
                  #     prob_pred,
                  #     bin_counts / bin_counts.max(),   # normalizar só p/ visual
                  #     width=bin_width,
                  #     color="gray",
                  #     alpha=0.6
                  # )

                  # # --- Curva de confiabilidade ---
                  # plt.plot(prob_pred, prob_true, color="black", linewidth=2)

                  # # --- Linha da confiabilidade perfeita ---
                  # plt.plot([-0.08, 1.08], [-0.08, 1.08], color="black", linestyle="-")

                  # # --- Eixos e títulos ---
                  # plt.xlabel("FORECAST PROBABILITY")
                  # plt.ylabel("OBSERVED RELATIVE FREQUENCY")

                  # plt.title(
                  #     f"RELIABILITY DIAGRAM: {title1}\n"
                  #     f"{title2}\n"
                  #     f"ISSUED: {month_issued}  VALID FOR {fcst_period}"
                  # )

                  # # Deixar o gráfico mais parecido com o da imagem
                  # plt.xlim(0, 1)
                  # plt.ylim(0, 1)
                  # plt.grid(False)
                  # plt.tight_layout()

                  # out_rel = f"{pathfig}{base}_{model}_{calib}_reliabilitydiagram_{product}_{period}_{month_issued}_{region_name}.png"
                  # plt.savefig(out_rel, dpi=120, bbox_inches="tight")
                  # plt.close()

                  # print("RELIABILITY salvo:", out_rel)
                  # quit()
        print(pathfig)
        quit()
      } # fim tipo
    } # fim region
  } # fim period
} # fim calib



                    # # -------------------------
                    # # Reliability diagram
                    # # -------------------------
                    # # prob e obs já definidos
                    # prob_true, prob_pred = calibration_curve(obs, prob, n_bins=10)

                    # plt.figure(figsize=(5, 5))

                    # # --- Barras cinza (número de ocorrências por bin) ---
                    # bin_counts, _ = np.histogram(prob, bins=np.linspace(0, 1, 11))
                    # bin_width = 0.09
                    # plt.bar(
                    #     prob_pred,
                    #     bin_counts / bin_counts.max(),   # normalizar só p/ visual
                    #     width=bin_width,
                    #     color="gray",
                    #     alpha=0.6
                    # )

                    # # --- Curva de confiabilidade ---
                    # plt.plot(prob_pred, prob_true, color="black", linewidth=2)

                    # # --- Linha da confiabilidade perfeita ---
                    # plt.plot([-0.08, 1.08], [-0.08, 1.08], color="black", linestyle="-")

                    # # --- Eixos e títulos ---
                    # plt.xlabel("FORECAST PROBABILITY")
                    # plt.ylabel("OBSERVED RELATIVE FREQUENCY")

                    # plt.title(
                    #     f"RELIABILITY DIAGRAM: {title1}\n"
                    #     f"{title2}\n"
                    #     f"ISSUED: {month_issued}  VALID FOR {fcst_period}"
                    # )

                    # # Deixar o gráfico mais parecido com o da imagem
                    # plt.xlim(0, 1)
                    # plt.ylim(0, 1)
                    # plt.grid(False)
                    # plt.tight_layout()

                    # out_rel = f"{pathfig}{base}_{model}_{calib}_reliabilitydiagram_{product}_{period}_{month_issued}_{region_name}.png"
                    # plt.savefig(out_rel, dpi=120, bbox_inches="tight")
                    # plt.close()

                    # print("RELIABILITY salvo:", out_rel)
                    # quit()
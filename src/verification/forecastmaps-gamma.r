
forecastmapsgamma<-function(ano,mesatual){

###################################################################
#Inicializa os caminhos de entrada/saída e as extensões utilizadas#
###################################################################

source('/clima2/users/denis/nmme/correlacaoo.r') #Extensão para a função correlação
source('/clima2/users/denis/monitmensal/rclim.txt') #Carrega o pacote Rclim
#source('/clima2/users/denis/monitmensal/rclim1.txt') #Carrega o pacote Rclim
source('/clima2/users/denis/modelo/netcdfreadmask.r') #Extensão para ler netcdf

path_realtime<-"/clima2/users/denis/modelo/realtime/" #Caminho dos arquivos .nc com os dados de precip. das previsões em tempo-real para cada mês
path_hindcast<-"/clima2/users/denis/modelo/hindcast/" #Caminho dos arquivos .nc com os dados de precip. das previsões retrospectivas para cada mês
path_observation<-"/clima2/users/denis/modelo/observation/" #Caminho dos arquivos .nc com os dados de precip. observada para cada mês
pathncfile<-"/clima2/users/denis/modelo/"

#mesatual<-"12" #Se for rodar a mão tem que entrar com a string do mesatual e anoatual
#ano<-"2021"

#######################
#Trimestre de previsão#
#######################

if(mesatual=="01"){trimestre<-"FMA"}
if(mesatual=="02"){trimestre<-"MAM"}
if(mesatual=="03"){trimestre<-"AMJ"}
if(mesatual=="04"){trimestre<-"MJJ"}
if(mesatual=="05"){trimestre<-"JJA"}
if(mesatual=="06"){trimestre<-"JAS"}
if(mesatual=="07"){trimestre<-"ASO"}
if(mesatual=="08"){trimestre<-"SON"}
if(mesatual=="09"){trimestre<-"OND"}
if(mesatual=="10"){trimestre<-"NDJ"}
if(mesatual=="11"){trimestre<-"DJF"}
if(mesatual=="12"){trimestre<-"JFM"}

#################
#Mês de produção#
#################

if(mesatual=="01"){mesprod<-"Jan"}
if(mesatual=="02"){mesprod<-"Fev"}
if(mesatual=="03"){mesprod<-"Mar"}
if(mesatual=="04"){mesprod<-"Abr"}
if(mesatual=="05"){mesprod<-"Mai"}
if(mesatual=="06"){mesprod<-"Jun"}
if(mesatual=="07"){mesprod<-"Jul"}
if(mesatual=="08"){mesprod<-"Ago"}
if(mesatual=="09"){mesprod<-"Set"}
if(mesatual=="10"){mesprod<-"Out"}
if(mesatual=="11"){mesprod<-"Nov"}
if(mesatual=="12"){mesprod<-"Dez"}

if(mesprod=="Jan"){mestitle<-"Jan"}
if(mesprod=="Fev"){mestitle<-"Feb"}
if(mesprod=="Mar"){mestitle<-"Mar"}
if(mesprod=="Abr"){mestitle<-"Apr"}
if(mesprod=="Mai"){mestitle<-"May"}
if(mesprod=="Jun"){mestitle<-"Jun"}
if(mesprod=="Jul"){mestitle<-"Jul"}
if(mesprod=="Ago"){mestitle<-"Aug"}
if(mesprod=="Set"){mestitle<-"Sep"}
if(mesprod=="Out"){mestitle<-"Oct"}
if(mesprod=="Nov"){mestitle<-"Nov"}
if(mesprod=="Dez"){mestitle<-"Dec"}

#############################
#Numero de dias do trimestre#
#############################

if(mesatual=="01"){ndias<-89}
if(mesatual=="02"){ndias<-92}
if(mesatual=="03"){ndias<-91}
if(mesatual=="04"){ndias<-92}
if(mesatual=="05"){ndias<-92}
if(mesatual=="06"){ndias<-92}
if(mesatual=="07"){ndias<-92}
if(mesatual=="08"){ndias<-91}
if(mesatual=="09"){ndias<-92}
if(mesatual=="10"){ndias<-92}
if(mesatual=="11"){ndias<-90}
if(mesatual=="12"){ndias<-90}

###########################################
#Definindo diretório de saída dos produtos#
###########################################

saidaprodutos<-"/clima2/users/denis/modelo/saidaprodutos/"
pathncfile<-paste(saidaprodutos,mesprod,"-",trimestre,"/","previsao/",sep="")

##################################
#Lendo as observações (1982-2010)#
##################################

caminho_observation<-paste(path_observation,mesprod,"-",trimestre,"/","CPC-CMAP-",trimestre,"-1982-2010.nc",sep="")
obs<-netcdfread(caminho_observation,"X","Y","T","prate") #Os dados estarão armazenados em uma array com três dimensões: latitude, longitude e tempo (1982-2010)
obs$data<-obs$data*ndias  #Multiplica pelo número de dias do trimestre pra ir de mm/day pra mm/trimestre

if(mesatual=="12"){
obs$data<-obs$data[,,2:29] #Os dados de observação variam seu tamanho na dimensão do Tempo (para o mês 12 são 28 meses)
}

dimensao<-dim(obs$data) 
obstempo<-dimensao[3]


#####################################################################################
#Lendo a previsão em tempo-real (realtime) para cada modelo do NMME  individualmente#
#####################################################################################

## Usado para o arquivo .grb
##temporeal<-paste(ano,mesatual,"0800.",sep="") #definindo o nome dos arquivos de dados
temporeal2<-paste(ano,mesatual,sep="")

cfsv2_caminho<-paste(path_realtime,"CFSv2/","CFSv2.prate.",temporeal2,".ENSMEAN.fcst.nc",sep="") #Lê o arquivo .nc que foi baixado diretamente do ftp (a partir de abril 2018)
cfsv2_realtime<-netcdfread(cfsv2_caminho,"lon","lat","target","fcst")
cfsv2_realtime$data<-cfsv2_realtime$data[,,2:(dim(cfsv2_realtime$data)[3])]

cancm4i_caminho<-paste(path_realtime,"CanCM4i/","CanCM4i.prate.",temporeal2,".ENSMEAN.fcst.nc",sep="") #Lê o arquivo .nc que foi transformado a partir do arquivo .grb
#netcdfinfo(cancm4i_caminho)
cancm4i_realtime<-netcdfread(cancm4i_caminho,"lon","lat","target","fcst")
cancm4i_realtime$data<-cancm4i_realtime$data[,,2:(dim(cancm4i_realtime$data)[3])]

#gem5nemo_caminho<-paste(path_realtime,"GEM5_NEMO/","GEM5_NEMO.prate.",temporeal2,".ENSMEAN.fcst.nc",sep="") #Lê o arquivo .nc que foi transformado a partir do arquivo .grb
##netcdfinfo(gem5nemo_caminho)
#gem5nemo_realtime<-netcdfread(gem5nemo_caminho,"lon","lat","target","fcst")
#gem5nemo_realtime$data<-gem5nemo_realtime$data[,,2:(dim(gem5nemo_realtime$data)[3])]

#gfdlspear_caminho<-paste(path_realtime,"GFDL_SPEAR/","GFDL_SPEAR.prate.",temporeal2,".ENSMEAN.fcst.nc",sep="") #Lê o arquivo .nc que foi transformado a partir do arquivo .grb
#netcdfinfo(gfdlspear_caminho)
#gfdlspear_realtime<-netcdfread(gfdlspear_caminho,"lon","lat","target","fcst")
#gfdlspear_realtime$data<-gfdlspear_realtime$data[,,2:(dim(gfdlspear_realtime$data)[3])]

ccsm4_caminho<-paste(path_realtime,"NCAR_CCSM4/","NCAR_CCSM4.prate.",temporeal2,".ENSMEAN.fcst.nc",sep="") #Lê o arquivo .nc que foi transformado a partir do arquivo .grb
ccsm4_realtime<-netcdfread(ccsm4_caminho,"lon","lat","target","fcst")
ccsm4_realtime$data<-ccsm4_realtime$data[,,2:(dim(ccsm4_realtime$data)[3])]

nasa_geos5v2_caminho<-paste(path_realtime,"NASA_GEOS5v2/","NASA_GEOS5v2.prate.",temporeal2,".ENSMEAN.fcst.nc",sep="") #Este modelo foi implementado em Fevereiro de 2018
nasa_geos5v2_realtime<-netcdfread(nasa_geos5v2_caminho,"lon","lat","target","fcst") 
nasa_geos5v2_realtime$data<-nasa_geos5v2_realtime$data[,,2:(dim(nasa_geos5v2_realtime$data)[3])]


#################
#Modelos antigos#
#################
## Usado para o arquivo .grb
##ccsm4_caminho<-paste(path_realtime,"NCAR_CCSM4/","prate.",temporeal,"NCAR_CCSM4.ensmean.fcst.1x1.nc",sep="") #Lê o arquivo .nc que foi transformado a partir do arquivo .grb
##ccsm4_realtime<-netcdfread(ccsm4_caminho,"lon","lat","time","var59")

#nasa_gmao_caminho<-paste(path_realtime,"NASA/","prate.",temporeal,"NASA.ensmean.fcst.1x1.nc",sep="") #Este modelo esteve no NMME até Fevereiro de 2018
#nasa_gmao_realtime<-netcdfread(nasa_gmao_caminho,"lon","lat","time","var59")

#cesm_caminho<-paste(path_realtime,"NCAR_CESM/","prate.",temporeal,"NCAR_CESM.ensmean.fcst.1x1.nc",sep="") #Este modelo esteve no NMME apenas entre junho de 2016 e março de 2017
#cesm_realtime<-netcdfread(cesm_caminho,"lon","lat","time","var59")

#cmc1_caminho<-paste(path_realtime,"CMC1/","prate.",temporeal,"CMC1.ensmean.fcst.1x1.nc",sep="") #Lê o arquivo .nc que foi transformado a partir do arquivo .grb
#cmc1_realtime<-netcdfread(cmc1_caminho,"lon","lat","time","var59")

#cmc2_caminho<-paste(path_realtime,"CMC2/","prate.",temporeal,"CMC2.ensmean.fcst.1x1.nc",sep="") #Lê o arquivo .nc que foi transformado a partir do arquivo .grb
#cmc2_realtime<-netcdfread(cmc2_caminho,"lon","lat","time","var59")

#gfdl_caminho<-paste(path_realtime,"GFDL/","GFDL.prate.",temporeal2,".ENSMEAN.fcst.nc",sep="") #Lê o arquivo .nc que foi transformado a partir do arquivo .grb
#gfdl_realtime<-netcdfread(gfdl_caminho,"lon","lat","target","fcst")
#gfdl_realtime$data<-gfdl_realtime$data[,,2:(dim(gfdl_realtime$data)[3])]

#flor_caminho<-paste(path_realtime,"GFDL_FLOR/","GFDL_FLOR.prate.",temporeal2,".ENSMEAN.fcst.nc",sep="") #Lê o arquivo .nc que foi transformado a partir do arquivo .grb
#flor_realtime<-netcdfread(flor_caminho,"lon","lat","target","fcst")
#flor_realtime$data<-flor_realtime$data[,,2:(dim(flor_realtime$data)[3])]


######################################################################################
#Calculando a média (multi-modelo) das previsões em tempo-real - agrupando o ensemble#
######################################################################################

media_multi_realtime<-array(NA, dim=c(360,181,4))
for (i in 1:4){
media_multi_realtime[,,i]<-(cfsv2_realtime$data[,,i]+cancm4i_realtime$data[,,i]+ #Calculando a média de todos os modelos conjuntamente 
ccsm4_realtime$data[,,i]+nasa_geos5v2_realtime$data[,,i])/4
} 

realtimemean<-apply(media_multi_realtime[,,1:3]*86400,c(1,2),mean) #Faz a média dos 3 primeiros meses previstos *86400 (segundos por dia) para transformar em mm/day
realtimemean<-realtimemean*ndias #Multiplica pelo numero de dias do trimestre para obter o valor da chuva prevista para o trimestre em cada um dos pontos de grade


#########################################################################################
#Lendo as previsões retrospectivas (hindcasts) para cada modelo do NMME individualmente #
#########################################################################################

caminho_cfsv2<-paste(path_hindcast,"CFSv2/",mesprod,"-",trimestre,"/","NCEP-CFSv2-precip-hind-ens-mean-ic-",mesprod,"-",trimestre,"-1982.2010.nc",sep="")
cfsv2_hindcast<-netcdfread(caminho_cfsv2,"X","Y","S","prec")

caminho_cancm4i<-paste(path_hindcast,"CanCM4i/",mesprod,"-",trimestre,"/","CanCM4i-precip-hind-ens-mean-ic-",mesprod,"-",trimestre,"-1982-2010.nc",sep="")
cancm4i_hindcast<-netcdfread(caminho_cancm4i,"X","Y","S","prec")

#caminho_gem5nemo<-paste(path_hindcast,"GEM5_NEMO/",mesprod,"-",trimestre,"/","GEM5_NEMO-precip-hind-ens-mean-ic-",mesprod,"-",trimestre,"-1982-2010.nc",sep="")
#gem5nemo_hindcast<-netcdfread(caminho_gem5nemo,"X","Y","S","prec")

#caminho_gfdlspear<-paste(path_hindcast,"GFDL_SPEAR/",mesprod,"-",trimestre,"/","GFDL_SPEAR-precip-hind-ens-mean-ic-",mesprod,"-",trimestre,"-1982-2010.nc",sep="")
#gfdlspear_hindcast<-netcdfread(caminho_gfdlspear,"X","Y","S","prec")

caminho_ccsm4<-paste(path_hindcast,"COLA-CCSM4/",mesprod,"-",trimestre,"/","NCAR-CCSM4-precip-hind-ens-mean-ic-",mesprod,"-",trimestre,"-1982-2010.nc",sep="")
ccsm4_hindcast<-netcdfread(caminho_ccsm4,"X","Y","S","prec")

caminho_nasa_geos5v2<-paste(path_hindcast,"NASA_GEOS5v2/",mesprod,"-",trimestre,"/","NASA_GEOS5v2-precip-hind-ens-mean-ic-",mesprod,"-",trimestre,"-1982-2010.nc",sep="")
nasa_geos5v2_hindcast<-netcdfread(caminho_nasa_geos5v2,"X","Y","S","prec")

#################
#Modelos antigos#
#################
#caminho_gmao<-paste(path_hindcast,"NASA_GMAO/",mesprod,"-",trimestre,"/","NASA-GMAO-062012-precip-hind-ens-mean-ic-",mesprod,"-",trimestre,"-1982-2010.nc",sep="")
#gmao_hindcast<-netcdfread(caminho_gmao,"X","Y","S","prec") #MODELO NASA GMAO - RETIRADO DO NMME A PARTIR DE FEVEREIRO 2018

#caminho_cesm<-paste(path_hindcast,"NCAR_CESM/",mesprod,"-",trimestre,"/","NCAR-CESM-precip-hind-ens-mean-ic-",mesprod,"-",trimestre,"-1982-2010.nc",sep="")
#cesm_hindcast<-netcdfread(caminho_cesm,"X","Y","S","prec") #MODELO RETIRADO DO NMME A PARTIR DE ABRIL DE 2017

#caminho_cmc1<-paste(path_hindcast,"CMC1/",mesprod,"-",trimestre,"/","CMC1-CanCM3-precip-hind-ens-mean-ic-",mesprod,"-",trimestre,"-1982-2010.nc",sep="")
#cmc1_hindcast<-netcdfread(caminho_cmc1,"X","Y","S","prec")

#caminho_cmc2<-paste(path_hindcast,"CMC2/",mesprod,"-",trimestre,"/","CMC2-CanCM4-precip-hind-ens-mean-ic-",mesprod,"-",trimestre,"-1982-2010.nc",sep="")
#cmc2_hindcast<-netcdfread(caminho_cmc2,"X","Y","S","prec")

#caminho_gfdl<-paste(path_hindcast,"GFDL/",mesprod,"-",trimestre,"/","GFDL-CM2p1-aer04-precip-hind-ens-mean-ic-",mesprod,"-",trimestre,"-1982-2010.nc",sep="")
#gfdl_hindcast<-netcdfread(caminho_gfdl,"X","Y","S","prec")

#caminho_flora<-paste(path_hindcast,"GFDL_FLOR/",mesprod,"-",trimestre,"/","GFDL-CM2p5-FLOR-A06-precip-hind-ens-mean-ic-",mesprod,"-",trimestre,"-1982-2010.nc",sep="")
#flora_hindcast<-netcdfread(caminho_flora,"X","Y","S","prec")
#caminho_florb<-paste(path_hindcast,"GFDL_FLOR/",mesprod,"-",trimestre,"/","GFDL-CM2p5-FLOR-B01-precip-hind-ens-mean-ic-",mesprod,"-",trimestre,"-1982-2010.nc",sep="")
#florb_hindcast<-netcdfread(caminho_florb,"X","Y","S","prec")
#flor_hindcast<-(flora_hindcast$data[,,]+florb_hindcast$data[,,])/2 #No caso do modelo FLOR, os hindcasts são a média de dois modelos: flor-a e flor-b


if(mesatual=="11"){ #Como para o mês de novembro e dezembro a série das observações tem 27 anos, retira-se dois tempos das previsões
#cmc1_hindcast$data<-cmc1_hindcast$data[,,2:28]
#cmc2_hindcast$data<-cmc2_hindcast$data[,,2:28]
#gfdl_hindcast$data<-gfdl_hindcast$data[,,2:28]
#gmao_hindcast$data<-gmao_hindcast$data[,,2:28]
#flor_hindcast<-flor_hindcast[,,2:28]
cfsv2_hindcast$data<-cfsv2_hindcast$data[,,2:28]
ccsm4_hindcast$data<-ccsm4_hindcast$data[,,2:28]
nasa_geos5v2_hindcast$data<-nasa_geos5v2_hindcast$data[,,2:28]
cancm4i_hindcast$data<-cancm4i_hindcast$data[,,2:28]}
#gem5nemo_hindcast$data<-gem5nemo_hindcast$data[,,2:28]}
#gfdlspear_hindcast$data<-gfdlspear_hindcast$data[,,2:18]}

if(mesatual=="12"){
#cmc1_hindcast$data<-cmc1_hindcast$data[,,1:28]
#cmc2_hindcast$data<-cmc2_hindcast$data[,,1:28]
#gfdl_hindcast$data<-gfdl_hindcast$data[,,1:28]
#gmao_hindcast$data<-gmao_hindcast$data[,,1:28]
#flor_hindcast<-flor_hindcast[,,1:28]
cfsv2_hindcast$data<-cfsv2_hindcast$data[,,1:28]
ccsm4_hindcast$data<-ccsm4_hindcast$data[,,1:28]
nasa_geos5v2_hindcast$data<-nasa_geos5v2_hindcast$data[,,1:28]
cancm4i_hindcast$data<-cancm4i_hindcast$data[,,1:28]}
#gem5nemo_hindcast$data<-gem5nemo_hindcast$data[,,1:28]}
#gfdlspear_hindcast$data<-gfdlspear_hindcast$data[,,1:18]}


#################################################
#Calculando a média (multi-modelo) dos hindcasts#
#################################################

mediahindcast<-array(NA, dim=c(360,181,obstempo))
for (i in 1:obstempo){
mediahindcast[,,i]<-(cfsv2_hindcast$data[,,i]+cancm4i_hindcast$data[,,i]+ #Para calcular a média: a soma de todos os modelos/
ccsm4_hindcast$data[,,i]+nasa_geos5v2_hindcast$data[,,i])/4 #dividindo por n (número de modelos)
}

mediahindcast<-mediahindcast*ndias #Faz a conversão da precipitação em mm/mês para mm/trimestre

hindcastmean<-apply(mediahindcast[,,1:obstempo],c(1,2),mean,na.rm=TRUE) 


##################################################
#Calculando anomalia (multi-modelo) dos hindcasts#
##################################################

hindcastanomaly<-array(NA, dim=c(360,181,obstempo))
for (i in 1:obstempo){
hindcastanomaly[,,i]<-(mediahindcast[,,i])-(hindcastmean)
}

#hindcastanomaly[hindcastanomaly == Inf]<-NA
#hindcastanomaly[hindcastanomaly == -Inf]<-NA


#############################################################################
#Calculando climatologia (média de todos os anos) e anomalia das observações#
#############################################################################

obsmean<-apply(obs$data[,,1:obstempo],c(1,2),mean,na.rm=TRUE)
obsmedian<-apply(obs$data[,,1:obstempo],c(1,2),median,na.rm=TRUE)
obsanomaly<-array(NA, dim=c(360,181,obstempo))
for (i in 1:obstempo){
obsanomaly[,,i]<-(obs$data[,,i])-(obsmean)}

obsanomaly[obsanomaly == Inf]<-NA
obsanomaly[obsanomaly == -Inf]<-NA

stdevobs<-obs$data*NA
n<-dim(obs$data)[3]

stdevobs<-sqrt(applyfield(obs$data[,,1:obstempo], var)*(n-1)/(n)) #Desvio padrão da série observada para cada ponto de grade

###################################################################
#Calculando correlacao entre anomalia dos hindcasts e observacoes #
###################################################################

multimodelcor<-cortwo3dsst(obsanomaly[,,1:obstempo],hindcastanomaly[,,1:obstempo])
multimodelcor$cor[multimodelcor$cor == -999.99] <- NA
multimodelcor$cor[multimodelcor$cor<0]<-0

#multimodelcor$cor[multimodelcor$cor<=0]<-0
#plotmap(obs$lon,obs$lat,multimodelcor$cor)


#############################################################################################################################
#                                                                                                                           #
#Após a leitura das observações e das previsões do multi-modelo, bem como o cálculo das médias e do desvio padrão,          #
#                                                                                                                           #
#A partir daqui inicia o procedimento estatístico para a calibração das previsões climáticas, utilizando o método Gamma     #
#                                                                                                                           #
#de transformação da distribuição, para a remoção de viés das previsões.                                                    #
#                                                                                                                           #
#############################################################################################################################

###########################################################
#ARRAYS UTILIZADAS PARA ARMAZENAR O RESULTADO DOS CÁLCULOS#
###########################################################

########################################################################
#Uma array é uma matriz de três dimensões. Neste caso: lat, lon e tempo#
########################################################################
alpha_hind<-mediahindcast[,,1]*NA
beta_hind<-mediahindcast[,,1]*NA
alpha_obs<-mediahindcast[,,1]*NA
beta_obs<-mediahindcast[,,1]*NA
beta<-mediahindcast[,,1]*NA
alpha<-mediahindcast[,,1]*NA
correlacao<-mediahindcast[,,1]*NA
correlacaomm<-mediahindcast[,,1]*NA
media2<-mediahindcast[,,1]*NA
media3<-mediahindcast[,,1]*NA
desviopadrao2<-mediahindcast[,,1]*NA
desviopadrao3<-mediahindcast[,,1]*NA
alpha2<-mediahindcast[,,1]*NA
beta2<-mediahindcast[,,1]*NA
alpha3<-mediahindcast[,,1]*NA
beta3<-mediahindcast[,,1]*NA
above<-mediahindcast[,,1]*NA
below<-mediahindcast[,,1]*NA
normal<-mediahindcast[,,1]*NA
anomprevmm<-mediahindcast[,,1]*NA


########################################

lat<-seq(-90,90)
lon<-seq( 0,359)

########################################


######################################################
#LOOP (EM CADA PONTO DE GRADE DE LONGITUDE E LATITUDE#
######################################################
for(i in 1:360){ #Lon
for(j in 1:181){ #Lat


################################################################
#Calcular os parâmetros Alpha e Beta da série dos hindcasts (X)#
################################################################
alpha_hind[i,j]<-mean(mediahindcast[i,j,])^2/(var(mediahindcast[i,j,])*(n-1)/(n))
beta_hind[i,j]<-(var(mediahindcast[i,j,])*(n-1)/(n))/mean(mediahindcast[i,j,])


#########################################################
#Calcular Alpha e Beta da série dos dados observados (Y)#
#########################################################
alpha_obs[i,j]<-mean(obs$data[i,j,1:obstempo])^2/(var(obs$data[i,j,1:obstempo])*(n-1)/(n))
beta_obs[i,j]<-(var(obs$data[i,j,1:obstempo])*(n-1)/(n))/mean(obs$data[i,j,1:obstempo])
}}

for(i in 1:360){
for(j in 1:181){

###################################################################
#      Ajustar distribuição gamma à série dos hindcasts (X)       #
#Mapear cada valor de X na distribuição padronizada - normal (0,1)#
###################################################################
serie_hind<-mediahindcast[i,j,1:obstempo] #Série dos hindcasts do multimodelo
gamma_seriehind<-pgamma(serie_hind,shape=alpha_hind[i,j],scale=beta_hind[i,j]) #Gera a distribuição Gamma de prob. para a série dos hindcasts
spi_hind<-qnorm(gamma_seriehind,mean=0,sd=1) #Série de valores x'#

###################################################################
#     Ajustar uma distribuição gamma aos dados observados (Y)     #
#Mapear cada valor de Y na distribuição padronizada - normal (0,1)#
###################################################################
serie_obs<-obs$data[i,j,1:obstempo] #Série dos dados observados
gamma_serieobs<-pgamma(serie_obs,shape=alpha_obs[i,j],scale=beta_obs[i,j])#Gera a distribuição Gamma de prob. para a série das observações
spi_obs<-qnorm(gamma_serieobs,mean=0,sd=1)

#####################################################################
#Usar as novas séries de dados transformados p/ estimar alpha e beta#
#####################################################################
correlacao[i,j]<-cor(spi_hind,spi_obs) #Correlação das séries padronizadas de hindcast e obs.
correlacao[i,j][correlacao[i,j]<0]<-0


se<-sqrt(var(spi_obs)*(length(spi_obs)-1)/(length(spi_obs)))*sqrt(1-((correlacao[i,j])^2)) 
beta[i,j]<-(correlacao[i,j])*(sqrt(var(spi_obs)*(length(spi_obs)-1)/(length(spi_obs)))/sqrt(var(spi_hind)*(length(spi_hind)-1)/(length(spi_hind))))

alpha[i,j]<-(mean(spi_obs,na.rm=T))-(beta[i,j]*mean(spi_hind,na.rm=T))


######################################################
#Dada uma nova previsão futura p/ algum ano após 2010#
#transformar o valor de x para x' via gamma->N(0,1)  #
#Usando o valor padronizado da previsão futura       #
#para calcular a previsão do valor médio y'e estimar #
#o valor do desvio padrão previsto Se                #
######################################################

#########################################
#selecionar valor da previsão (hindcast)#
#########################################
xprevisao<-realtimemean[i,j]  #Valor da previsão real-time da chuva em milímetros
xp<-pgamma(xprevisao,shape=alpha_hind[i,j],scale=beta_hind[i,j])
xlinhaprevisao<-qnorm(xp,mean=0,sd=1) #Valor padronizado da previsão n 

ylinhamedio<-alpha[i,j]+(beta[i,j]*xlinhaprevisao) #A1 Valor médio - padronizado - de Y' (média obs. padronizada)

seprevisto<-sqrt(var(spi_obs)*(length(spi_obs)-1)/(length(spi_obs)))*sqrt(1-((correlacao[i,j])^2)) #Cálculo do desvio padrão previsto

#########################################
##MÉTODO GAMMA: Cálculo do alpha e beta##
######para gerar a gamma prevista########
#########################################
media2[i,j]<-((ylinhamedio)*stdevobs[i,j])+obsmean[i,j] #Cálculo da Média prevista em milímetros
media2[i,j][media2[i,j]==Inf]<-NA
media2[i,j][media2[i,j]==-Inf]<-NA
#media2[i,j][media2[i,j]<0]<-0.1

anomprevmm[i,j]<-(ylinhamedio)*stdevobs[i,j] #Cálculo da anomalia prevista
anomprevmm[i,j][anomprevmm[i,j]==Inf]<-NA
anomprevmm[i,j][anomprevmm[i,j]==-Inf]<-NA

correlacaomm[i,j]<-cor(serie_hind,serie_obs)
correlacaomm[i,j][correlacaomm[i,j]<0]<-0

desviopadrao2[i,j]<-(stdevobs[i,j])*sqrt(1-((correlacao[i,j])^2)) #Cálculo da Variância em milímetros

alpha2[i,j]<-((media2[i,j])^2)/(desviopadrao2[i,j]^2) #Estimativa dos valores de alpha da distribuição gamma prevista
beta2[i,j]<-(desviopadrao2[i,j]^2)/media2[i,j] #Estimativa dos valores de beta da gamma prevista

}}



##################################################################################################################
#Após o cálculo da média prevista, anomalia prevista e estimativa dos parâmetros alpha e beta da gamma prevista, #
#                                                                                                                #
#são calculadas as probabilidades da precipitação prevista para diferentes eventos.                              #
#                                                                                                                #
##################################################################################################################


##########################################################################
# Compute forecast probabilities for below, normal and above categories  #
##########################################################################

tercilinferior<-mediahindcast[,,1]*NA
tercilsuperior<-mediahindcast[,,1]*NA
quintil20<-mediahindcast[,,1]*NA
quintil80<-mediahindcast[,,1]*NA
prob20<-mediahindcast[,,1]*NA
prob80<-mediahindcast[,,1]*NA
abovemean<-mediahindcast[,,1]*NA

for(i in 1:360){
for(j in 1:181){
tercilinferior[i,j]<-quantile(obs$data[i,j,],probs=1/3) #Faz o cálculo do tercil inferior da série observada
tercilsuperior[i,j]<-quantile(obs$data[i,j,],probs=2/3) #Faz o cálculo do tercil superior da série observada
quintil20[i,j]<-quantile(obs$data[i,j,],probs=1/5) #Faz o cálculo do quintil inferior da série observada
quintil80[i,j]<-quantile(obs$data[i,j,],probs=4/5) #Faz o cálculo do quintil superior da série observada
}
}  

#####################################################################################################
#Calcula as probabilidades da preciptação prevista estar acima/abaixo da faixa normal climatológica##
#####################################################################################################

for(i in 1:360){
for(j in 1:181){
below[i,j]<-pgamma(tercilinferior[i,j],shape=alpha2[i,j],scale=beta2[i,j]) #Calcula a probabilidade da chuva prevista estar abaixo do tercil inferior
above[i,j]<-(1-pgamma(tercilsuperior[i,j],shape=alpha2[i,j],scale=beta2[i,j])) #Probabilidade da chuva prevista estar acima do tercil superior
normal[i,j]<-(1-below[i,j]-above[i,j]) #Probabilidade da chuva prevista estar dentro da faixa normal
prob20[i,j]<-pgamma(quintil20[i,j],shape=alpha2[i,j],scale=beta2[i,j]) #Calcula a probabilidade da chuva prevista estar abaixo do quintil inferior
prob80[i,j]<-1-pgamma(quintil80[i,j],shape=alpha2[i,j],scale=beta2[i,j]) #Calcula a probabilidade da chuva prevista estar acima do quintil superior
abovemean[i,j]<-1-pgamma(obsmean[i,j],shape=alpha2[i,j],scale=beta2[i,j]) #Calcula a probabilidade da chuva prevista estar acima ou abaixo da normal(média) climatológica 
}
} 

#############################################################################################
#Gera arquivos netcdf com os valores de prec. prevista que tem 80% 20% e 50% de ocorrência ##
#############################################################################################

precip80<-qgamma(0.8,shape=alpha2,scale=beta2) #Precip. that have 80% chance of occurrence
precip20<-qgamma(0.2,shape=alpha2,scale=beta2) #Precip. that have 20% chance of occurrence
precip50<-qgamma(0.5,shape=alpha2,scale=beta2) #Precip. that have 50% chance of occurrence

#A partir dos arquivos gerados são gerados mapas no grads
mask<-netcdfreadmask(paste("/clima2/users/denis/modelo/","land-sea-mask-nmme.nc",sep=""),"X","Y","land") #Carrega a máscara p/ escrever somente dados sobre o continente
aux<-precip80
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-precip80-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99)

aux<-precip20
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-precip20-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99)

aux<-precip50
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-precip50-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99)

############################################################################################################
#Gera arquivos netcdf com as probabilidades de ocorrência de determinados valores em mm de prec. prevista ##
############################################################################################################

prob10<-1-pgamma(10,shape=alpha2,scale=beta2) #Calculate probability (chance) of at least 10 mm
prob20<-1-pgamma(20,shape=alpha2,scale=beta2) #Calculate probability (chance) of at least 20 mm
prob40<-1-pgamma(40,shape=alpha2,scale=beta2) #Calculate probability (chance) of at least 40 mm
prob60<-1-pgamma(60,shape=alpha2,scale=beta2) #Calculate probability (chance) of at least 60 mm
prob80<-1-pgamma(80,shape=alpha2,scale=beta2) #Calculate probability (chance) of at least 80 mm
prob100<-1-pgamma(100,shape=alpha2,scale=beta2) #Calculate probability (chance) of at least 100 mm
prob150<-1-pgamma(150,shape=alpha2,scale=beta2) #Calculate probability (chance) of at least 150 mm
prob200<-1-pgamma(200,shape=alpha2,scale=beta2) #Calculate probability (chance) of at least 200 mm
prob250<-1-pgamma(250,shape=alpha2,scale=beta2) #Calculate probability (chance) of at least 250 mm
prob300<-1-pgamma(300,shape=alpha2,scale=beta2) #Calculate probability (chance) of at least 300 mm
prob400<-1-pgamma(400,shape=alpha2,scale=beta2) #Calculate probability (chance) of at least 400 mm
prob500<-1-pgamma(500,shape=alpha2,scale=beta2) #Calculate probability (chance) of at least 500 mm
prob600<-1-pgamma(600,shape=alpha2,scale=beta2) #Calculate probability (chance) of at least 600 mm

mask<-netcdfreadmask(paste("/clima2/users/denis/modelo/","land-sea-mask-nmme.nc",sep=""),"X","Y","land") #Carrega a máscara p/ escrever somente dados sobre o continente
aux<-prob10*100
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-prob10-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99) #Escreve o arquivo netcdf com as probabilidades

aux<-prob20*100
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-prob20-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99)

aux<-prob40*100
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-prob40-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99)

aux<-prob60*100
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-prob60-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99)

aux<-prob80*100
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-prob80-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99)

aux<-prob100*100
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-prob100-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99)

aux<-prob150*100
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-prob150-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99)

aux<-prob200*100
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-prob200-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99)

aux<-prob250*100
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-prob250-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99)

aux<-prob300*100
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-prob300-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99)

aux<-prob400*100
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-prob400-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99)

aux<-prob500*100
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-prob500-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99)

aux<-prob600*100
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-prob600-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99)

#}
########################################################################
#Escrever probabilidades de ocorrência para os tercis, quintis e média##
########################################################################

mask<-netcdfreadmask(paste("/clima2/users/denis/modelo/","land-sea-mask-nmme.nc",sep=""),"X","Y","land")
aux<-below*100
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-problowertercile-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99) #prob. de ocorrência abaixo do tercil inferior

aux<-above*100
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-probuppertercile-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99) #prob. de ocorrência acima do tercil superior

aux<-prob20*100
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-problowerquintile-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99) #prob. de ocorrência abaixo do quintil inferior

aux<-prob80*100
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-probupperquintile-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99) #prob. de ocorrência acima do quintil superior

aux<-abovemean*100
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-probmean-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99) #prob. de ocorrência acima/abaixo da média climatológica


#############################################
#Escrever anomalia de precipitação prevista##
#############################################
anomprevmm<-anomprevmm*ndias
aux<-anomprevmm
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-anomalia-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99)


########################################################################################################################################
# Compute probability of most likely tercile (calcula a probabilidade dos tercis mais prováveis de ocorrência para cada ponto de grade)#
########################################################################################################################################

mlc<-normal*NA
probmlc<-normal*NA

for (i in 1:360){
      for(j in 1:181){
         if(is.na(obs$data[i,j,1])){
  	      mlc[i,j]<-NA
	      probmlc[i,j]<-NA    
	      }
	      else{
              mlc[i,j]<-order(c(below[i,j],normal[i,j],above[i,j]))[3]
	      if (mlc[i,j]==3){probmlc[i,j]<-c(below[i,j],normal[i,j],above[i,j])[mlc[i,j]]}
	      if (mlc[i,j]==1){probmlc[i,j]<--c(below[i,j],normal[i,j],above[i,j])[mlc[i,j]]}
	      if (mlc[i,j]==2){probmlc[i,j]<-0}
	      }
      }
}
#plotmap(lon,lat,probmlc*100)

#######################################################################################################
# Cria os arquivos netcdf com as probabilidades dos tercis mais prováveis para gerar os mapas no grads#
#######################################################################################################
lat<-seq(-90,90)
lon<-seq( 0,359)

#Create probmlc files
probmlc[is.na(probmlc)] <- 0
netcdfwrite(lon,lat,probmlc*100,paste(pathncfile,"gamma-probmlc-nmme-",trimestre,"-",ano,".nc",sep=""),mv=-999.99)

#Mask
mask<-netcdfreadmask(paste("/clima2/users/denis/modelo/","land-sea-mask-nmme.nc",sep=""),"X","Y","land")
aux<-probmlc*100
maskc<-t(apply(mask$data, 1, rev))
aux[maskc==0]<-NA
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-probmlc-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99)

#if(mesatual!="12"){
#probmlc[is.na(probmlc)] <- 0
#netcdfwrite(lon,lat,probmlc*100,paste(pathncfile,"gamma-probmlc-nmme-",trimestre,"-",ano,".nc",sep=""),mv=-999.99)

##Mask
#mask<-netcdfreadmask(paste("/clima2/users/denis/modelo/","land-sea-mask-nmme.nc",sep=""),"X","Y","land")
#aux<-probmlc*100
#maskc<-t(apply(mask$data, 1, rev))
#aux[maskc==0]<-NA
#aux[is.na(aux)] <- -999.99
#netcdfwrite(lon,lat,aux,paste(pathncfile,"gamma-probmlc-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99)
#}


#####################################################################################################
#Aqui são calculadas as anomalias da chuva prevista para cada modelo do conjunto NMME separadamente #
#                                                                                                   #
#A partir dos arquivos .nc com as anomalias são gerados mapas no grads                              #
#                                                                                                   #
#e comparados com os mapas da anomalia para cada modelo, disponibilizados no site do NMME           #
#                                                                                                   #
#####################################################################################################

lat<-seq(-90,90)
lon<-seq( 0,359)

#######
#CFSV2#
#######
realtimemean1<-apply(cfsv2_realtime$data[,,1:3]*86400,c(1,2),mean)
hindcastmean1<-apply(cfsv2_hindcast$data[,,1:obstempo],c(1,2),mean)
hindcastanomaly_cfsv2<-array(NA, dim=c(360,181,1))
hindcastanomaly_cfsv2<-((realtimemean1)-(hindcastmean1)) #chuva prevista - chuva prevista em retrospectiva
#plotmap(lon,lat,hindcastanomaly_cfsv2)
aux<-hindcastanomaly_cfsv2
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"cfsv2-anomaly-",trimestre,"-",ano,".nc",sep=""),mv=-999.99)

############
#NCAR_CCSM4#
############
realtimemean4<-apply(ccsm4_realtime$data[,,1:3]*86400,c(1,2),mean)
hindcastmean4<-apply(ccsm4_hindcast$data[,,1:obstempo],c(1,2),mean)
hindcastanomaly_ccsm4<-array(NA, dim=c(360,181,1))
hindcastanomaly_ccsm4<-((realtimemean4)-(hindcastmean4)) #
#plotmap(lon,lat,hindcastanomaly_ccsm4)
aux<-hindcastanomaly_ccsm4
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"ccsm4-anomaly-",trimestre,"-",ano,".nc",sep=""),mv=-999.99)

################
#NASA_GEOS5 v.2#
################
realtimemean5<-apply(nasa_geos5v2_realtime$data[,,1:3]*86400,c(1,2),mean)
hindcastmean5<-apply(nasa_geos5v2_hindcast$data[,,1:obstempo],c(1,2),mean)
hindcastanomaly_nasa<-array(NA, dim=c(360,181,1))
hindcastanomaly_nasa<-((realtimemean5)-(hindcastmean5)) #
##plotmap(lon,lat,hindcastanomaly_nasa)
aux<-hindcastanomaly_nasa
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"nasa-anomaly-",trimestre,"-",ano,".nc",sep=""),mv=-999.99)

#########
#CanCM4i#
#########
realtimemean6<-apply(cancm4i_realtime$data[,,1:3]*86400,c(1,2),mean)
hindcastmean6<-apply(cancm4i_hindcast$data[,,1:obstempo],c(1,2),mean)
hindcastanomaly_cancm4i<-array(NA, dim=c(360,181,1))
hindcastanomaly_cancm4i<-((realtimemean6)-(hindcastmean6)) #
##plotmap(lon,lat,hindcastanomaly_cancm4i)
aux<-hindcastanomaly_cancm4i
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"cancm4i-anomaly-",trimestre,"-",ano,".nc",sep=""),mv=-999.99)

############
#GFDL_SPEAR#
############
#realtimemean2<-apply(gfdlspear_realtime$data[,,1:2]*86400,c(1,2),mean)
#hindcastmean3<-apply(gfdlspear_hindcast$data[,,1:obstempo],c(1,2),mean)
#hindcastanomaly_gfdlspear<-array(NA, dim=c(360,181,1))
#hindcastanomaly_gfdlspear<-((realtimemean3)-(hindcastmean3)) #
##plotmap(lon,lat,hindcastanomaly_gfdlspear)
#aux<-hindcastanomaly_gfdlspear
#aux[is.na(aux)] <- -999.99
#netcdfwrite(lon,lat,aux,paste(pathncfile,"gfdlspear-anomaly-",trimestre,"-",ano,".nc",sep=""),mv=-999.99)


##########
#GEM5-NEMO#
##########
#realtimemean7<-apply(gem5nemo_realtime$data[,,1:3]*86400,c(1,2),mean)
#hindcastmean7<-apply(gem5nemo_hindcast$data[,,1:obstempo],c(1,2),mean)
#hindcastanomaly_gem5nemo<-array(NA, dim=c(360,181,1))
#hindcastanomaly_gem5nemo<-((realtimemean7)-(hindcastmean7)) #
##plotmap(lon,lat,hindcastanomaly_gem5nemo)
#aux<-hindcastanomaly_gem5nemo
#aux[is.na(aux)] <- -999.99
#netcdfwrite(lon,lat,aux,paste(pathncfile,"gem5nemo-anomaly-",trimestre,"-",ano,".nc",sep=""),mv=-999.99)

######
#CMC1#
######
#realtimemean2<-apply(cmc1_realtime$data[,,1:3]*86400,c(1,2),mean)
#hindcastmean2<-apply(cmc1_hindcast$data[,,1:obstempo],c(1,2),mean)
#hindcastanomaly_cmc1<-array(NA, dim=c(360,181,1))
#hindcastanomaly_cmc1<-((realtimemean2)-(hindcastmean2)) #
#plotmap(lon,lat,hindcastanomaly_cmc1)
#aux<-hindcastanomaly_cmc1
#aux[is.na(aux)] <- -999.99
#netcdfwrite(lon,lat,aux,paste(pathncfile,"cmc1-anomaly-",trimestre,"-",ano,".nc",sep=""),mv=-999.99)
######
#CMC2#
######
#realtimemean3<-apply(cmc2_realtime$data[,,1:3]*86400,c(1,2),mean)
#hindcastmean3<-apply(cmc2_hindcast$data[,,1:obstempo],c(1,2),mean)
#hindcastanomaly_cmc2<-array(NA, dim=c(360,181,1))
#hindcastanomaly_cmc2<-((realtimemean3)-(hindcastmean3)) #
#plotmap(lon,lat,hindcastanomaly_cmc2)
#aux<-hindcastanomaly_cmc2
#aux[is.na(aux)] <- -999.99
#netcdfwrite(lon,lat,aux,paste(pathncfile,"cmc2-anomaly-",trimestre,"-",ano,".nc",sep=""),mv=-999.99)
###########
#NASA_GMAO#
###########
#realtimemean7<-apply(nasa_realtime$data[,,1:3]*86400,c(1,2),mean)
#hindcastmean7<-apply(gmao_hindcast$data[,,1:obstempo],c(1,2),mean)
#hindcastanomaly_nasa<-array(NA, dim=c(360,181,1))
#hindcastanomaly_nasa<-((realtimemean7)-(hindcastmean7)) #
##plotmap(lon,lat,hindcastanomaly_nasa)
#aux<-hindcastanomaly_nasa
#aux[is.na(aux)] <- -999.99
#netcdfwrite(lon,lat,aux,paste(pathncfile,"nasa-anomaly-",trimestre,"-",ano,".nc",sep=""),mv=-999.99)
###########
#GFDL_FLOR#
###########
#realtimemean2<-apply(flor_realtime$data[,,1:3]*86400,c(1,2),mean)
#hindcastmean2<-apply(flor_hindcast[,,1:obstempo],c(1,2),mean)
#hindcastanomaly_flor<-array(NA, dim=c(360,181,1))
##hindcastanomaly_flor<-((realtimemean2)-(hindcastmean2)) #
##plotmap(lon,lat,hindcastanomaly_flor)
#aux<-hindcastanomaly_flor
#aux[is.na(aux)] <- -999.99
#netcdfwrite(lon,lat,aux,paste(pathncfile,"flor-anomaly-",trimestre,"-",ano,".nc",sep=""),mv=-999.99)
######
#GFDL#
######
#realtimemean3<-apply(gfdl_realtime$data[,,1:3]*86400,c(1,2),mean)
##hindcastmean3<-apply(gfdl_hindcast$data[,,1:obstempo],c(1,2),mean)
#hindcastanomaly_gfdl<-array(NA, dim=c(360,181,1))
#hindcastanomaly_gfdl<-((realtimemean3)-(hindcastmean3)) #
##plotmap(lon,lat,hindcastanomaly_gfdl)
##aux<-hindcastanomaly_gfdl
##aux[is.na(aux)] <- -999.99
##netcdfwrite(lon,lat,aux,paste(pathncfile,"gfdl-anomaly-",trimestre,"-",ano,".nc",sep=""),mv=-999.99)


#############
#MULTIMODELO#
#############
hindcastanomaly_nmme<-(hindcastanomaly_cfsv2+hindcastanomaly_ccsm4+hindcastanomaly_nasa+
hindcastanomaly_cancm4i)/4
aux<-hindcastanomaly_nmme
aux[is.na(aux)] <- -999.99
netcdfwrite(lon,lat,aux,paste(pathncfile,"nmme1-anomaly-",trimestre,"-",ano,".nc",sep=""),mv=-999.99)
   
##hindcastanomaly_nmme<-(hindcastanomaly_cfsv2+hindcastanomaly_cmc1+hindcastanomaly_cmc2+hindcastanomaly_flor+hindcastanomaly_gfdl+
##hindcastanomaly_ccsm4+hindcastanomaly_nasa)/7


############
#Assimetria#
############
##skewness<-yk
##skewness[maskc==0]<-NA
##skewness[is.na(skewness)] <- -999.99
#netcdfwrite(lon,lat,skewness,paste(pathncfile,"skewness-nmme-",trimestre,"-",ano,"-masked.nc",sep=""),mv=-999.99)


}

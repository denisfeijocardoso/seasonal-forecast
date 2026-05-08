attributediagr <- function(data1,data2, nbins=10,maintitle="") {
# Plot attribute diagram 
#
# Usage: attributediagr(data1,data2, nbins, maintitle)
#
# Inputs:
#
# data1: Vector of forecast probabilities for the event of 
#        interest (e.g. precip. in the upper tercile)
#
# data2: Vector of binary observations for the event of
#        interest (e.g. precip. in the upper tercile)
#
#    nbins: number of probability bins 
#
#    maintitle: String containing the text for the reliability diagram title
#
# Author: Caio Coelho <caio.coelho@cptec.inpe.br>

pf<-data1
probfcsts<-as.vector(pf)

aux<-probfcsts
probfcsts<-probfcsts[!is.na(aux)]

binobs<-data2 
binobs <- as.vector(binobs)
binobs <- binobs[!is.na(aux)]

aux1<-binobs
binobs <- binobs[!is.na(aux1)]
probfcsts <- probfcsts[!is.na(aux1)]
                                             
obar <- mean(binobs, na.rm=TRUE)
n<-length(probfcsts)                                            

h1<-hist(probfcsts,breaks=seq(0,1,1/nbins),plot=F)$counts        
#h1<-h1[h1>0]

g1<-hist(probfcsts[binobs==1],breaks=seq(0,1,1/nbins),plot=F)$counts
#g1<-g1[g1>0]

obari <- g1/h1                                                    
obari[is.na(obari)]<-0
  
# Computes reliability,resolution and uncertainty components of the 
# Brier score 
yi <- seq((1/nbins)/2,1,1/nbins)
  
reliab <- sum(h1*((yi-obari)^2), na.rm=TRUE)/n
resol <- sum(h1*((obari-obar)^2), na.rm=TRUE)/n
uncert<-obar*(1-obar)

bs<-reliab-resol+uncert

#bs1<-mean((probfcsts-binobs)^2)

par(mar=c(4.3,1.5,3.5,0),pty="s",las=1,cex=2)  
plot(yi*100,h1/n*100,xlim=c(0,1)*100,ylim=c(0,1)*100,type='h',main=maintitle,xlab="Forecast probility (%)",ylab="Observed or forecast relative frequency (%)",col="#666666",lwd=10)
lines(yi*100,obari*100,lwd=2)
points(yi*100,obari*100,pch=16)
abline(0,1)
abline(h=obar*100)
abline(v=obar*100)
#abline(lsfit(yi*100,obari*100,wt=h1),lty=2)
lines(seq(-10,110),(seq(-10,110)+(obar*100))/2,lty=3)
text(20,100,paste("Rel: ",as.character(round(reliab,2)),sep=""))
text(20,90,paste("Res: ",as.character(round(resol,2)),sep=""))
text(20,80,paste("Unc: ",as.character(round(uncert,2)),sep=""))
text(20,70,paste("BS: ",as.character(round(bs,2)),sep=""))

}


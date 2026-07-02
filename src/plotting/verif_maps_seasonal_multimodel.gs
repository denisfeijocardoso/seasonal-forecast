function main(args)

'reinit'

tools='/scripts/subsaz/tools/'

**grads -lbc "run verif_maps_seasonal_multimodel.gs 2026020100 FEB 1 nmme prec regr"
**grads -lbc "run verif_maps_seasonal_multimodel.gs 2025020100 FEB 1 nmme prec nocalib"
***********DATE****************
anomesdiahora=subwrd(args,1)
anomesdia= substr(anomesdiahora,1,8)
ano  = substr(anomesdiahora,1,4)
anomes = substr(anomesdiahora,1,6)
mes = substr(anomesdiahora,5,2)
say anomesdiahora
******************************

********NAME MONTH**********
namemonth=subwrd(args,2)
***************************

********VERSÃO MULTIMODELO**********
version=subwrd(args,3)
if(substr(version,1,1) != 'v')
    version='v' % version
endif
say version
***********************************

************BASE DE DADOS**********
base=subwrd(args,4)
say base
***********************************

*************VARIÁVEL**************
namevar=subwrd(args,5)
say namevar
***********************************

*************CALIBRAÇÃO**************
calibration=subwrd(args,6)
say calibration
***********************************

if (namevar='prec')
    uni='mm'
endif
if (namevar='t2mt')
    uni='`ao`nC'
endif

lbt='White: equal probability for all categories'

model = 'multimodel'

***************PARAMETROS QUE DEPENDEM DO PRODUTO***************
prol='mnth0 seas0'
incrproi=1
incrprof=2
****************************************************************

while (incrproi<=incrprof)
    plt=subwrd(prol,incrproi)
    if(plt=mnth0)
        ltf=4
        pro='mnth'
    endif
    if(plt=seas0)
        ltf=2
        pro='seas'
    endif
    monthi=1
    monthf=12

    lt=0
    while(lt<=ltf)
        metl='corskill mssskill msssfase msssamplitude bias arocmed aroctinf aroctsup'   
        metm='corr msss pher aper bias rocarea_positiveanom rocarea_lowertercile rocarea_uppertercile'                            
        meti=1
        metf=8
    
        while(meti<=metf)

            met=subwrd(metl,meti)
            metname=subwrd(metm,meti)

            if (calibration = 'nocalib')
                if (base = 'copernicus')
                    path_in = '/dados/mmclima/multimodelo/seasonal/posproc/copernicus/'version'/verification/nocalib/' % model % '/'
                    out     = '/dados/mmclima/multimodelo/seasonal/figures/copernicus/'version'/verification/nocalib/' % model % '/'
                    '!mkdir -p 'out'' 
                endif
                if (base = 'nmme')
                    path_in = '/dados/mmclima/multimodelo/seasonal/posproc/nmme/'version'/verification/nocalib/' % model % '/'
                    out     = '/dados/mmclima/multimodelo/seasonal/figures/nmme/'version'/verification/nocalib/' % model % '/'
                    '!mkdir -p 'out'' 
                endif
                file = namevar % "_" % met % "_" % plt % lt % "_" % model % "_nocalib_" % anomesdiahora % ".nc"
            endif

            if (calibration = 'regr')
                if (base = 'copernicus')
                    path_in = '/dados/mmclima/multimodelo/seasonal/posproc/copernicus/'version'/verification/regr/' % model % '/'
                    out     = '/dados/mmclima/multimodelo/seasonal/figures/copernicus/'version'/verification/regr/' % model % '/'
                    '!mkdir -p 'out'' 
                endif
                if (base = 'nmme')
                    path_in = '/dados/mmclima/multimodelo/seasonal/posproc/nmme/'version'/verification/regr/' % model % '/'
                    out     = '/dados/mmclima/multimodelo/seasonal/figures/nmme/'version'/verification/regr/' % model % '/'
                    '!mkdir -p 'out'' 
                endif
                file = namevar % "_" % met % "_" % plt % lt % "_" % model % "_calibrated_regr_" % anomesdiahora % ".nc"
            endif

            if (calibration = 'cox')
                if (base = 'copernicus')
                    path_in = '/dados/mmclima/multimodelo/seasonal/posproc/copernicus/'version'/verification/cox/' % model % '/'
                    out     = '/dados/mmclima/multimodelo/seasonal/figures/copernicus/'version'/verification/cox/' % model % '/'
                    '!mkdir -p 'out'' 
                endif
                if (base = 'nmme')
                    path_in = '/dados/mmclima/multimodelo/seasonal/posproc/nmme/'version'/verification/cox/' % model % '/'
                    out     = '/dados/mmclima/multimodelo/seasonal/figures/nmme/'version'/verification/cox/' % model % '/'
                    '!mkdir -p 'out'' 
                endif
                file = namevar % "_" % met % "_" % plt % lt % "_" % model % "_calibrated_cox_" % anomesdiahora % ".nc"
            endif

            fullpath_in = path_in''file
            say fullpath_in
            'sdfopen 'fullpath_in
            'q file'
            'q attr'

            linha = sublin(result, 5)
            nlinha = 1
            while (nlinha <= 200)
                linha_attr = sublin(result, nlinha)
                if (subwrd(linha_attr, 3) = 'history')
                    linha = linha_attr
                endif
                nlinha = nlinha + 1
            endwhile
            say 'Arquivo aberto: ' % linha
            
            mes_init = subwrd(linha, 5)
            ano_init = subwrd(linha, 6)
            mes_fcst = subwrd(linha, 8)
            ano_fcst = subwrd(linha, 9)

            'set display color white'
            'c'
            'set gxout shaded'
            'set font 4'
            'set map 1 1 3'
            'set display color white'
            'set mproj latlon'
            'set grads off'
            'set lat -90 90'
            'set lon -260 190'

            if(met=corskill)
                metn='CORRELATION'
                vale='0 0.2 0.4 0.6 0.8' 
                valc='0 115 7 8 2 114'
                'run ' % tools % '/crgb2.gs'
            endif
            if(met=mssskill)
                metn='MSSS'
                vale='-0.1 0 0.1 0.2 0.4 0.6 0.8'
                valc='47 48 49 50 51 52 53 54'
                'run ' % tools % '/cmrgb2.gs'
            endif
            if(met=arocmed | met=aroctinf | met=aroctsup)
                metn='ROC AREA'
                vale='0.5 0.6 0.7 0.8 0.9'
                valc='0 50 51 52 53 54'
                'run ' % tools % '/cmrgb2.gs'
            endif            
            if(met=msssamplitude)
                metn='AMPLITUDE ERROR'
                vale='0.1 0.2 0.4 0.6 0.9 1.1 2'
                valc='39 40 41 42 43 44 45 46'
                'run ' % tools % '/cmrgb2.gs'
            endif 
            if(met=msssfase)
                metn='PHASE ERROR'
                vale='0.3 0.6 0.9 1.2 1.5' 
                valc='0 82 83 84 85 86'
                'run ' % tools % '/crgb2.gs'
            endif
            if(met=bias)
                metn='BIAS'
                if(namevar='prec' & plt='mnth0') 
                    vale='-150 -130 -100 -70 -50 -30 -10 10 30 50 70 100 130 150'
                    valc='61 60 59 58 57 56 55 54 53 52 51 50 49 48 47'
                endif
                if(namevar='prec' & plt='seas0')
                    vale='-400 -300 -200 -160 -120 -80 -40 40 80 120 160 200 300 400'
                    valc='61 60 59 58 57 56 55 54 53 52 51 50 49 48 47'
                endif   
                if(namevar='t2mt')
                    vale='-10 -8 -6 -4 -3 -2 -1 1 2 3 4 6 8 10'
                    valc='47 48 49 50 51 52 53 54 55 56 57 58 59 60 61'
                endif                              
                'run ' % tools % 'brgb.gs'
            endif       

            say anomesdia' - 'plt''lt '   'metn

            if (base = 'copernicus')

                if(met=bias)
                    if (namevar = 'prec')
                        l2='PRECIPITATION TOTAL (1993 - 2016)'
                    endif
                    if (namevar = 't2mt')
                        l2='2-METRE TEMPERATURE TOTAL (1993 - 2016)'
                    endif   
                endif    

                if(met=corskill | met=mssskill | met=msssfase | met=msssamplitude)
                    if (namevar = 'prec')
                        l2='PRECIPITATION ANOMALY (1993 - 2016)'
                    endif
                    if (namevar = 't2mt')
                        l2='2-METRE TEMPERATURE ANOMALY (1993 - 2016)'
                    endif   
                endif     

                if(met=arocmed)
                    if (namevar = 'prec')
                        l2='POS. OR NEG. PRECIPITATION ANOMALY (1993 - 2016)'
                    endif
                    if (namevar = 't2mt')
                        l2='POS. OR NEG. 2-METRE TEMPERATURE ANOMALY (1993 - 2016)'
                    endif   
                endif  

                if(met=aroctinf)
                    if (namevar = 'prec')
                        l2='PRECIPITATION IN LOWER TERCILE (1993 - 2016)'
                    endif
                    if (namevar = 't2mt')
                        l2='2-METRE TEMPERATURE IN LOWER TERCILE (1993 - 2016)'
                    endif   
                endif  

                if(met=aroctsup)
                    if (namevar = 'prec')
                        l2='PRECIPITATION IN UPPER TERCILE (1993 - 2016)'
                    endif
                    if (namevar = 't2mt')
                        l2='2-METRE TEMPERATURE IN UPPER TERCILE (1993 - 2016)'
                    endif   
                endif       

                l3 = "ISSUED: " % mes_init % " VALID FOR " % mes_fcst

                if (calibration = 'nocalib') 
                    if (namevar = 'prec')
                        l1 = metn % ": C3S + CPTEC MULTIMODEL  REF: GPCP"   
                    endif
                    if (namevar = 't2mt')     
                        l1 = metn % ": C3S + CPTEC MULTIMODEL  REF: ERA5" 
                    endif                                
                endif

                if (calibration = 'regr')
                    if (namevar = 'prec')
                        l1 = metn % ": C3S + CPTEC MULTIMODEL CALIBRATED (REGR.) REF: GPCP"
                    endif
                    if (namevar = 't2mt')     
                        l1 = metn % ": C3S + CPTEC MULTIMODEL CALIBRATED (REGR.) REF: ERA5"  
                    endif                      
                endif

                if (calibration = 'cox')
                    if (namevar = 'prec')
                        l1 = metn % ": C3S + CPTEC MULTIMODEL CALIBRATED (COX) REF: GPCP"
                    endif
                    if (namevar = 't2mt')
                        l1= metn % ": C3S + CPTEC MULTIMODEL CALIBRATED (COX) REF: ERA5"
                    endif                            
                endif        

            endif

            if (base = 'nmme')

                if(met=bias)
                    if (namevar = 'prec')
                        l2='PRECIPITATION TOTAL (1991 - 2020)'
                    endif
                    if (namevar = 't2mt')
                        l2='2-METRE TEMPERATURE TOTAL (1991 - 2020)'
                    endif   
                endif    

                if(met=corskill | met=mssskill | met=msssfase | met=msssamplitude)
                    if (namevar = 'prec')
                        l2='PRECIPITATION ANOMALY (1991 - 2020)'
                    endif
                    if (namevar = 't2mt')
                        l2='2-METRE TEMPERATURE ANOMALY (1991 - 2020)'
                    endif   
                endif     

                if(met=arocmed)
                    if (namevar = 'prec')
                        l2='POS. OR NEG. PRECIPITATION ANOMALY (1991 - 2020)'
                    endif
                    if (namevar = 't2mt')
                        l2='POS. OR NEG. 2-METRE TEMPERATURE ANOMALY (1991 - 2020)'
                    endif   
                endif  

                if(met=aroctinf)
                    if (namevar = 'prec')
                        l2='PRECIPITATION IN LOWER TERCILE (1991 - 2020)'
                    endif
                    if (namevar = 't2mt')
                        l2='2-METRE TEMPERATURE IN LOWER TERCILE (1991 - 2020)'
                    endif   
                endif  

                if(met=aroctsup)
                    if (namevar = 'prec')
                        l2='PRECIPITATION IN UPPER TERCILE (1991 - 2020)'
                    endif
                    if (namevar = 't2mt')
                        l2='2-METRE TEMPERATURE IN UPPER TERCILE (1991 - 2020)'
                    endif   
                endif       

                l3 = "ISSUED: " % mes_init % " VALID FOR " % mes_fcst

                if (calibration = 'nocalib') 
                    if (namevar = 'prec')
                        l1 = metn % ": NMME + CPTEC MULTIMODEL  REF: GPCP"   
                    endif
                    if (namevar = 't2mt')     
                        l1 = metn % ": NMME + CPTEC MULTIMODEL  REF: ERA5" 
                    endif                                
                endif
                if (calibration = 'regr')
                    if (namevar = 'prec')
                        l1 = metn % ": NMME + CPTEC MULTIMODEL CALIBRATED (REGR.) REF: GPCP"
                    endif
                    if (namevar = 't2mt')     
                        l1 = metn % ": NMME + CPTEC MULTIMODEL CALIBRATED (REGR.) REF: ERA5"  
                    endif                      
                endif
                if (calibration = 'cox')
                    if (namevar = 'prec')
                        l1 = metn % ": NMME + CPTEC MULTIMODEL CALIBRATED (COX) REF: GPCP"
                    endif
                    if (namevar = 't2mt')
                        l1= metn % ": NMME + CPTEC MULTIMODEL CALIBRATED (COX) REF: ERA5"
                    endif                            
                endif        
            endif


****AF****

            reg=af

            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = "nmme_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "nmme_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "nmme_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = "c3s_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "c3s_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "c3s_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif           
            endif

            'run ' % tools % '/' % reg
            'set clevs 'vale
            'set ccols 'valc   
            'set gxout shaded'
            'd ' % met
            ''tools'/xcbar 9.0 9.3 1.5 7.0 -edge triangle -line on'

            'set string 1 c 14 0'
            'set strsiz 0.13'
            'draw string 5.5 8.4  'l1
            'draw string 5.5 8.15 'l2
            'draw string 5.5 7.9  'l3
            'printim 'out'/'fileout'.png'
            say '***Figura gerada: 'out''fileout'.png'
            'c'

            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'



****AA****

            reg=aa
            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = "nmme_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "nmme_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "nmme_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = "c3s_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "c3s_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "c3s_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif           
            endif 

            'run ' % tools % '/' % reg
            'set clevs 'vale
            'set ccols 'valc   
            'd smth9('met')'
            ''tools'/xcbar 9.3 9.7 1.5 7.0 -edge triangle -line on'

            'set string 1 c 14 0'
            'set strsiz 0.13'
            'draw string 5.5 8.4 'l1
            'draw string 5.5 8.15 'l2
            'draw string 5.5 7.9 'l3
            'printim 'out'/'fileout'.png'
            say '***Figura gerada: 'out''fileout'.png'                    

            'c'
            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'

****AU****

            reg=au
            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = "nmme_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "nmme_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "nmme_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = "c3s_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "c3s_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "c3s_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif           
            endif
            'run ' % tools % '/' % reg
            'set clevs 'vale
            'set ccols 'valc   
            'd smth9('met')'
            ''tools'/xcbar 8.8 9.1 1.5 7.0 -edge triangle -line on'

            'set string 1 c 14 0'
            'set strsiz 0.13'
            'draw string 5.5 8.4 'l1
            'draw string 5.5 8.15 'l2
            'draw string 5.5 7.9 'l3
            'printim 'out'/'fileout'.png'
            say '***Figura gerada: 'out''fileout'.png'
            'c'
            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'

****EU***

            reg=eu
            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = "nmme_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "nmme_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "nmme_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = "c3s_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "c3s_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "c3s_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif           
            endif
            'run ' % tools % '/' % reg
            'set clevs 'vale
            'set ccols 'valc   
            'd smth9('met')'
            ''tools'/xcbar 1.5 9.5 0.2 0.5 -edge triangle -line on'

            'set string 1 c 14 0'
            'set strsiz 0.15'
            'draw string 5.5 8.25 'l1
            'draw string 5.5 8.0 'l2
            'draw string 5.5 7.75 'l3
            'printim 'out'/'fileout'.png'
            say '***Figura gerada: 'out''fileout'.png'
            'c'
            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'

****AN****

            reg=an
            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = "nmme_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "nmme_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "nmme_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = "c3s_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "c3s_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "c3s_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif           
            endif                 
            'run ' % tools % '/' % reg
            'set clevs 'vale
            'set ccols 'valc   
            'd smth9('met')'
            ''tools'/xcbar 10 10.3 1.5 7.0 -edge triangle -line on'

            'set string 1 c 14 0'
            'set strsiz 0.15'
            'draw string 5.5 8.4 'l1
            'draw string 5.5 8.15 'l2
            'draw string 5.5 7.9 'l3
            'printim 'out'/'fileout'.png'
            say '***Figura gerada: 'out''fileout'.png'
            'c'
            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'

****PA****

            reg=pa
            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = "nmme_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "nmme_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "nmme_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = "c3s_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "c3s_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "c3s_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif           
            endif                     
            'run ' % tools % '/' % reg
            'set clevs 'vale
            'set ccols 'valc   
            'd smth9('met')'
            ''tools'/xcbar 1.5 9.5 1.4 1.8 -edge triangle -line on'

            'set string 1 c 14 0'
            'set strsiz 0.15'
            'draw string 5.5 7.1 'l1
            'draw string 5.5 6.75 'l2
            'draw string 5.5 6.4 'l3
            'printim 'out'/'fileout'.png'
            say '***Figura gerada: 'out''fileout'.png'
            'c'
            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'

****NE****

            reg=ne
            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = "nmme_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "nmme_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "nmme_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = "c3s_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "c3s_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "c3s_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif           
            endif                      
            'run ' % tools % '/' % reg
            'set clevs 'vale
            'set ccols 'valc   
            'd smth9('met')'
            ''tools'/xcbar 1.5 9.5 2.6 2.9 -edge triangle -line on'

            'set string 1 c 14 0'
            'set strsiz 0.15'
            'draw string 5.5 6.2 'l1
            'draw string 5.5 5.85 'l2
            'draw string 5.5 5.5 'l3
            'printim 'out'/'fileout'.png'
            say '***Figura gerada: 'out''fileout'.png'
            'c'
            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'
****SE****

            reg=se
            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = "nmme_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "nmme_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "nmme_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = "c3s_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "c3s_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "c3s_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif           
            endif                          
            'run ' % tools % '/' % reg
            'set clevs 'vale
            'set ccols 'valc   
            'd smth9('met')'
            ''tools'/xcbar 1.5 9.5 2.6 2.9 -edge triangle -line on'

            'set string 1 c 14 0'
            'set strsiz 0.15'
            'draw string 5.5 6.2 'l1
            'draw string 5.5 5.85 'l2
            'draw string 5.5 5.5 'l3
            'printim 'out'/'fileout'.png'
            say '***Figura gerada: 'out''fileout'.png'
            'c'
            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'

****TR****

            reg=tr
            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = "nmme_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "nmme_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "nmme_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = "c3s_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "c3s_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "c3s_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif           
            endif                        
            'run ' % tools % '/' % reg
            'set clevs 'vale
            'set ccols 'valc   
            'd smth9('met')'
            ''tools'/xcbar 1.5 9.5 2.9 3.2 -edge triangle -line on'

            'set string 1 c 14 0'
            'set strsiz 0.15'
            'draw string 5.5 5.8 'l1
            'draw string 5.5 5.45 'l2
            'draw string 5.5 5.1 'l3
            'printim 'out'/'fileout'.png'
            say '***Figura gerada: 'out''fileout'.png'
            'c'
            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'
****GL****

            reg=gl
            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = "nmme_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "nmme_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "nmme_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = "c3s_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "c3s_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "c3s_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif           
            endif                         
            'run ' % tools % '/' % reg
            'set clevs 'vale
            'set ccols 'valc   
            'd smth9('met')'
            ''tools'/xcbar 1.5 9.5 1.1 1.4 -edge triangle -line on'

            'set string 1 c 14 0'
            'set strsiz 0.15'
            'draw string 5.5 7.5 'l1
            'draw string 5.5 7.15 'l2
            'draw string 5.5 6.8 'l3
            'printim 'out'/'fileout'.png'
            say '***Figura gerada: 'out''fileout'.png'
            'c'
            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'
            'reset'
****AM****

            reg=am
            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = "nmme_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "nmme_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "nmme_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = "c3s_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "c3s_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "c3s_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif           
            endif                         
            'set gxout shaded'
            'run ' % tools % '/' % reg
            'set clevs 'vale
            'set ccols 'valc   
            'd smth9('met')'
            ''tools'/xcbar 9.2 9.5 1.5 7.0 -edge triangle -line on'
    
            'set string 1 c 14 0'
            'set strsiz 0.13'
            'draw string 5.5 8.4 'l1
            'draw string 5.5 8.15 'l2
            'draw string 5.5 7.9 'l3
            'printim 'out'/'fileout'.png'
            say '***Figura gerada: 'out''fileout'.png'
            'c'
            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'

****AS****

            reg=as
            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = "nmme_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "nmme_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "nmme_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = "c3s_" % model % "_nocalib_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'regr')
                    fileout = "c3s_" % model % "_regr_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif
                if (calibration = 'cox')
                    fileout = "c3s_" % model % "_cox_" % metname % "_" % namevar % "_" % plt % lt % "_" % namemonth % "_" % reg
                endif           
            endif                             
            'set gxout shaded'
            'run ' % tools % '/' % reg
            'set clevs 'vale
            'set ccols 'valc   
            'd smth9('met')'
            ''tools'/xcbar 8.0 8.3 1.5 7.0 -edge triangle -line on'
    
            'set string 1 c 14 0'
            'set strsiz 0.13'
            'draw string 5.5 8.4 'l1
            'draw string 5.5 8.15 'l2
            'draw string 5.5 7.9 'l3
            'printim 'out'/'fileout'.png'
            say '***Figura gerada: 'out''fileout'.png'
            'c'
            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'


            meti = meti + 1
            'close 1'
        endwhile 
        lt = lt + 1
    endwhile 
incrproi = incrproi + 1
endwhile 

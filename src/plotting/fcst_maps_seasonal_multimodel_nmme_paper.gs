function main(args)

'reinit'

tools='/scripts/clima/produtos/site_forecast/tools/' 

**2025010100
***********DATE****************
anomesdiahora=subwrd(args,1)
anomesdia= substr(anomesdiahora,1,8)
ano  = substr(anomesdiahora,1,4)
anomes = substr(anomesdiahora,1,6)
mes = substr(anomesdiahora,5,2)
******************************
lbt='White: equal probability for all categories'

****DEFINIR VARIÁVEL, MODELO E BASE DE DADOS****
model = 'multimodel'   
base = 'nmme'
************************************************

***************PARAMETROS QUE DEPENDEM DO PRODUTO***************
prol='mnth0 seas0'
incrproi=1
incrprof=2
****************************************************************
''tools'ccrgb'

calib='cox regr gamma nocalib'
lis='prec'
**lis='prec t2mt'
lsu='mm `ao`nC'

incrvari=1
incrvarf=2

while(incrvari<=1)
  namevar=subwrd(lis,incrvari)
  uni=subwrd(lsu,incrvari)

  j = 1

  while (j <= 4)
    calibration = subwrd(calib,j)

    incrproi = 1 

    while (incrproi<=incrprof)
        plt=subwrd(prol,incrproi)
        if(plt=mnth0)
            ltf=4
            ltl=3
            pro='mnth'
        endif
        if(plt=seas0)
            ltf=2
            ltl=1
            pro='seas'
        endif

        lt=0

        while(lt<=ltf)
            if(namevar=prec & pro=mnth)
                if (calibration = 'nocalib')
                    metl = 'anom'
                    metm = 'anomaly'
                    num_met = 1
                endif
                if (calibration = 'regr' | calibration = 'cox' | calibration = 'gamma' )
                    metl = 'anom terc'
                    metm = 'anomaly probability_tercile'
                    num_met = 2
                endif
            endif

            if(namevar=prec & pro=seas)
                if (calibration = 'nocalib')
                    metl = 'anom'
                    metm = 'anomaly'
                    num_met = 1
                endif
                if (calibration = 'regr' | calibration = 'cox' | calibration = 'gamma' )
                    metl = 'anom terc'
                    metm = 'anomaly probability_tercile'
                    num_met = 2
                endif
            endif

            if(namevar=t2mt)
                if (calibration = 'nocalib')
                    metl = 'anom'
                    metm = 'anomaly'
                    num_met = 1
                endif
                if (calibration = 'regr' | calibration = 'cox' )
                    metl = 'anom acum terc prob '
                    metm = 'anomaly total probability_tercile probability_positive'
                    num_met = 4
                endif
            endif

          meti=1

          while(meti<=num_met)
            met=subwrd(metl,meti)
            metname=subwrd(metm,meti)

            say met
            if(namevar=prec & meti=1 & pro=seas)
              fac=ltl
              ll='on'
              var2='PRECIPITATION ANOMALY ('uni')'
              vale='-500 -300 -200 -150 -100 -50 -25 25 50 100 150 200 300 500'
              valc='34 33 32 31 30 29 28 27 26 25 24 23 22 21 20'
            endif

            if(namevar=prec & meti=1 & pro=mnth)
              fac=ltl
              ll='on'
              var2='PRECIPITATION ANOMALY ('uni')'
              vale='-180 -130 -90 -60 -30 -10 -5 5 10 30 60 90 130 180'
              valc='34 33 32 31 30 29 28 27 26 25 24 23 22 21 20'
            endif

            if(namevar=prec & meti=3 & pro=seas)
              fac=ltl
              ll='off'
              var2='PRECIPITATION ('uni')'
              vale='50 100 150 200 250 300 400 550 700 900'
              valc='27 74 75 76 77 78 79 80 81 82 83'
            endif

            if(namevar=prec & meti=3 & pro=mnth)
              fac=ltl
              ll='off'
              var2='PRECIPITATION ('uni')'
              vale='0 10 20 40 60 100 140 200 300 400'
              valc='27 74 75 76 77 78 79 80 81 82 83'
            endif

            if(namevar=prec & meti=2)
              fac=100
              ll='off'
              var2='PROB. MOST LIKELY PRECIP. TERCILE (%)'
              vale='-100 -90 -80 -70 -60 -50 -40 40 50 60 70 80 90 100'
              valc='27 34 33 32 31 30 29 27 26 25 24 23 22 20 27'
            endif

            if(namevar=prec & meti=4)
                fac=100
                ll='off'
                var2='PROB. PRECIP. ABOVE NORMAL (%)'
                vale='0 10 20 30 40 45 55 60 70 80 90 100'
                valc='27 34 33 32 30 29 27 26 25 24 22 20 27'
            endif

            if(namevar=prec & meti=5)
                fac=100
                ll='on'
                var2='PROBABILITY (CHANCE) OF EXCEEDING 10 mm'
                vale='10 25 50 75 90' 
                valc='28 26 25 24 23 20'
            endif

            if(namevar=prec & meti=6)
                fac=1
                ll='on'
                var2='PROBABILITY (CHANCE) OF EXCEEDING 20 mm'
                vale='10 25 50 75 90' 
                valc='28 26 25 24 23 20'
            endif
            if(namevar=prec & meti=7)
                fac=1
                ll='on'
                var2='PROBABILITY (CHANCE) OF EXCEEDING 40 mm'
                vale='10 25 50 75 90' 
                valc='28 26 25 24 23 20'                
**vale='10 20 30 40 50 60 70 80 90' 
**valc='33 32 31 30 29 27 26 25 24 20 20'
            endif
            if(namevar=prec & meti=8)
                fac=1
                ll='on'
                var2='PROBABILITY (CHANCE) OF EXCEEDING 60 mm'
                vale='10 25 50 75 90' 
                valc='28 26 25 24 23 20'    
            endif
            if(namevar=prec & meti=9)
                fac=1
                ll='on'
                var2='PROBABILITY (CHANCE) OF EXCEEDING 80 mm'
                vale='10 25 50 75 90' 
                valc='28 26 25 24 23 20'    
            endif
            if(namevar=prec & meti=10)
                fac=1
                ll='on'
                var2='PROBABILITY (CHANCE) OF EXCEEDING 100 mm'
                vale='10 25 50 75 90' 
                valc='28 26 25 24 23 20'    
            endif

            if(namevar=prec & meti=11)
                fac=1
                ll='on'
                var2='PROBABILITY (CHANCE) OF EXCEEDING 150 mm'
                vale='10 25 50 75 90' 
                valc='28 26 25 24 23 20'    
            endif

            if(namevar=prec & meti=12)
                fac=1
                ll='on'
                var2='PROBABILITY (CHANCE) OF EXCEEDING 200 mm'
                vale='10 25 50 75 90' 
                valc='28 26 25 24 23 20'    
            endif

            if(namevar=prec & meti=13)
                fac=1
                ll='on'
                var2='PROBABILITY (CHANCE) OF EXCEEDING 250 mm'
                vale='10 25 50 75 90' 
                valc='28 26 25 24 23 20'    
            endif

            if(namevar=prec & meti=14)
                fac=1
                ll='on'
                var2='PROBABILITY (CHANCE) OF EXCEEDING 300 mm'
                vale='10 25 50 75 90' 
                valc='28 26 25 24 23 20'    
            endif

            if(namevar=prec & meti=15)
                fac=1
                ll='on'
                var2='PROBABILITY (CHANCE) OF EXCEEDING 400 mm'
                vale='10 25 50 75 90' 
                valc='28 26 25 24 23 20'    
            endif

            if(namevar=prec & meti=16)
                fac=1
                ll='on'
                var2='PROBABILITY (CHANCE) OF EXCEEDING 500 mm'
                vale='10 25 50 75 90' 
                valc='28 26 25 24 23 20'    
            endif

            if(namevar=prec & meti=17)
                fac=1
                ll='on'
                var2='PROBABILITY (CHANCE) OF EXCEEDING 600 mm'
                vale='10 25 50 75 90' 
                valc='28 26 25 24 23 20'    
            endif

            if(namevar=prec & meti=18 & pro=seas)
                fac=1
                ll='on'
                var2='PRECIP. THAT HAVE 20% CHANCE OF OCCURRENCE'
                vale='1 25 50 100 200 300 400 500 700 800 1000' 
                valc='27 33 32 31 30 29 26 25 24 23 22 20'
            endif

            if(namevar=prec & meti=18 & pro=mnth)
                fac=1
                ll='on'
                var2='PRECIP. THAT HAVE 20% CHANCE OF OCCURRENCE'
                vale='1 5 10 25 50 100 200 300 400 600 800' 
                valc='27 33 32 31 30 29 26 25 24 23 22 20'
            endif

            if(namevar=prec & meti=19 & pro=seas)
                fac=1
                ll='on'
                var2='PRECIP. THAT HAVE 50% CHANCE OF OCCURRENCE'
                vale='1 25 50 100 200 300 400 500 700 800 1000' 
                valc='27 33 32 31 30 29 26 25 24 23 22 20'
            endif   

            if(namevar=prec & meti=19 & pro=mnth)
                fac=1
                ll='on'
                var2='PRECIP. THAT HAVE 50% CHANCE OF OCCURRENCE'
                vale='1 5 10 25 50 100 200 300 400 600 800' 
                valc='27 33 32 31 30 29 26 25 24 23 22 20'
            endif

            if(namevar=prec & meti=20 & pro=seas)
                fac=1
                ll='on'
                var2='PRECIP. THAT HAVE 80% CHANCE OF OCCURRENCE'
                vale='1 25 50 100 200 300 400 500 700 800 1000' 
                valc='27 33 32 31 30 29 26 25 24 23 22 20'
            endif   

            if(namevar=prec & meti=20 & pro=mnth)
                fac=1
                ll='on'
                var2='PRECIP. THAT HAVE 80% CHANCE OF OCCURRENCE'
                vale='1 5 10 25 50 100 200 300 400 600 800' 
                valc='27 33 32 31 30 29 26 25 24 23 22 20'
            endif

            if(namevar=t2mt & meti=1)
              fac=1
              ll='on'
              var2='2-METRE TEMPERATURE ANOMALY ('uni')'
              vale='-3 -2.5 -2 -1.5 -1 -0.5 -0.25 0.25 0.5 1 1.5 2 2.5 3'
              valc='47 48 49 50 51 52 53 54 55 56 57 58 59 60 61'
            endif

            if(namevar=t2mt & meti=3)
              fac=1
              ll='on'
              var2='2-METRE TEMPERATURE ('uni')'
              vale='-30 -27 -24 -21 -18 -15 -12 -8 -4 4 8 12 15 18 21 24 27 30'
              valc='100 83 82 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99'
            endif

            if(namevar=t2mt & meti=2)
              fac=100
              ll='off'
              var2='PROB. MOST LIKELY TEMP. TERCILE (%)'
              vale='-100 -90 -80 -70 -60 -50 -40 40 50 60 70 80 90 100'
              valc='27 20 22 23 24 25 26 27 29 30 31 32 33 34 27'
            endif

            if(namevar=t2mt & meti=4)
                fac=100
                ll='off'
                var2='PROB. TEMPERATURE ABOVE NORMAL (%)'
                vale='0 10 20 30 40 45 55 60 70 80 90 100'
                valc='27 20 22 24 25 26 27 30 30 32 33 34 27'
            endif


            if (calibration = 'nocalib')
                if (base = 'copernicus')
                    path_in = '/dados/mmclima/multimodelo/seasonal/posproc/copernicus/v2/forecast/nocalib/'model'/'ano'/'anomesdiahora'/'
                    out     = '/dados/mmclima/multimodelo/seasonal/figures/copernicus/v2/forecast/nocalib/'model'/'ano'/'anomesdiahora
                    '!mkdir -p 'out''                    
                endif
                if (base = 'nmme')
                    path_in = '/dados/mmclima/multimodelo/seasonal/posproc/nmme/v1/forecast/nocalib/'model'/'ano'/'anomesdiahora'/'
                    out     = '/dados/mmclima/multimodelo/seasonal/figures/nmme/v1/forecast/nocalib/'model'/'ano'/'anomesdiahora'/'
                    '!mkdir -p 'out''   
                endif
                file = 'fcst_'namevar'_'met'_'plt''lt'_'model'_nocalib_'anomesdiahora'.nc'
            endif

            if (calibration = 'regr')
                if (base = 'copernicus')
                    path_in = '/dados/mmclima/multimodelo/seasonal/posproc/copernicus/v2/forecast/regr/'model'/'ano'/'anomesdiahora'/'
                    out     = '/dados/mmclima/multimodelo/seasonal/figures/copernicus/v2/forecast/regr/'model'/'ano'/'anomesdiahora'/'
                    '!mkdir -p 'out''   
                endif
                if (base = 'nmme')
                    path_in = '/dados/mmclima/multimodelo/seasonal/posproc/nmme/v1/forecast/regr/'model'/'ano'/'anomesdiahora'/'
                    out     = '/dados/mmclima/multimodelo/seasonal/figures/nmme/v1/forecast/regr/'model'/'ano'/'anomesdiahora'/'
                    '!mkdir -p 'out''   
                endif
                file = 'fcst_'namevar'_'met'_'plt''lt'_'model'_calibrated_regr_'anomesdiahora'.nc'
            endif

            if (calibration = 'cox')
                if (base = 'copernicus')
                    path_in = '/dados/mmclima/multimodelo/seasonal/posproc/copernicus/v2/forecast/cox/'model'/'ano'/'anomesdiahora'/'
                    out     = '/dados/mmclima/multimodelo/seasonal/figures/copernicus/v2/forecast/cox/'model'/'ano'/'anomesdiahora'/'
                    '!mkdir -p 'out''   
                endif
                if (base = 'nmme')
                    path_in = '/dados/mmclima/multimodelo/seasonal/posproc/nmme/v1/forecast/cox/'model'/'ano'/'anomesdiahora'/'
                    out     = '/dados/mmclima/multimodelo/seasonal/figures/nmme/v1/forecast/cox/'model'/'ano'/'anomesdiahora'/'
                    '!mkdir -p 'out''   
                endif
                file = 'fcst_'namevar'_'met'_'plt''lt'_'model'_calibrated_cox_'anomesdiahora'.nc'
            endif

            if (calibration = 'gamma')
                if (base = 'copernicus')
                    path_in = '/dados/mmclima/multimodelo/seasonal/posproc/copernicus/v2/forecast/cox/'model'/'ano'/'anomesdiahora'/'
                    out     = '/dados/mmclima/multimodelo/seasonal/figures/copernicus/v2/forecast/cox/'model'/'ano'/'anomesdiahora'/'
                    '!mkdir -p 'out''   
                endif
                if (base = 'nmme')
                    path_in = '/dados/mmclima/multimodelo/seasonal/posproc/nmme/v1/forecast/gamma/'model'/'ano'/'anomesdiahora'/'
                    out     = '/dados/mmclima/multimodelo/seasonal/figures/nmme/v1/forecast/gamma/'model'/'ano'/'anomesdiahora'/'
                    '!mkdir -p 'out''   
                endif
                file = 'fcst_'namevar'_'met'_'plt''lt'_'model'_calibrated_gamma_'anomesdiahora'.nc'
            endif            

            fullpath_in = path_in''file

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

            'set gxout shaded'
            'set font 4'
            'set map 1 1 3'
            'set display color white'
            'set mproj latlon'
            'set grads off'
            'set lat -90 90'
            'set lon -260 360'
            'set grads off'

            l3='FORECAST ISSUED 'mes_init' 'ano_init' FOR 'mes_fcst' 'ano_fcst                                                          

            say 'ISSUED DATA ----- 'anomesdiahora' FOR 'mes_fcst' 'ano_fcst

            l2=''var2''

            if (base = 'copernicus')
              if (calibration = 'nocalib')
                l1='C3S + CPTEC MULTIMODEL '
              endif
              if (calibration = 'regr')
                l1='C3S + CPTEC MULTIMODEL CALIBRATED (REGR.)'
              endif
              if (calibration = 'cox')
                l1='C3S + CPTEC MULTIMODEL CALIBRATED (Cox)'
              endif        
            endif

            if (base = 'nmme')
              if (calibration = 'nocalib')
                l1='NMME + CPTEC MULTIMODEL '
              endif
              if (calibration = 'regr')
                l1='NMME + CPTEC MULTIMODEL CALIBRATED (Normal)'
              endif
              if (calibration = 'cox')
                l1='NMME + CPTEC MULTIMODEL CALIBRATED (Cox)'
              endif 
              if (calibration = 'gamma')
                l1='NMME + CPTEC MULTIMODEL CALIBRATED (Gamma)'
              endif                       
            endif            

****GL****
                        reg=gl
            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = 'nmme_'model'_nocalib_'namevar'_'metname'_'anomesdiahora'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'nmme_'model'_regr_'namevar'_'metname'_'anomesdiahora'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'nmme_'model'_cox_'namevar'_'metname'_'anomesdiahora'_'plt''lt'_'reg
                endif    
                if (calibration = 'gamma')
                    fileout = 'nmme_'model'_gamma_'namevar'_'metname'_'anomesdiahora'_'plt''lt'_'reg
                endif                        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = 'c3s_'model'_nocalib_'namevar'_'metname'_'anomesdiahora'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'c3s_'model'_regr_'namevar'_'metname'_'anomesdiahora'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'c3s_'model'_cox_'namevar'_'metname'_'anomesdiahora'_'plt''lt'_'reg
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

***********
****AS****
            reg=as

            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = 'nmme_'model'_nocalib_'namevar'_'metname'_'anomesdiahora'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'nmme_'model'_regr_'namevar'_'metname'_'anomesdiahora'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'nmme_'model'_cox_'namevar'_'metname'_'anomesdiahora'_'plt''lt'_'reg
                endif    
                if (calibration = 'gamma')
                    fileout = 'nmme_'model'_gamma_'namevar'_'metname'_'anomesdiahora'_'plt''lt'_'reg
                endif                        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = 'c3s_'model'_nocalib_'namevar'_'metname'_'anomesdiahora'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'c3s_'model'_regr_'namevar'_'metname'_'anomesdiahora'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'c3s_'model'_cox_'namevar'_'metname'_'anomesdiahora'_'plt''lt'_'reg
                endif                 
            endif
            say '***Figura gerada: 'out''fileout'.png'

            ''tools''reg
            'set clevs 'vale
            'set ccols 'valc
            'd ' % met
            ''tools'/xcbar 8.5 8.8 1.5 7.0 -edge triangle -line 'll''
 
            'set string 1 c 14 0'
            'set strsiz 0.12'
            'draw string 5.8 8.4  'l1
            'draw string 5.8 8.15 'l2
            'draw string 5.8 7.9  'l3
            if(meti=2)
               'set string 1 l 3 90'
               'set strsiz 0.12'
               'draw string 8.0 2.1 'lbt
               'draw string 8.3 4.9 Upper tercile'
               'draw string 8.3 2.1 Lower tercile'
            endif

            if(meti=3 & namevar=t2mt)
               'set gxout contour'
               'set map 0'
               'set mpdraw off'
               'set clevs 'vale
               'set ccols 1'
               'set clopts 1 1 0.13'
               'set clab masked'
               'd ' % met
               'set mpdraw on'
            endif

            'printim 'out''fileout'.png'
            'c'

            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out''fileout'.png'

            meti = meti + 1
            'close 1'
          endwhile 
      lt = lt + 1
      endwhile 
      incrproi = incrproi + 1
    endwhile
    j = j + 1
  endwhile 
  incrvari = incrvari + 1
endwhile           

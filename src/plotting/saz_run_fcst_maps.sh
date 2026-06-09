#!/bin/bash

# --- CRIAÇÃO DOS DIRETÓRIOS DOS MAPAS DA PREVISÃO EM TEMPO-REAL (SAZONAL) -----#

#Argumentos
anomes=$1
ano=${anomesdia:0:4}     
bases=("copernicus" "nmme")
calibs=("cox" "regr" "nocalib")


# Define lista de modelos conforme a base de dados
for base in "${bases[@]}"; do
    if [ "$base" = "copernicus" ]; then
        modelos=("multimodel" "canesm5" "ccsm4" "cesm1" "cfsv2" "gem52nemo" "geos5v2" "spear")
        version="v2"
    elif [ "$base" = "nmme" ]; then
        modelos=("multimodel" "ecmwf" "ukmo" "meteo_france" "dwd" "cmcc" "ncep" "jma" "eccc4" "eccc5" "bom")
        version="v1"
    fi

    # Loop nas calibrações
    for calib in "${calibs[@]}"; do
        # Loop nos modelos
        for modelo in "${modelos[@]}"; do
            dir="/dados/mmclima/multimodelo/sazonal/figures/${base}/${version}/forecast/${calib}/${modelo}/${ano}/${anomes}"

            if [ ! -d "$dir" ]; then
                echo " Criando diretório: $dir"
                mkdir -p "$dir"
            else
                echo " Diretório já existe: $dir"
            fi
        done
    done
done    

# --- Roda o script GrADS ---
# (substitua 'meuscript.gs' pelo nome real do seu script)
#grads -blc "run meuscript.gs ${anomesdia}"

#echo "Processamento concluído!"



  while (j <= 2)
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

        monthi=1
        monthf=12

        while(lt<=ltf)

          if (calibration = 'nocalib')
              metl = 'anom'
              metm = 'anomaly'
              num_met = 1
          else
              metl = 'anom acum terc prob'
              metm = 'anomaly total probability_tercile probability_positive'
              num_met = 4
          endif

          while(meti<=num_met)
            met=subwrd(metl,meti)
            metname=subwrd(metm,meti)


            if(var_name=prec & meti=1 & pro=seas)
              fac=ltl
              ll='on'
              var2='PRECIPITATION ANOMALY ('uni')'
              vale='-500 -300 -200 -150 -100 -50 -25 25 50 100 150 200 300 500'
              valc='34 33 32 31 30 29 28 27 26 25 24 23 22 21 20'
            endif

            if(var_name=prec & meti=1 & pro=mnth)
              fac=ltl
              ll='on'
              var2='PRECIPITATION ANOMALY ('uni')'
              vale='-180 -130 -90 -60 -30 -10 -5 5 10 30 60 90 130 180'
              valc='34 33 32 31 30 29 28 27 26 25 24 23 22 21 20'
            endif

            if(var_name=prec & meti=2 & pro=seas)
              fac=ltl
              ll='off'
              var2='PRECIPITATION ('uni')'
              vale='50 100 150 200 250 300 400 550 700 900'
              valc='27 74 75 76 77 78 79 80 81 82 83'
            endif

            if(var_name=prec & meti=2 & pro=mnth)
              fac=ltl
              ll='off'
              var2='PRECIPITATION ('uni')'
              vale='0 10 20 40 60 100 140 200 300 400'
              valc='27 74 75 76 77 78 79 80 81 82 83'
            endif

            if(var_name=prec & meti=3)
              fac=100
              ll='off'
              var2='PROB. MOST LIKELY PRECIP. TERCILE (%)'
              vale='-100 -90 -80 -70 -60 -50 -40 40 50 60 70 80 90 100'
              valc='27 34 33 32 31 30 29 27 26 25 24 23 22 20 27'
            endif

            if(var_name=prec & meti=4)
                fac=100
              ll='off'
                var2='PROB. PRECIP. ABOVE NORMAL (%)'
                vale='0 10 20 30 40 45 55 60 70 80 90 100'
                valc='27 34 33 32 30 29 27 26 25 24 22 20 27'
            endif

            if(var_name=t2mt & meti=1)
              fac=1
              ll='on'
              var2='2-METRE TEMPERATURE ANOMALY ('uni')'
              vale='-3 -2.5 -2 -1.5 -1 -0.5 -0.25 0.25 0.5 1 1.5 2 2.5 3'
              valc='47 48 49 50 51 52 53 54 55 56 57 58 59 60 61'
            endif

            if(var_name=t2mt & meti=2)
              fac=1
              ll='on'
              var2='2-METRE TEMPERATURE ('uni')'
              vale='-30 -27 -24 -21 -18 -15 -12 -8 -4 4 8 12 15 18 21 24 27 30'
              valc='100 83 82 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99'
            endif

            if(var_name=t2mt & meti=3)
              fac=100
              ll='off'
              var2='PROB. MOST LIKELY TEMP. TERCILE (%)'
              vale='-100 -90 -80 -70 -60 -50 -40 40 50 60 70 80 90 100'
              valc='27 20 22 23 24 25 26 27 29 30 31 32 33 34 27'
            endif

            if(var_name=t2mt & meti=4)
                fac=100
                ll='off'
                var2='PROB. TEMPERATURE ABOVE NORMAL (%)'
                vale='0 10 20 30 40 45 55 60 70 80 90 100'
                valc='27 20 22 24 25 26 27 30 30 32 33 34 27'
            endif

            if (calibration = 'nocalib')
                if (base = 'copernicus')
                    path_in = '/dados/mmclima/multimodelo/sazonal/posproc/copernicus/v2/forecast/nocalib/'model'/'ano'/'anomes
                    out     = '/dados/mmclima/multimodelo/sazonal/figures/copernicus/v2/forecast/nocalib/'model'/'ano'/'anomes
                endif
                if (base = 'nmme')
                    path_in = '/dados/mmclima/multimodelo/sazonal/posproc/nmme/v1/forecast/nocalib/'model'/'ano'/'anomes
                    out     = '/dados/mmclima/multimodelo/sazonal/figures/nmme/v1/forecast/nocalib/'model'/'ano'/'anomes
                endif
                file = 'fcst_'namevar'_'met'_'plt''lt'_'model'_calibrated_nocalib_'anomesdia'.nc'
            endif

            if (calibration = 'regr')
                if (base = 'copernicus')
                    path_in = '/dados/mmclima/multimodelo/sazonal/posproc/copernicus/v2/forecast/regr/'model'/'ano'/'anomes
                    out     = '/dados/mmclima/multimodelo/sazonal/figures/copernicus/v2/forecast/regr/'model'/'ano'/'anomes
                endif
                if (base = 'nmme')
                    path_in = '/dados/mmclima/multimodelo/sazonal/posproc/nmme/v1/forecast/regr/'model'/'ano'/'anomes
                    out     = '/dados/mmclima/multimodelo/sazonal/figures/nmme/v1/forecast/regr/'model'/'ano'/'anomes
                endif
                file = 'fcst_'namevar'_'met'_'plt''lt'_'model'_calibrated_regr_'anomesdia'.nc'
            endif

            if (calibration = 'cox')
                if (base = 'copernicus')
                    path_in = '/dados/mmclima/multimodelo/sazonal/posproc/copernicus/v2/forecast/cox/'model'/'ano'/'anomes
                    out     = '/dados/mmclima/multimodelo/sazonal/figures/copernicus/v2/forecast/cox/'model'/'ano'/'anomes
                endif
                if (base = 'nmme')
                    path_in = '/dados/mmclima/multimodelo/sazonal/posproc/nmme/v1/forecast/cox/'model'/'ano'/'anomes
                    out     = '/dados/mmclima/multimodelo/sazonal/figures/nmme/v1/forecast/cox/'model'/'ano'/'anomes
                endif
                file = 'fcst_'namevar'_'met'_'plt''lt'_'model'_calibrated_cox_'anomesdia'.nc'
            endif

            fullpath_in = path_in''file

            'sdfopen 'fullpath_in
            'q file'
            'q attr'

            linha = sublin(result, 5)
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

            say 'ISSUED DATA ----- 'anomesdia' FOR 'mes_fcst' 'ano_fcst

            l1=''

            if (base = 'copernicus')
              if (calibration = 'nocalib')
                l2='C3S + CPTEC MULTIMODEL UNCALIBRATED 'var2''
              endif
              if (calibration = 'regr')
                l2='C3S + CPTEC MULTIMODEL CALIBRATED (REGR.) 'var2''
              endif
              if (calibration = 'cox')
                l2='C3S + CPTEC MULTIMODEL CALIBRATED (COX) 'var2''
              endif        
            endif

            if (base = 'nmme')
              if (calibration = 'nocalib')
                l2='NMME + CPTEC MULTIMODEL UNCALIBRATED 'var2''
              endif
              if (calibration = 'regr')
                l2='NMME + CPTEC MULTIMODEL CALIBRATED (REGR.) 'var2''
              endif
              if (calibration = 'cox')
                l2='NMME + CPTEC MULTIMODEL CALIBRATED (COX) 'var2''
              endif        
            endif            

****AF****
            reg=af

            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = 'nmme_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'nmme_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'nmme_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = 'cs3_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'cs3_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'cs3_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif                 
            endif

            'run ' % tools % '/' % reg
            'set clevs 'vale
            'set ccols 'valc
            'd varn*'fac

            ''tools'xcbar 9.5 9.8 1.5 7.0 -edge triangle -line 'll''

            'set string 1 c 14 0'
            'set strsiz 0.15'
            'draw string 5.5 8.4  'l1
            'draw string 5.5 8.15 'l2
            'draw string 5.5 7.9  'l3
            if(meti=3)
               'set string 1 l 3 90'
               'set strsiz 0.12'
               'draw string 9.0 2.1 'lbt
               'draw string 9.3 4.9 Upper tercile'
               'draw string 9.3 2.1 Lower tercile'
            endif

            if(meti=2 & namevar=t2mt)
               'set gxout contour'
               'set map 0'
               'set mpdraw off'
               'set clevs 'vale
               'set ccols 1'
               'set clopts 1 1 0.13'
               'set clab masked'
               'd varn*'fac
               'set mpdraw on'
            endif

            'printim 'out'/'fileout'.png'
            'c'

            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'

***********
****AA****
            reg=aa

            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = 'nmme_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'nmme_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'nmme_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = 'cs3_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'cs3_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'cs3_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif                 
            endif

            ''tools''reg
            'set clevs 'vale
            'set ccols 'valc
            'd varn*'fac
            ''tools'xcbar 9.9 10.2 1.5 7.0 -edge triangle -line 'll''
 
            'set string 1 c 14 0'
            'set strsiz 0.15'
            'draw string 5.5 8.4  'l1
            'draw string 5.5 8.15 'l2
            'draw string 5.5 7.9  'l3
            if(meti=3)
               'set string 1 l 3 90'
               'set strsiz 0.12'
               'draw string 9.4 2.1 'lbt
               'draw string 9.7 4.9 Upper tercile'
               'draw string 9.7 2.1 Lower tercile'
            endif

            if(meti=2 & namevar=t2mt)
               'set gxout contour'
               'set map 0'
               'set mpdraw off'
               'set clevs 'vale
               'set ccols 1'
               'set clopts 1 1 0.13'
               'set clab masked'
               'd varn*'fac
               'set mpdraw on'
            endif

            'printim 'out'/'fileout'.png'
            'c'

            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'
           
***********
****AU****
            reg=au

            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = 'nmme_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'nmme_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'nmme_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = 'cs3_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'cs3_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'cs3_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif                 
            endif      

            ''tools''reg
            'set clevs 'vale
            'set ccols 'valc
            'd varn*'fac
            ''tools'xcbar 9.3 9.6 1.5 7.0 -edge triangle -line 'll''
 
            'set string 1 c 14 0'
            'set strsiz 0.13'
            'draw string 5.5 8.4  'l1
            'draw string 5.5 8.15 'l2
            'draw string 5.5 7.9  'l3
            if(meti=3)
               'set string 1 l 3 90'
               'set strsiz 0.12'
               'draw string 8.8 2.1 'lbt
               'draw string 9.1 4.9 Upper tercile'
               'draw string 9.1 2.1 Lower tercile'
            endif

            if(meti=2 & namevar=t2mt)
               'set gxout contour'
               'set map 0'
               'set mpdraw off'
               'set clevs 'vale
               'set ccols 1'
               'set clopts 1 1 0.13'
               'set clab masked'
               'd varn*'fac
               'set mpdraw on'
            endif

            'printim 'out'/'fileout'.png'
            'c'

            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'
           
***********
****EU****
            reg=eu

            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = 'nmme_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'nmme_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'nmme_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = 'cs3_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'cs3_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'cs3_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif                 
            endif

            ''tools''reg
            'set clevs 'vale
            'set ccols 'valc
            'd varn*'fac
            ''tools'xcbar 1.5 9.5 0.2 0.3 -edge triangle -line 'll''
 
            'set string 1 c 14 0'
            'set strsiz 0.15'
            'draw string 5.5 8.25 'l1
            'draw string 5.5 8.0  'l2
            'draw string 5.5 7.75 'l3
            if(meti=3)
               'set string 1 l 3 0'
               'set strsiz 0.12'
               'draw string 3.5 0.57 'lbt
               'draw string 7.3 0.43 Upper tercile'
               'draw string 2.5 0.43 Lower tercile'
            endif

            if(meti=2 & namevar=t2mt)
               'set gxout contour'
               'set map 0'
               'set mpdraw off'
               'set clevs 'vale
               'set ccols 1'
               'set clopts 1 1 0.13'
               'set clab masked'
               'd varn*'fac
               'set mpdraw on'
            endif

            'printim 'out'/'fileout'.png'
            'c'

            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'
           
***********
****AN****
            reg=an

            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = 'nmme_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'nmme_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'nmme_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = 'cs3_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'cs3_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'cs3_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif                 
            endif

            ''tools''reg
            'set clevs 'vale
            'set ccols 'valc
            'd varn*'fac
            ''tools'xcbar 10.3 10.45 1.5 7.0 -edge triangle -line 'll''
 
            'set string 1 c 14 0'
            'set strsiz 0.15'
            'draw string 5.5 8.4  'l1
            'draw string 5.5 8.15 'l2
            'draw string 5.5 7.9  'l3
            if(meti=3)
               'set string 1 l 3 90'
               'set strsiz 0.12'
               'draw string 9.98 2.1 'lbt
               'draw string 10.2 4.9 Upper tercile'
               'draw string 10.2 2.1 Lower tercile'
            endif

            if(meti=2 & namevar=t2mt)
               'set gxout contour'
               'set map 0'
               'set mpdraw off'
               'set clevs 'vale
               'set ccols 1'
               'set clopts 1 1 0.13'
               'set clab masked'
               'd varn*'fac
               'set mpdraw on'
            endif

            'printim 'out'/'fileout'.png'
            'c'

            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'
           
***********
****PA****
            reg=pa
            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = 'nmme_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'nmme_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'nmme_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = 'cs3_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'cs3_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'cs3_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif                 
            endif

            ''tools''reg
            'set clevs 'vale
            'set ccols 'valc
            'd varn*'fac
            ''tools'xcbar 1.5 9.5 1.0 1.3 -edge triangle -line 'll''
 
            'set string 1 c 14 0'
            'set strsiz 0.15'
            'draw string 5.5 7.1  'l1
            'draw string 5.5 6.75 'l2
            'draw string 5.5 6.4  'l3
            if(meti=3)
               'set string 1 l 3 0'
               'set strsiz 0.12'
               'draw string 3.5 1.8 'lbt
               'draw string 7.3 1.5 Upper tercile'
               'draw string 2.5 1.5 Lower tercile'
            endif

            if(meti=2 & namevar=t2mt)
               'set gxout contour'
               'set map 0'
               'set mpdraw off'
               'set clevs 'vale
               'set ccols 1'
               'set clopts 1 1 0.13'
               'set clab masked'
               'd varn*'fac
               'set mpdraw on'
            endif

            'printim 'out'/'fileout'.png'
            'c'

            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'
          
***********
****NE****
            reg=ne
            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = 'nmme_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'nmme_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'nmme_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = 'cs3_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'cs3_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'cs3_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif                 
            endif

            ''tools''reg
            'set clevs 'vale
            'set ccols 'valc
            'd varn*'fac
            ''tools'xcbar 1.5 9.5 2.1 2.4 -edge triangle -line 'll''
 
            'set string 1 c 14 0'
            'set strsiz 0.15'
            'draw string 5.5 6.2  'l1
            'draw string 5.5 5.85 'l2
            'draw string 5.5 5.5  'l3
            if(meti=3)
               'set string 1 l 3 0'
               'set strsiz 0.12'
               'draw string 3.5 2.9 'lbt
               'draw string 7.3 2.6 Upper tercile'
               'draw string 2.5 2.6 Lower tercile'
            endif

            if(meti=2 & namevar=t2mt)
               'set gxout contour'
               'set map 0'
               'set mpdraw off'
               'set clevs 'vale
               'set ccols 1'
               'set clopts 1 1 0.13'
               'set clab masked'
               'd varn*'fac
               'set mpdraw on'
            endif

            'printim 'out'/'fileout'.png'
            'c'

            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'
           
***********
****SE****
            reg=se
            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = 'nmme_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'nmme_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'nmme_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = 'cs3_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'cs3_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'cs3_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif                 
            endif

            ''tools''reg
            'set clevs 'vale
            'set ccols 'valc
            'd varn*'fac
            ''tools'xcbar 1.5 9.5 2.1 2.4 -edge triangle -line 'll''
 
            'set string 1 c 14 0'
            'set strsiz 0.15'
            'draw string 5.5 6.2  'l1
            'draw string 5.5 5.85 'l2
            'draw string 5.5 5.5  'l3
            if(meti=3)
               'set string 1 l 3 0'
               'set strsiz 0.12'
               'draw string 3.5 2.9 'lbt
               'draw string 7.3 2.6 Upper tercile'
               'draw string 2.5 2.6 Lower tercile'
            endif
            if(meti=2 & namevar=t2mt)
               'set gxout contour'
               'set map 0'
               'set mpdraw off'
               'set clevs 'vale
               'set ccols 1'
               'set clopts 1 1 0.13'
               'set clab masked'
               'd varn*'fac
               'set mpdraw on'
            endif

            'printim 'out'/'fileout'.png'
            'c'

            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'
           
***********
****TR****
            reg=tr
            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = 'nmme_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'nmme_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'nmme_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = 'cs3_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'cs3_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'cs3_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif                 
            endif

            ''tools''reg
            'set clevs 'vale
            'set ccols 'valc
            'd varn*'fac
            ''tools'xcbar 1.5 9.5 2.4 2.7 -edge triangle -line 'll''
 
            'set string 1 c 14 0'
            'set strsiz 0.15'
            'draw string 5.5 5.8  'l1
            'draw string 5.5 5.45 'l2
            'draw string 5.5 5.1  'l3
            if(meti=3)
               'set string 1 l 3 0'
               'set strsiz 0.12'
               'draw string 3.5 3.2 'lbt
               'draw string 7.3 2.9 Upper tercile'
               'draw string 2.5 2.9 Lower tercile'
            endif

            if(meti=2 & namevar=t2mt)
               'set gxout contour'
               'set map 0'
               'set mpdraw off'
               'set clevs 'vale
               'set ccols 1'
               'set clopts 1 1 0.13'
               'set clab masked'
               'd varn*'fac
               'set mpdraw on'
            endif

            'printim 'out'/'fileout'.png'
            'c'

            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'
           

***********
****GL****
            reg=gl

            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = 'nmme_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'nmme_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'nmme_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = 'cs3_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'cs3_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'cs3_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif                 
            endif

            ''tools''reg
            'set clevs 'vale
            'set ccols 'valc             
            'd varn*'fac
            ''tools'xcbar 1.5 9.5 0.6 0.9 -edge triangle -line 'll''
 
            'set string 1 c 14 0'
            'set strsiz 0.15'
            'draw string 5.5 7.5   'l1
            'draw string 5.55 7.15 'l2
            'draw string 5.5 6.8   'l3
            if(meti=3)
               'set string 1 l 3 0'
               'set strsiz 0.12'
               'draw string 3.5 1.4 'lbt
               'draw string 7.3 1.1 Upper tercile'
               'draw string 2.5 1.1 Lower tercile'
            endif

            if(meti=2 & namevar=t2mt)
               'set gxout contour'
               'set map 0'
               'set mpdraw off'
               'set clevs 'vale
               'set ccols 1'
               'set clopts 1 1 0.13'
               'set clab masked'
               'd varn*'fac
               'set mpdraw on'
            endif

            'printim 'out'/'fileout'.png'
            'c'

            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'
           
           'reset'
**********
****AM****
            reg=am

            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = 'nmme_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'nmme_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'nmme_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = 'cs3_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'cs3_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'cs3_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif                 
            endif

            ''tools''reg
            'set clevs 'vale
            'set ccols 'valc
            'd varn*'fac
            ''tools'xcbar 9.8 10.1 1.5 7.0 -edge triangle -line 'll''
 
            'set string 1 c 14 0'
            'set strsiz 0.15'
            'draw string 5.5 8.4  'l1
            'draw string 5.5 8.15 'l2
            'draw string 5.5 7.9  'l3
            if(meti=3)
               'set string 1 l 3 90'
               'set strsiz 0.12'
               'draw string 9.3 2.1 'lbt
               'draw string 9.6 4.9 Upperr tercile'
               'draw string 9.6 2.1 Lower tercile'
            endif

            if(meti=2 & namevar=t2mt)
               'set gxout contour'
               'set map 0'
               'set mpdraw off'
               'set clevs 'vale
               'set ccols 1'
               'set clopts 1 1 0.13'
               'set clab masked'
               'd varn*'fac
               'set mpdraw on'
            endif

            'printim 'out'/'fileout'.png'
            'c'

            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'
           
***********
****AS****
            reg=as

            if (base = 'nmme')
                if (calibration = 'nocalib')
                    fileout = 'nmme_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'nmme_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'nmme_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif        
            endif

            if (base = 'copernicus')
                if (calibration = 'nocalib')
                    fileout = 'cs3_'model'_nocalib_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'regr')
                    fileout = 'cs3_'model'_regr_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif
                if (calibration = 'cox')
                    fileout = 'cs3_'model'_cox_'namevar'_'metname'_'anomesdia'_'plt''lt'_'reg
                endif                 
            endif

            ''tools''reg
            'set clevs 'vale
            'set ccols 'valc
            'd varn*'fac
            ''tools'xcbar 8.5 8.8 1.5 7.0 -edge triangle -line 'll''
 
            'set string 1 c 14 0'
            'set strsiz 0.12'
            'draw string 5.8 8.4  'l1
            'draw string 5.8 8.15 'l2
            'draw string 5.8 7.9  'l3
            if(meti=3)
               'set string 1 l 3 90'
               'set strsiz 0.12'
               'draw string 8.0 2.1 'lbt
               'draw string 8.3 4.9 Upper tercile'
               'draw string 8.3 2.1 Lower tercile'
            endif

            if(meti=2 & namevar=t2mt)
               'set gxout contour'
               'set map 0'
               'set mpdraw off'
               'set clevs 'vale
               'set ccols 1'
               'set clopts 1 1 0.13'
               'set clab masked'
               'd varn*'fac
               'set mpdraw on'
            endif

            'printim 'out'/'fileout'.png'
            'c'

            '!LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu magick 'out'/'fileout'.png -density 300 -trim +repage 'out'/'fileout'.png'

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
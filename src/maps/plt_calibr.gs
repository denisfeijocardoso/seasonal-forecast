function main(args)

'reinit'

ic=subwrd(args,1)
paths='/scripts/clima/produtos/Bruno/forecast/'
tools=subwrd(read(''paths'config.gs'),3)
in1=subwrd(read(''paths'config.gs'),3)
in=subwrd(read(''paths'config.gs'),3)'calibrated/'
hin=subwrd(read(''paths'config.gs'),3)
refpre=subwrd(read(''paths'config.gs'),3)
reft2m=subwrd(read(''paths'config.gs'),3)
pathfr=subwrd(read(''paths'config.gs'),3)
outtf=subwrd(read(''paths'config.gs'),3)
outtf2=subwrd(read(''paths'config.gs'),3)
outfig=subwrd(read(''paths'config.gs'),3)

say " "
say "-------------------------------------------"
say "tools-> "tools
say "in-> "in
say "outfig-> "outfig
say "-------------------------------------------"
say " "

lbt='White: equal probability for all categories'
*PARAMETROS QUE DEPENDEM DO TEMPO DE PREVISÃO*
*PARANMETROS QUE DEPENDEM DO PRODUTO*
prol='SEAS0 MNTH0'
*************************************
*PARAMETROS QUE DEPENDEM DA VARIAVEL*
*incrvari - alterar na linha 37
*incrvarf - alterar na linha 38
*************************************
***PARAMETROS QUE DEPENDEM DA INIC***
*lista_datas - linha 23
*************************************
''tools'ccrgb'

year=substr(ic,1,4)
month=substr(ic,5,2)
day='01'
if(month=11);indx=JFM;endif
if(month=12);indx=FMA;endif
if(month=01);indx=MAM;endif
if(month=02);indx=AMJ;endif
if(month=03);indx=MJJ;endif
if(month=04);indx=JJA;endif
if(month=05);indx=JAS;endif
if(month=06);indx=ASO;endif
if(month=07);indx=SON;endif
if(month=08);indx=OND;endif
if(month=09);indx=NDJ;endif
if(month=10);indx=DJF;endif
lis='prec t2mt psnm role tp85 zg50 uv85 uv20 vv85 vv20'
lsu='mm `ao`nC hPa Wm`a-2`n `ao`nC m ms`a-1`n ms`a-1`n ms`a-1`n ms`a-1`n'
incrvari=1
incrvarf=2
while(incrvari<=incrvarf)

   var=subwrd(lis,incrvari)
   uni=subwrd(lsu,incrvari)
   fac=1
            
   incrproi=1
   incrprof=2 
   while(incrproi<=incrprof)

      plt=subwrd(prol,incrproi)
   
      if(plt=SEAS0)
         ltf=2
         ltl=3
         pro='seas'
      endif
      
      if(plt=MNTH0)
         ltf=4
         ltl=1
         pro='mnth'
      endif  

      '!mkdir -p 'outfig''year'/'month'/'day''
      
      lcamp='anomaly ensemble probability_tercile probability_positive'
      icamp=1
      while(icamp<=4)
      
         camp=subwrd(lcamp,icamp)

         if(camp=anomaly)
            camp2='anomalies'
         endif
         if(camp=ensemble)
            camp2='totals'
         endif
         if(camp='probability_tercile')
            camp2='prob_terciles'
         endif
         if(camp='probability_positive')
            camp2='prob_positve_anomaly'
         endif

      if(var=prec & icamp=1 & pro=seas)
         fac=ltl
         ll='on'
         var2='PRECIPITATION ANOMALY ('uni')'
         vale='-500 -300 -200 -150 -100 -50 -25 25 50 100 150 200 300 500'
         valc='34 33 32 31 30 29 28 27 26 25 24 23 22 21 20'
      endif

      if(var=prec & icamp=1 & pro=mnth)
         fac=ltl
         ll='on'
         var2='PRECIPITATION ANOMALY ('uni')'
         vale='-180 -130 -90 -60 -30 -10 -5 5 10 30 60 90 130 180'
         valc='34 33 32 31 30 29 28 27 26 25 24 23 22 21 20'
      endif

      if(var=prec & icamp=2 & pro=seas)
         fac=ltl
         ll='off'
         var2='PRECIPITATION ('uni')'
         vale='50 100 150 200 250 300 400 550 700 900'
         valc='27 74 75 76 77 78 79 80 81 82 83'
      endif

      if(var=prec & icamp=2 & pro=mnth)
         fac=ltl
         ll='off'
         var2='PRECIPITATION ('uni')'
         vale='0 10 20 40 60 100 140 200 300 400'
         valc='27 74 75 76 77 78 79 80 81 82 83'
      endif

      if(var=prec & icamp=3)
         fac=100
         ll='off'
         var2='PROB. MOST LIKELY PRECIP. TERCILE (%)'
         vale='-100 -90 -80 -70 -60 -50 -40 40 50 60 70 80 90 100'
         valc='27 34 33 32 31 30 29 27 26 25 24 23 22 20 27'
      endif

      if(var=prec & icamp=4)
          fac=100
         ll='off'
          var2='PROB. PRECIP. ABOVE NORMAL (%)'
          vale='0 10 20 30 40 45 55 60 70 80 90 100'
          valc='27 34 33 32 30 29 27 26 25 24 22 20 27'
      endif

      if(var=t2mt & icamp=1)
         fac=1
         ll='on'
         var2='2-METRE TEMPERATURE ANOMALY ('uni')'
         vale='-3 -2.5 -2 -1.5 -1 -0.5 -0.25 0.25 0.5 1 1.5 2 2.5 3'
         valc='47 48 49 50 51 52 53 54 55 56 57 58 59 60 61'
      endif

      if(var=t2mt & icamp=2)
         fac=1
         ll='on'
         var2='2-METRE TEMPERATURE ('uni')'
         vale='-30 -27 -24 -21 -18 -15 -12 -8 -4 4 8 12 15 18 21 24 27 30'
         valc='100 83 82 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99'
      endif

      if(var=t2mt & icamp=3)
         fac=100
         ll='off'
         var2='PROB. MOST LIKELY TEMP. TERCILE (%)'
         vale='-100 -90 -80 -70 -60 -50 -40 40 50 60 70 80 90 100'
         valc='27 20 22 23 24 25 26 27 29 30 31 32 33 34 27'
      endif

      if(var=t2mt & icamp=4)
          fac=100
          ll='off'
          var2='PROB. TEMPERATURE ABOVE NORMAL (%)'
          vale='0 10 20 30 40 45 55 60 70 80 90 100'
          valc='27 20 22 24 25 26 27 30 30 32 33 34 27'
      endif

         t1=1
         t2=2
         t3=3
         lt=0
         while(lt<=ltf)

            'open 'in''var'-'pro'/'camp2'/BAM12_SEASONAL_FORECAST_LEAD0'lt'.ctl'

            'set gxout shaded'
            'set font 4'
            'set map 1 1 3'
            'set display color white'
            'set mproj latlon'
            'set grads off'
            'set lat -90 90'
            'set lon -260 360'
            'set grads off'

            if(month=01);month2=JAN;endif
            if(month=02);month2=FEB;endif
            if(month=03);month2=MAR;endif
            if(month=04);month2=APR;endif
            if(month=05);month2=MAY;endif
            if(month=06);month2=JUN;endif
            if(month=07);month2=JUL;endif
            if(month=08);month2=AUG;endif
            if(month=09);month2=SEP;endif
            if(month=10);month2=OCT;endif
            if(month=11);month2=NOV;endif
            if(month=12);month2=DEC;endif
                         
            'set time 00Z'day''month2''year''
            'q dims'
            tt=sublin(result,5)
            it=subwrd(tt,9)

            'define varn=varx'
            if(var=t2mt & icamp=2);'define varn=varx-273';endif
                        
            'set t 'it+1
            'q time'
            date=subwrd(result,3)
            monthi=substr(date,6,3)
            yeari=substr(date,9,4)
            
            if(pro=seas)

               'set t 'it+t1
               'q time'
               dd=subwrd(result,3)
               mm=substr(dd,6,3)
               m1=substr(mm,1,1)
               iyear=substr(dd,9,4)

               'set t 'it+t2
               'q time'
               dd=subwrd(result,3)
               mm=substr(dd,6,3)
               m2=substr(mm,1,1)

               'set t 'it+t3
               'q time'
               dd=subwrd(result,3)
               mm=substr(dd,6,3)
               m3=substr(mm,1,1)
               fyear=substr(dd,9,4)

               if(iyear=fyear)
                  l3='FORECAST ISSUED 'monthi' 'yeari' FOR 'm1''m2''m3' 'fyear''
               else
                  yyi=substr(iyear,3,2)
                  yyf=substr(fyear,3,2)
                  l3='FORECAST ISSUED 'monthi' 'yeari' FOR 'm1''m2''m3' 'yyi'/'yyf''
               endif                                                                

               say 'ISSUED DATA ----- 'date' FOR 'm1''m2''m3' LEAD0'lt

            endif
            
            if(pro=mnth)

               'set t 'it+t1
               'q time'
               dd=subwrd(result,3)
               mm=substr(dd,6,3)
               iyear=substr(dd,9,4)
               
               l3='FORECAST ISSUED 'monthi' 'yeari' FOR 'mm' 'iyear''
               
               say 'ISSUED DATA ----- 'date' FOR 'mm' 'iyear' LEAD0'lt
               
            endif

            'set t 'it

            l1=''
            l2='CPTEC/INPE (BAM1.2) 'var2''

****AF****
            reg=af
            ''tools''reg
            'set clevs 'vale
            'set ccols 'valc
            'd varn*'fac

            ''tools'xcbar 9.5 9.8 1.5 7.0 -edge triangle -line 'll''

            'set string 1 c 14 0'
            'set strsiz 0.15'
            'draw string 5.5 8.4  'l1
            'draw string 5.5 8.15 'l2
            'draw string 5.5 7.9  'l3
            if(icamp=3)
               'set string 1 l 3 90'
               'set strsiz 0.12'
               'draw string 9.0 2.1 'lbt
               'draw string 9.3 4.9 Upper tercile'
               'draw string 9.3 2.1 Lower tercile'
            endif

            if(icamp=2 & var=t2mt)
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

            'printim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png x1200 y927'

            'c'

            '!convert -density 300 -trim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png'

***********
****AA****
            reg=aa
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
            if(icamp=3)
               'set string 1 l 3 90'
               'set strsiz 0.12'
               'draw string 9.4 2.1 'lbt
               'draw string 9.7 4.9 Upper tercile'
               'draw string 9.7 2.1 Lower tercile'
            endif

            if(icamp=2 & var=t2mt)
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

            'printim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png x1200 y927'

            'c'

            '!convert -density 300 -trim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png'
           
***********
****AU****
            reg=au
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
            if(icamp=3)
               'set string 1 l 3 90'
               'set strsiz 0.12'
               'draw string 8.8 2.1 'lbt
               'draw string 9.1 4.9 Upper tercile'
               'draw string 9.1 2.1 Lower tercile'
            endif

            if(icamp=2 & var=t2mt)
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

            'printim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png x1200 y927'

            'c'

            '!convert -density 300 -trim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png'
           
***********
****EU****
            reg=eu
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
            if(icamp=3)
               'set string 1 l 3 0'
               'set strsiz 0.12'
               'draw string 3.5 0.57 'lbt
               'draw string 7.3 0.43 Upper tercile'
               'draw string 2.5 0.43 Lower tercile'
            endif

            if(icamp=2 & var=t2mt)
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

            'printim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png x1200 y927'

            'c'

            '!convert -density 300 -trim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png'
           
***********
****AN****
            reg=an
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
            if(icamp=3)
               'set string 1 l 3 90'
               'set strsiz 0.12'
               'draw string 9.98 2.1 'lbt
               'draw string 10.2 4.9 Upper tercile'
               'draw string 10.2 2.1 Lower tercile'
            endif

            if(icamp=2 & var=t2mt)
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

            'printim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png x1200 y927'

            'c'

            '!convert -density 300 -trim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png'
           
***********
****PA****
            reg=pa
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
            if(icamp=3)
               'set string 1 l 3 0'
               'set strsiz 0.12'
               'draw string 3.5 1.8 'lbt
               'draw string 7.3 1.5 Upper tercile'
               'draw string 2.5 1.5 Lower tercile'
            endif

            if(icamp=2 & var=t2mt)
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

            'printim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png x1200 y927'

            'c'

            '!convert -density 300 -trim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png'
           
***********
****NE****
            reg=ne
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
            if(icamp=3)
               'set string 1 l 3 0'
               'set strsiz 0.12'
               'draw string 3.5 2.9 'lbt
               'draw string 7.3 2.6 Upper tercile'
               'draw string 2.5 2.6 Lower tercile'
            endif

            if(icamp=2 & var=t2mt)
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

            'printim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png x1200 y927'

            'c'

            '!convert -density 300 -trim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png'
           
***********
****SE****
            reg=se
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
            if(icamp=3)
               'set string 1 l 3 0'
               'set strsiz 0.12'
               'draw string 3.5 2.9 'lbt
               'draw string 7.3 2.6 Upper tercile'
               'draw string 2.5 2.6 Lower tercile'
            endif
            if(icamp=2 & var=t2mt)
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

            'printim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png x1200 y927'

            'c'

            '!convert -density 300 -trim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png'
           
***********
****TR****
            reg=tr
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
            if(icamp=3)
               'set string 1 l 3 0'
               'set strsiz 0.12'
               'draw string 3.5 3.2 'lbt
               'draw string 7.3 2.9 Upper tercile'
               'draw string 2.5 2.9 Lower tercile'
            endif

            if(icamp=2 & var=t2mt)
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

            'printim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png x1200 y927'

            'c'

            '!convert -density 300 -trim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png'
           

***********
****GL****
            reg=gl
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
            if(icamp=3)
               'set string 1 l 3 0'
               'set strsiz 0.12'
               'draw string 3.5 1.4 'lbt
               'draw string 7.3 1.1 Upper tercile'
               'draw string 2.5 1.1 Lower tercile'
            endif

            if(icamp=2 & var=t2mt)
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

            'printim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png x1200 y927'

            'c'

            '!convert -density 300 -trim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png'
           
           'reset'
**********
****AM****
            reg=am
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
            if(icamp=3)
               'set string 1 l 3 90'
               'set strsiz 0.12'
               'draw string 9.3 2.1 'lbt
               'draw string 9.6 4.9 Upperr tercile'
               'draw string 9.6 2.1 Lower tercile'
            endif

            if(icamp=2 & var=t2mt)
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

            'printim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png x1200 y927'

            'c'

            '!convert -density 300 -trim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png'
           
***********
****AS****
            reg=as
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
            if(icamp=3)
               'set string 1 l 3 90'
               'set strsiz 0.12'
               'draw string 8.0 2.1 'lbt
               'draw string 8.3 4.9 Upper tercile'
               'draw string 8.3 2.1 Lower tercile'
            endif

            if(icamp=2 & var=t2mt)
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

            'printim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png x1400 y1082'

            'c'

            '!convert -density 300 -trim 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png 'outfig''year'/'month'/'day'/bam12_'var'_ca_'camp'_'year''month'0100_'pro'0'lt'_'reg'.png'
           
*********** 

            'close 1'
            'reset'
            
            t1=t1+1
            t2=t2+1
            t3=t3+1
            lt=lt+1
         endwhile
         
         icamp=icamp+1
      endwhile
      
      incrproi=incrproi+1
   endwhile

   incrvari=incrvari+1
endwhile
'quit'

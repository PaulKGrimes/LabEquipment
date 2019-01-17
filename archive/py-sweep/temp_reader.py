'''
Python code to read a temperature sensor connected to the 4th port of ADC
Thermometer is activated/energized by Bit 6 of A port

'''


import UniversalLibrary as ul
import time as time
import math as math

BoardNum = 0
Channel  = 3
ul_range = ul.BIP5VOLTS
Cbit     = 6
SensorOn = 1
SensorOff= 0

data=[]
sum1=0.0
sum2=0.0
Ndata = 16


for i in range(Ndata):
    val = ul.cbAIn(BoardNum, Channel, ul_range)
    x = ul.cbToEngUnits(BoardNum, ul_range, val)
    data.append(x)
    print i, val, x
    sum1+=x
    sum2 += x*x
#    time.sleep(0.2)
meanT = sum1/Ndata
print 'Mean Reading = ', meanT
print 'Sigma = ', math.sqrt(sum2/Ndata-meanT*meanT)

'''
Python code to monitor a temperature sensor connected to the 4th port of ADC

'''


import UniversalLibrary as ul
import time as time
import math as math

BoardNum = 0
Channel  = 3
ul_range = ul.BIP5VOLTS

Ndata = 3601                  #no. of data points
Tinterval = 10              #time in seconds between points
Nblock = 10                 #no. of data points between closing and reopening file
filename = 'Tvalue.txt'     #output filename

f = open(filename,'w')
t0 = int(time.time())
for i in range(Ndata):
    t1 = int(time.time())
    while ( ((t1-t0)%Tinterval) != 0 ):
        time.sleep(0.25)
        t1 = int(time.time())
    val = ul.cbAIn(BoardNum, Channel, ul_range)
    x = ul.cbToEngUnits(BoardNum, ul_range, val)
    print (t1-t0), x  
    if ( (i%Nblock) == 0 ):
        f.close()
        time.sleep(0.25)
        f = open(filename, 'a')
    f.write("%5d\t%.4f\n" % ((t1-t0),x))
    time.sleep(1)
f.close()
            


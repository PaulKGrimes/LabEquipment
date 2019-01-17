'''
Source code for moving the swing arm load.
Setting the motor driver is connected to Port A Bit 7 of USB-1408FS controller.

Edward Tong Feb 2012

'''

import UniversalLibrary as ul
import time as time

BoardNum = 0    #Board number of USB controller
Cbit     = 7    #Control bit is at A7
ambload  = 0
coldload = 1

ul.cbDConfigPort(BoardNum,ul.FIRSTPORTA,ul.DIGITALOUT)
ul.cbDBitOut (BoardNum,ul.FIRSTPORTA,Cbit,coldload)
time.sleep(2)

t0 = time.time()
for n in range(0,10,1):
    ul.cbDBitOut (BoardNum,ul.FIRSTPORTA,Cbit,ambload)
    time.sleep(1)
    ul.cbDBitOut (BoardNum,ul.FIRSTPORTA,Cbit,coldload)
    time.sleep(1)
    print n, time.time()-t0

t1 = time.time()
print t1-t0

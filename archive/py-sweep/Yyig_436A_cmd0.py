'''
Source code for power measurement versus frequency with the HP436A power meter
in conjunction with the Micro-lambda MLBF filter.
This version computes the Y-factor with a hot followed by a cold measurement.
   
Created on Aug 3, 2011

@author: Kieran

modified dec 2011 by ET
a) check if power meter is giving out 2 very different readings
b) accept command line input
c) compute noise temp with the knowledge of Tamb

'''
import math
import visa
import time
import socket
import sys

PM_ADDRESS='GPIB::13'
FILTER_IP='192.168.1.13'
FILTER_PORT=30303
F_neutral=6.0         #Freq (GHz) returned to at the end
pow_read_sleep=0.15   #Waiting time for power meter

pm=visa.instrument(PM_ADDRESS) #connect to power meter
visa.vpp43.set_attribute(pm.vi,visa.VI_ATTR_TERMCHAR_EN,visa.VI_TRUE)
pm.write('9A+V')

#set up socket to connect to filter
sock = socket.socket( socket.AF_INET, # Internet
                      socket.SOCK_DGRAM ) # UDP

def read():
    global value
    value=pm.read()
    return value
    

def power():#read power from pm. takes two measurements and averages
    while (read()[:1]!='P'):
        if raw_input('power out of range, please correct and press enter (0 to break)')=='0':
            break   
    pow1=float(value[3:12])
    time.sleep(pow_read_sleep)
    pow2=float(pm.read()[3:12])
    if ( abs((pow1-pow2)/(pow1+pow2)) < 0.05 ):
        return ((pow1+pow2)*0.5)
    else:
        time.sleep(pow_read_sleep)
        pow3 = float(pm.read()[3:12])
        if ( abs(pow2-pow3) < abs(pow1-pow3) ):
            return ((pow2+pow3)*0.5)
        else:
            return ((pow1+pow3)*0.5)

   

#main part of code

Tamb = 295
Tcold = 77
if len(sys.argv) >= 6:
    f = open(sys.argv[1],'w')
    startfreq = float(sys.argv[2])
    stopfreq  = float(sys.argv[3])
    step = float(sys.argv[4])
    incr = float(sys.argv[5])
    Tamb = float(sys.argv[6])
else:
    print ('cmd line arguments: <out_file_name> <F1(GHz)> <F2(GHz)> <dF(G)> <incr[0]> <Tamb(K)>')
    f = open(raw_input('Output file: '), 'w')
    startfreq = input('Minimum frequency (GHz): ')
    stopfreq  = input('Maximum frequency (GHz): ')
    step = input ('Frequency step (GHz): ')
    incr = input ('increment multiplier offset: (>=0): ')
    Tamb = input ('Amb load temp (K): ')

#create list of frequencies
freq=[startfreq]
cfreq=startfreq
while cfreq<stopfreq-0.0001:
    cfreq=cfreq+step
    step=step*(1+incr)
    freq.append(cfreq)
    


print 'Actual end frequency: '+str(cfreq)

print 'Hot measurement'
Pon=[]
for i in range(len(freq)):
    #set filter
    sock.sendto('f'+str(1000*freq[i]),(FILTER_IP, FILTER_PORT))
    time.sleep(pow_read_sleep)
    Pon.append(power())
    print str(freq[i])+'Ghz\t'+str(Pon[i])
    
#pause to change load
raw_input('Change to cold load. Press enter when done')

print 'Cold measurement'
Poff=[]
Y=[]
Trx=[]
sock.sendto('f'+str(1000*startfreq),(FILTER_IP, FILTER_PORT))
pdummy=power()
for i in range(len(freq)):
    #set filter
    sock.sendto('f'+str(1000*freq[i]),(FILTER_IP, FILTER_PORT))
    time.sleep(pow_read_sleep)
    Poff.append(power())
    Y.append(Pon[i]/Poff[i])
    if ( Y[i] > 1.001 ):
        TT = (Tamb-Y[i]*Tcold)/(Y[i]-1)
    else:
        TT = 9999.9
    Trx.append(TT)
    print str(freq[i])+'Ghz\t'+str(Poff[i])+'\t'+str(round(Y[i],4))+'\t'+str(round(TT,1))
    f.write("%.2f\t%.3e\t%.3e\t%.4f\t%.2f\n" % (freq[i],Pon[i],Poff[i],Y[i],Trx[i]))
    
f.close()
sock.sendto('f'+str(1000*F_neutral),(FILTER_IP, FILTER_PORT))
pp=power()
pm.close()
print 'finished'

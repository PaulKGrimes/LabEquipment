'''
Source code for doing amplifier noise measurement with the SIS biased above the gap.

Created on March 6, 2012 ET,PG
modified March 23, 2012 ET

'''

from math import *
import visa
import socket
import sys
import UniversalLibrary as ul
import numpy as np
import time

PM_ADDRESS='GPIB::12'
FILTER_IP='169.254.59.19'
FILTER_PORT=5025

Vlist = [14.5,14,13.5,13,12.5,12,11.5]
                                #list of voltages to read

def read():
    global value
    value=pm.read()
    return value 

def power():#read power from pm. takes two measurements and averages
    while (read()[:1]!='P'):
        if raw_input('power out of range, please correct and press enter (0 to break)')=='0':
            break   
    pow1=float(value[3:12])
    time.sleep(0.1)
    pow2=float(pm.read()[3:12])
    if ( abs((pow1-pow2)/(pow1+pow2)) < 0.05 ):
        return ((pow1+pow2)*0.5)
    else:
        time.sleep(0.1)
        pow3 = float(pm.read()[3:12])
        if ( abs(pow2-pow3) < abs(pow1-pow3) ):
            return ((pow2+pow3)*0.5)
        else:
            return ((pow1+pow3)*0.5)


def readV():
    jv=ul.cbAIn(BoardNum,0,AD_GAIN)
    jv=ul.cbToEngUnits(BoardNum,AD_GAIN,jv)
    jv=(jv/G1)*1000
    global volts
    volts=jv
    return jv

pm=visa.instrument(PM_ADDRESS) #connect to power meter
visa.vpp43.set_attribute(pm.vi,visa.VI_ATTR_TERMCHAR_EN,visa.VI_TRUE)
pm.write('9A+V')

#set up socket to connect to filter
sock = socket.socket( socket.AF_INET, # Internet
                      socket.SOCK_DGRAM ) # UDP

DA_GAIN=ul.UNI5VOLTS
DA_channel=1                              #channel 1 is amplified

#data entry
if len(sys.argv) >=7:
    outfile = open(sys.argv[1],'w')
    startfreq = float(sys.argv[2])
    stopfreq  = float(sys.argv[3])
    step = float(sys.argv[4])
    incr = float(sys.argv[5])
    Fuse = open(sys.argv[6],'r')
else:
    print ('cmd line arguments: <out_file_name> <F1(GHz)> <F2(GHz)> <dF(G)> <incr[0]> <use file>')
    outfile = open(raw_input('Output file: '), 'w')
    startfreq = input('Minimum frequency (GHz): ')
    stopfreq  = input('Maximum frequency (GHz): ')
    step = input ('Frequency step (GHz): ')
    incr = input ('increment multiplier offset: (>=0): ')
    Fuse = open(raw_input('Select use file: '), 'r')

lines=Fuse.readlines()
Fuse.close()
Vs_min=float(lines[0].split()[0])
Vs_max=float(lines[1].split()[0])
MaxDAC=float(lines[2].split()[0])
ADRate=int(lines[3].split()[0])
G1=float(lines[4].split()[0])
G2=float(lines[5].split()[0])
BoardNum=int(lines[6].split()[0])
AD_GAIN=int(lines[7].split()[0])
Poffset=float(lines[8].split()[0])    

#create list of frequencies
freq=[startfreq]
cfreq=startfreq
while cfreq<stopfreq-0.0001:
    cfreq=cfreq+step
    step=step*(1+incr)
    freq.append(cfreq)

pdata=[]
vdata=[]
idata=[]
pdata.append(freq)
sock.sendto('f'+str(1000*startfreq),(FILTER_IP, FILTER_PORT))
pdummy=power()
for i, Vx in enumerate(Vlist):
    nn = int(floor((Vs_max-Vx)/(Vs_max-Vs_min)*MaxDAC))
    ul.cbAOut(BoardNum, DA_channel, DA_GAIN, nn) 
    jv=ul.cbToEngUnits(BoardNum,AD_GAIN,ul.cbAIn(BoardNum,0,AD_GAIN))
    vdata.append(jv/G1*1000)
    jc= jv=ul.cbToEngUnits(BoardNum,AD_GAIN,ul.cbAIn(BoardNum,1,AD_GAIN))
    idata.append(jc*G2)
    tempdata = []
    for F in freq:
        sock.sendto('f'+str(1000*F),(FILTER_IP, FILTER_PORT))
        time.sleep(0.1)
        pp = power()
        print i, Vx, F, pp
        tempdata.append(pp)
    pdata.append(tempdata)

parray = np.array(pdata, dtype = np.float32)
ptrans = np.transpose(parray)

outfile.write('Vbias\t')
for V in vdata:
    outfile.write('%.3f\t' % V)
outfile.write('\n')

outfile.write('Ibias\t')
for I in idata:
    outfile.write('%.4f\t' % I)
outfile.write('\n')

#for i, F in enumerate(freq):
#    outfile.write("%.1f\t" % F)
#    for j, V in enumerate(vdata):
#        outfile.write("%.3e\t" % ptrans[i, j])
#    outfile.write("\n")

np.savetxt(outfile,ptrans,fmt='%.3e',delimiter=' ',newline='\n')
outfile.write("\n")
outfile.close()

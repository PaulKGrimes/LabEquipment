'''
Created on Aug 8, 2011
@author: Kieran

modified Oct. 2011 by Edward Tong
This code takes the amplified output from DAC2 to give a +/-15 mV sweep

modified Aug. 2013 by ET
Takes two traces for hot & cold loads. Compute Y-factor from it.
Always read 3 channels

'''

docstring = '''
ivp_15mV_hc.py
--
Kieran - Aug 8, 2011
modified by Paul Grimes - Oct 7, 2011
modified by Edward Tong - Aug 26, 2013

IVP data sweeping program for hot/cold measurements

Command line usage: python ivp_15mV_hc.py <output file> <min mV> <max mV> <step> <Navg>

'''

from math import *
import UniversalLibrary as ul
import numpy
import pylab
import time
import sys

Cbit = 7                #Control bit is A7
loadSwitchDelay = 1.0   #Time to wait for load to switch and power to settle
Poffset = 0.01067         #offset in power reading
ambload  = 0
coldload = 1

Tamb = 295
Tcold = 78.5

Ymin = 2.0

def readV():
    jv=ul.cbAIn(BoardNum,0,AD_GAIN)
    jv=ul.cbToEngUnits(BoardNum,AD_GAIN,jv)
    jv=(jv/G1)*1000
    global volts
    volts=jv
    return jv

def crop(x):
    if x<Vs_min:
        x=Vs_min
    if x>Vs_max:
        x=Vs_max
    return x

print docstring

ch_used = 3
if len(sys.argv) >= 6:
    out = open(sys.argv[1], 'w')
    v1 = float(sys.argv[2])
    v2 = float(sys.argv[3])
    step= int(sys.argv[4])
    Navg = 3*int(sys.argv[5])+1
else:
    #parameters
    out=open(raw_input('Output file: '),'w')
    v1=input('Minimum voltage: ')
    v2=input('Maximum voltage: ')
    step=input('Step: ')
    Navg=int(3*(input('Averaging factor: ')+1))

if v1<v2:
    v1, v2 = v2, v1

#variables
DA_GAIN=ul.UNI5VOLTS
DA_channel=1                              #channel 1 is amplified
default_useFile = 'iv2014_15mV.use'

ADdata=numpy.array([numpy.int16(1)]*Navg)
Vout=[]
Iout=[]
Pout=[]
Vout2=[]
Iout2=[]
Pout2=[]

#open and read use file

try:
    if len(sys.argv) == 8:
        spec_useFile = sys.argv[7]
    elif len(sys.argv) == 2:
        spec_useFile = sys.argv[1]
    else:
        raise IndexError
    print "Using specified use file ('%s')" % spec_useFile
    f=open(spec_useFile,'r')
except IndexError:
    print "Using default use file ('%s')" % default_useFile
    f=open(default_useFile,'r')
except IOError:
    while True:
        print 'ERROR! file does not exist'
        try:
            f=open(raw_input('Select use file: '), 'r')
            break
        except IOError:
            pass
    
lines=f.readlines()
f.close()
Vs_min=float(lines[0].split()[0])
Vs_max=float(lines[1].split()[0])
MaxDAC=float(lines[2].split()[0])
ADRate=int(lines[3].split()[0])
G1=float(lines[4].split()[0])
G2=float(lines[5].split()[0])
BoardNum=int(lines[6].split()[0])
AD_GAIN=int(lines[7].split()[0])
Poffset=float(lines[8].split()[0])

v1,v2=crop(v1),crop(v2)
Vrange=Vs_max-Vs_min
n0=MaxDAC/Vrange
nn = int(floor((Vs_max-v1)*n0))

# setup USB controller
ul.cbDConfigPort(BoardNum,ul.FIRSTPORTA,ul.DIGITALOUT)
ul.cbDBitOut (BoardNum,ul.FIRSTPORTA,Cbit,ambload)
time.sleep(2)

#change voltage to v1
print 'changing voltage to maximum'
ul.cbAOut(BoardNum, DA_channel, DA_GAIN, nn)
while(abs(readV()-v1)>0.2):
    if(volts<v1):
        nn-=1
    else:
        nn+=1
    if nn>=MaxDAC:
        nn=MaxDAC-1
    ul.cbAOut(BoardNum, DA_channel, DA_GAIN, nn)

#take measurements
print 'Measure with ambient load first'
nn0=nn
index1=0
while(readV()>v2):
    ul.cbAInScan(BoardNum, 0, 2, Navg, ADRate, AD_GAIN, ADdata, 0)
    data=[]
    for chan in range(ch_used):
        data.append([])
    count=0
    for i in ADdata:
        data[count%ch_used].append(ul.cbToEngUnits(BoardNum, AD_GAIN, int(i)))
        count+=1
    Vout.append(1000*sum(data[0],0.0)/(len(data[0])*G1))
    Iout.append((sum(data[1],0.0)/len(data[1]))*G2)
    Pout.append(sum(data[2],0.0)/len(data[2]))
    if index1%100==0:
        print '%.4fmV\t%.4fmA\t%.4f' %(Vout[index1],Iout[index1],Pout[index1])
        
    nn+=step
    ul.cbAOut(BoardNum, DA_channel, DA_GAIN, nn)
    index1+=1

print('\n')
print('Change to cold load')
ul.cbDBitOut (BoardNum,ul.FIRSTPORTA,Cbit,coldload)
time.sleep(2)

nn=nn0
ul.cbAOut(BoardNum, DA_channel, DA_GAIN, nn)
index2=0
while(readV()>v2):
    ul.cbAInScan(BoardNum, 0, 2, Navg, ADRate, AD_GAIN, ADdata, 0)
    data=[]
    for chan in range(ch_used):
        data.append([])
    count=0
    for i in ADdata:
        data[count%ch_used].append(ul.cbToEngUnits(BoardNum, AD_GAIN, int(i)))
        count+=1
    Vout2.append(1000*sum(data[0],0.0)/(len(data[0])*G1))
    Iout2.append((sum(data[1],0.0)/len(data[1]))*G2)
    if ch_used ==3:
        Pout2.append(sum(data[2],0.0)/len(data[2]))
    if index2%100==0:
        print '%.4fmV\t%.4fmA\t%.4f' %(Vout2[index2],Iout2[index2],Pout2[index2])
        
    nn+=step
    ul.cbAOut(BoardNum, DA_channel, DA_GAIN, nn)
    index2+=1

#set back to zero
print index1, index2
index0 = index1
if index2<index1:
    index0 = index2
print 'setting back to zero'
nn = int(floor(Vs_max*n0))
while(abs(readV())>0.2):
    if(volts<v1):
        nn-=1
    else:
        nn+=1
    if nn>=MaxDAC:
        nn=MaxDAC-1
    ul.cbAOut(BoardNum, DA_channel, DA_GAIN, nn)

ul.cbDBitOut (BoardNum,ul.FIRSTPORTA,Cbit,ambload)

print 'total number of points ',index0
#write iv data to file
print 'writing data to file'
Tnoise=[]
for i in range(len(Vout)):
    P1 = Pout[i]-Poffset
    P2 = Pout2[i]-Poffset
    YY = P1/P2
    if YY > Ymin:
        Tbruit = ((Tamb-YY*Tcold)/(YY-1))
    else:
        Tbruit = ((Tamb-Ymin*Tcold)/(Ymin-1))
    Tnoise.append(Tbruit)
    out.write('%7.4f\t%7.4f\t%.5f\t%.5f\t%.5f\t%.1f\n' %
              (Vout[i], Iout[i], P1, P2, YY, Tbruit))
    
out.close

#print len(Vout),len(Pout),len(Tnoise)
#for i in range(len(Tnoise)):
#    print i, Tnoise[i]

#Plot data
print 'plotting data'
pylab.xlabel('Voltage/mV')
pylab.plot(numpy.array(Vout),numpy.array(Tnoise), 'g-', label='I-V curve')
pylab.grid()
pylab.ylabel('Current/mA')
if ch_used == 3:
    pylab.twinx()
    pylab.plot(numpy.array(Vout),numpy.array(Pout), 'r-', label='ambload')
    pylab.plot(numpy.array(Vout2),numpy.array(Pout2), 'b-', label='coldload')
    pylab.ylabel('Power Out')
print 'finished'
pylab.show()

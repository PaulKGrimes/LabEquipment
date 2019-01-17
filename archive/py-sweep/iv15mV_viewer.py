'''
Created on Aug 8, 2011
@author: Kieran

modified Oct. 2011 by Edward Tong
This code takes the amplified output from DAC2 to give a +/-15 mV sweep

modified Jun 2013 by ET
This code displays a swept IV

'''

docstring = '''
ivp_15mV.py
--
Kieran - Aug 8, 2011
modified by Paul Grimes - Oct 7, 2011
modified by Paul Grimes and Edward Tong - Oct 12, 2011
modified by ET -- June 2013

IV data sweeping program

Interactive usage : python iv2.py <optional use file>
Command line usage: python iv2.py <output file> <min mV> <max mV> <step> <Navg> <Nchan> <Optional use file>

'''

from math import *
import UniversalLibrary as ul
import numpy
import pylab
import sys

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

ch_used=2               #voltage & current channels only

if len(sys.argv) >= 7:
    out = open(sys.argv[1], 'w')
    v1 = float(sys.argv[2])
    v2 = float(sys.argv[3])
    step= int(sys.argv[4])
    Navg = ch_used*int(sys.argv[5])+1
else:
    #parameters
    out=open(raw_input('Output file: '),'w')

    v1=input('Minimum voltage: ')
    v2=input('Maximum voltage: ')
    step=input('Step: ')
    Navg=int(ch_used*(input('Averaging factor: ')+1))

if v1<v2:
    v1, v2 = v2, v1

#variables
DA_GAIN=ul.UNI5VOLTS
DA_channel=1                              #channel 1 is amplified

    
Vs_min=-15.59               #previously from use file
Vs_max=15.00
MaxDAC=4096
ADRate=8000
G1=50.02
G2=0.2015
BoardNum=0
AD_GAIN=14                  #code for +/-2V (G=8)

ADdata=numpy.array([numpy.int16(1)]*Navg)
Vout=[]
Iout=[]
Pout=[]



v1,v2=crop(v1),crop(v2)
Vrange=Vs_max-Vs_min
n0=MaxDAC/Vrange
nn = int(floor((Vs_max-v1)*n0))


#change voltage to v1
print 'changing voltage to maximum'
ul.cbAOut(BoardNum, DA_channel, DA_GAIN, nn)
while(abs(readV()-v1)>0.2):
    if(volts<v1):
        nn-=1
    else:
        nn+=1
    if nn>=(MaxDAC-1):
        nn=MaxDAC-1
    ul.cbAOut(BoardNum, DA_channel, DA_GAIN, nn)

#take measurements
print 'taking measurements'
index=0
while(readV()>v2):
    ul.cbAInScan(BoardNum, 0, 1, Navg, ADRate, AD_GAIN, ADdata, 0)
    data=[]
    for chan in range(ch_used):
        data.append([])
    count=0
    for i in ADdata:
        data[count%ch_used].append(ul.cbToEngUnits(BoardNum, AD_GAIN, int(i)))
        count+=1
    Vout.append(1000*sum(data[0],0.0)/(len(data[0])*G1))
    Iout.append((sum(data[1],0.0)/len(data[1]))*G2)
    if ch_used ==3:
        Pout.append(sum(data[2],0.0)/len(data[2]))
    if index%100==0:
        if ch_used ==3:
            print '%.4fmV\t%.4fmA\t%.4f' %(Vout[index],Iout[index],Pout[index])
        else:
            print '%.4fmV\t%.4f' %(Vout[index],Iout[index])
    nn+=step
    ul.cbAOut(BoardNum, DA_channel, DA_GAIN, nn)
    index+=1

#set back to zero
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

print 'total number of points ',index
#write iv data to file
print 'writing data to file'
for i in range(len(Vout)):
    if ch_used == 3:
        out.write('%.7f\t%.7f\t%.7f\n' % (Vout[i], Iout[i], Pout[i]))
    else:
        out.write('%.7f\t%.7f\n' % (Vout[i], Iout[i]))
out.close

#Plot data
print 'plotting data'
pylab.xlabel('Voltage/mV')
pylab.plot(numpy.array(Vout),numpy.array(Iout), 'b-', label='I-V curve')
pylab.grid()
pylab.ylabel('Current/mA')
if ch_used == 3:
    pylab.twinx()
    pylab.plot(numpy.array(Vout),numpy.array(Pout), 'r-', label='P-V curve') 
    pylab.ylabel('Power Out')
print 'finished'
pylab.show()

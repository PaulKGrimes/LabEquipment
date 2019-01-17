'''
Created on Aug 8, 2011
@author: Kieran

modified Oct. 2011 by Edward Tong
This code takes the amplified output from DAC2 to give a +/-15 mV sweep

'''

docstring = '''
ivp_15mV.py
--
Kieran - Aug 8, 2011
modified by Paul Grimes - Oct 7, 2011
modified by Paul Grimes and Edward Tong - Oct 12, 2011

IVP data sweeping program - with IF power readings

Interactive usage : python iv2.py <optional use file>
Command line usage: python iv2.py <output file> <min mV> <max mV> <step> <Navg> <Nchan> <Optional use file>

Use <Nchan> == 3 for IV and PV data, 2 for just IV data
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

if len(sys.argv) >= 7:
    out = open(sys.argv[1], 'w')
    v1 = float(sys.argv[2])
    v2 = float(sys.argv[3])
    step= int(sys.argv[4])
    Navg = 3*int(sys.argv[5])+1
    ch_used = int(sys.argv[6])
else:
    #parameters
    out=open(raw_input('Output file: '),'w')

    v1=input('Minimum voltage: ')
    v2=input('Maximum voltage: ')
    step=input('Step: ')
    Navg=int(3*(input('Averaging factor: ')+1))
    ch_used = int(input('Number of DAQ channels: '))

if v1<v2:
    v1, v2 = v2, v1

#variables
DA_GAIN=ul.UNI5VOLTS
DA_channel=1                              #channel 1 is amplified
default_useFile = 'iv2011_10mV.use'

ADdata=numpy.array([numpy.int16(1)]*Navg)
Vout=[]
Iout=[]
Pout=[]

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
print 'taking measurements'
index=0
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

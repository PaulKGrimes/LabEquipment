'''
Source code for power measurement versus frequency with the HP436A power meter
in conjunction with the Micro-lambda MLBF filter.
This version computes the Y-factor with a hot followed by a cold measurement.
   
Created on Aug 3, 2011

@author: Kieran

modified dec 2011 by ET
a) check if power meter is giving out 2 very different readings
b) accept command line input
c) compute noise temp with the knowledge of Tamb and Tcold
modified feb 2012 by ET
using swing arm load to perform automatic Y-factor measurement
Motor connected to Bit 7 of Port A of USB-1408FS controller
Y-factor measurement is done in blocks of frequency.
At the end of cycle, change frequency to Fneutral and put in ambload

LM34 temperature sensor is added to measure ambient temperature.
Sensor is connected to Channel 3 of ADC

'''
import math
import visa
import time
import socket
import sys
import UniversalLibrary as ul

t0 = time.time()

BoardNum = 0        #Board number of USB-1408FS controller
Cbit     = 7        #Control bit is A7
ambload  = 0
coldload = 1
Nfblock  = 10        #Y factor done over blocks of frequency with Nfblock points
Tchannel = 3        #temp sensor is connected to this ADC channel

loadSwitchDelay = 1.0 # Time to wait for load to switch and power to settle
Tamb = 295.0          # Hot load temperature
Tcold = 78.5        # Cold load temperature

PM_ADDRESS='GPIB::12'
FILTER_IP='169.254.59.19'
FILTER_PORT=5025
F_neutral=11         #Freq (GHz) returned to at the end

pm=visa.instrument(PM_ADDRESS) #connect to power meter
visa.vpp43.set_attribute(pm.vi,visa.VI_ATTR_TERMCHAR_EN,visa.VI_TRUE)
pm.write('9A+V')

#set up socket to connect to filter
sock = socket.socket( socket.AF_INET, # Internet
                      socket.SOCK_DGRAM ) # UDP

def Tmeasure():
    Tscal = 21.5             #Temp in C at which sensor is calibrated
    Vscal = 0.724            #Sensor calibration voltage at Tscal
    Trange = ul.BIP5VOLTS
    sum1 = 0.0
    sum2 = 0.0
    Ntemp= 16
    for i in range(Ntemp):
        val = ul.cbAIn(BoardNum, Tchannel, Trange)
        Tx  = ul.cbToEngUnits(BoardNum, Trange, val)
        sum1 += Tx
        sum2 += Tx*Tx
    meanT = sum1/Ntemp
    sigmT = math.sqrt(sum2/Ntemp-meanT*meanT)
    print 'Sensor data: Vsensor = '+ str(meanT) + '\t Sigma = '+ str(sigmT)
    Tdata = ((meanT-Vscal)*100/1.8+Tscal)+273.15
    Treg  = math.floor(2*Tdata+0.5)/2
    print 'This gives a measured temp of '+ str(Tdata) + 'K. Actual temp used is ' + str(Treg)
    return Treg


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


def Pblock (freqs):
    Plist=[]
    for f in freqs:
        sock.sendto('f'+str(1000*f),(FILTER_IP, FILTER_PORT))
        time.sleep(0.1)
        Plist.append(power())
    return Plist


def Yblock(freqs, start=ambload):
    '''Function to take the Y fact over a block of IF freqeuencies'''
    # Take initial block of data
    P1 = Pblock(freqs)
    # Switch the load
    if start==ambload:
        ul.cbDBitOut (BoardNum,ul.FIRSTPORTA,Cbit,coldload)
    else:
        ul.cbDBitOut (BoardNum,ul.FIRSTPORTA,Cbit,ambload)
    time.sleep(loadSwitchDelay)
    P2 = Pblock(freqs)

    if start==ambload:
        return [P1, P2]
    else:
        return [P2, P1]
    
def Yfactor(hot, cold):
    '''Calculate the Yfactor from two lists of data'''
    Yfact = []
    for i, x in enumerate(hot):
        try:
            Yfact.append(hot[i]/cold[i])
        except ValueError:
            Yfact.append(1.0)
    return Yfact


def Tnoise(Yfact, h=Tamb, c=Tcold):
    '''Calculate the Receiver noise from the Yfactor'''
    Tnoise = []
    for i, x in enumerate(Yfact):
        try:
            Tnoise.append((h-Yfact[i]*c)/(Yfact[i]-1))
        except ValueError:
            Tnoise.append(9999.9)
            
    return Tnoise

#main part of code

if len(sys.argv) >= 8:
    f = open(sys.argv[1],'w')
    startfreq = float(sys.argv[2])
    stopfreq  = float(sys.argv[3])
    step = float(sys.argv[4])
    incr = float(sys.argv[5])
    Tamb = float(sys.argv[6])
    Tcold = float(sys.argv[7])
else:
    print ('cmd line arguments: <out_file_name> <F1(GHz)> <F2(GHz)> <dF(G)> <incr[0]> <Tamb(K)> <Tcold(K)>')
    print ('input Tamb < 200 to use measured temperature from sensor')
    f = open(raw_input('Output file: '), 'w')
    startfreq = input('Minimum frequency (GHz): ')
    stopfreq  = input('Maximum frequency (GHz): ')
    step = input ('Frequency step (GHz): ')
    incr = input ('increment multiplier offset: (>=0): ')
    Tamb = input ('Amb load temp (K): ')
    Tcold = input ('Cold load temp (K): ')

if Tamb < 201:
    Tamb = Tmeasure()


#create list of frequencies
freq=[startfreq]
cfreq=startfreq
while cfreq<stopfreq-0.0001:
    cfreq=cfreq+step
    step=step*(1+incr)
    freq.append(cfreq)

    
print 'Total of ' + str(len(freq))+' frequency points. Actual end frequency: '+str(freq[-1])

# setup USB controller
ul.cbDConfigPort(BoardNum,ul.FIRSTPORTA,ul.DIGITALOUT)
ul.cbDBitOut (BoardNum,ul.FIRSTPORTA,Cbit,ambload)
Load = ambload
time.sleep(2)

Pon=[]
Poff=[]
Y=[]
Trx=[]
lastBlock = False
Nfreqs = len(freq)
Fcounter = 0

ul.cbDBitOut (BoardNum,ul.FIRSTPORTA,Cbit,ambload)  #always start with amb load
t1 = time.time()

while(True): # Loop over blocks

    if Fcounter+Nfblock > Nfreqs:
        freqs = freq[Fcounter:]
        lastBlock = True
    else:
        freqs = freq[Fcounter:Fcounter+Nfblock]

    Pdata = Yblock(freqs, start=Load)
    Pon.extend(Pdata[0])
    Poff.extend(Pdata[1])
    
    Yfact = Yfactor(Pdata[0], Pdata[1])
    Tn = Tnoise(Yfact)
    
    for i, x in enumerate(freqs):
        print "%.2f\t%.3e\t%.3e\t%.4f\t%.2f" % (freqs[i], Pdata[0][i], Pdata[1][i], Yfact[i], Tn[i])

    if Load == ambload:
        Load = coldload
    else:
        Load = ambload
    if lastBlock:
        break
    else:
        Fcounter += Nfblock

t2 = time.time()
# Calculate the final Yfactor and Tnoise
Y = Yfactor(Pon, Poff)
Trx = Tnoise(Y)

print '''Time taken:
    Initialization: %f
    Loop:           %f
''' % (t1-t0, t2-t1)


f.write("Tamb = %.1f\t Tcold = %.1f\n" %(Tamb,Tcold))
for i, x in enumerate(freq):
    f.write("%.2f\t%.3e\t%.3e\t%.4f\t%.2f\n" % (freq[i],Pon[i],Poff[i],Y[i],Trx[i]))
    
f.close()

sock.sendto('f'+str(1000*F_neutral),(FILTER_IP, FILTER_PORT))
ul.cbDBitOut (BoardNum,ul.FIRSTPORTA,Cbit,ambload)
time.sleep(2)
pp=power()
#print pp
pm.close()
print 'finished'

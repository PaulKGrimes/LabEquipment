# PyVVM_VNA
#
# Paul Grimes, July 2014
#
# A script to operate the VVM in conjunction with two synthesizers as a high frequency VNA
# Uses pyvisa based modules to control each of the HP 8508A VVM, HP 83630A and Agilent E8256D
#
# Measurement configuration data is read from a .use file specified on the command line

usageStr = '''Usage:
> python PyVVM_VNA.py <usefile> <filename>
'''

import HP8508A
import HP83630A
import AgilentE8257D
import readUseFile
import sys
import numpy as np
import time
import skrf

# Read the command line parameters to get the use file and the output file
if len(sys.argv) < 3:
    sys.exit(usageStr)
    
usefile = sys.argv[1]
outfile = sys.argv[2]


# Read the use file
options = readUseFile.readUseFile(usefile)

# Set up the measurement
Fstart = options['Fstart']
Fstop = options['Fstop']
Fstep = options['Fstep']

settleTime = options['SettleTime']
measureTime = options['MeasureTime']

loMult = options['LOMultiplier']
rfMult = options['SourceMultiplier']

# Calculate the frequency points
# - Calculate the frequency points at the lowest frequency in use to avoid rounding errors
if loMult > rfMult:
    mult = rfMult
else: # loMult <= rfMult
    mult = loMult

fstart = round(Fstart/1e9/mult, 6)*1e9*mult
fstop = round(Fstop/1e9/mult, 6)*1e9*mult
fstep = round(Fstep/1e9/mult, 6)*1e9*mult

freqs = np.arange(fstart, fstop+fstep, fstep)

# Set up the VVM
vvm = HP8508A.HP8508A()

origVVMaverage = vvm.getAveraging()

vvm.setTransmission()
vvm.setFormatLog()
vvm.setTriggerBus()

vvm.setAveraging(options['Averaging'])


# Set up the Source VNA
rf = AgilentE8257D.AgilentE8257D()


rfSourceFreq = fstart/rfMult

origRFFreq = rf.getFreq()
origRFAmp = rf.getAmp()

rf.setExtRefAuto()
rf.setAmp(options['SourcePower'])
rf.setFreq(rfSourceFreq)


# Set up the LO Synth
lo = HP83630A.HP83630A()

loOffset = options['LOOffset']/loMult
loSourceFreq = fstart/loMult + loOffset

origLOFreq = lo.getFreq()
origLOAmp = lo.getAmp()

lo.setAmp(options['LOPower'])
lo.setFreq(loSourceFreq)

# Create the network to store the data in
net = skrf.Network()
net.frequency.unit = "Hz"
net.f = freqs
net.s = np.ndarray((len(net.f), 1, 1))


for i, f in enumerate(freqs):
    # Set synth frequencies
    rfSourceFreq = f/rfMult
    loSourceFreq = f/loMult + loOffset
    lo.setFreq(loSourceFreq)
    rf.setFreq(rfSourceFreq)
    
    # Wait to settle
    time.sleep(settleTime)
    
    # Trigger reading
    vvm.trigger()
    
    # Wait to settle
    time.sleep(measureTime)
    
    # Get data
    try:
        data = vvm.getTransmission()
    except HP5808.pyvisa.VisaIOError:
        print "# Could not get data at %.2f GHz"
        data = [0.0, 0.0]
    
    print f/1e9, rfSourceFreq/1e9, loSourceFreq/1e9, data[0], data[1]
    
    net.s[i,0,0] = skrf.dbdeg_2_reim(data[0],data[1])
    
net.frequency.unit = "GHz"
net.write_touchstone(filename=outfile)

# Set the synths back to the original frequencies and set VVM to free run
vvm.setTriggerFree()
vvm.setAveraging(origVVMaverage)
rf.setFreq(origRFFreq)
rf.setAmp(origRFAmp)
lo.setFreq(origLOFreq)
lo.setAmp(origLOAmp)
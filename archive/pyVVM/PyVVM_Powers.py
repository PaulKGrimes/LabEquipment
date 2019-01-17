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
rfMult = options['SourceMultiplier']
loMult = options['LOMultiplier']

Fstart = options['Fstart']
Fstop = options['Fstop']
Fstep = options['Fstep']

settleTime = options['SettleTime']
measureTime = options['MeasureTime']

# Calculate the frequency points
# - Calculate the frequency points at the lowest frequency in use to avoid rounding errors
if loMult > rfMult:
	mult = rfMult
else: # loMult <= rfMult
	mult = loMult

fstart = round(Fstart/1e9/mult, 5)*1e9*mult
fstop = round(Fstop/1e9/mult, 5)*1e9*mult
fstep = round(Fstep/1e9/mult, 5)*1e9*mult

freqs = np.arange(fstart, fstop+fstep, fstep)
	
# Set up the VVM
vvm = HP8508A.HP8508A()
vvm.setTransmission()
vvm.setFormatLog()
vvm.setTriggerBus()

origVVMaverage = vvm.getAveraging()
vvm.setAveraging(options['Averaging'])


# Set up the Source VNA
rf = AgilentE8257D.AgilentE8257D()

rfMult = options['SourceMultiplier']
rfSourceFreq = Fstart/rfMult

origRFFreq = rf.getFreq()
origRFAmp = rf.getAmp()

rf.setExtRefAuto()
rf.setAmp(options['SourcePower'])
rf.setFreq(rfSourceFreq)


# Set up the LO Synth
lo = HP83630A.HP83630A()

loMult = options['LOMultiplier']
loOffset = options['LOOffset']/loMult
loSourceFreq = Fstart/loMult + loOffset

origLOFreq = lo.getFreq()
origLOAmp = lo.getAmp()

lo.setAmp(options['LOPower'])
lo.setFreq(loSourceFreq)

# Create the array for the data.
outdata = np.ndarray((len(freqs), 3))

for i, f in enumerate(freqs):
	# Set synth frequencies
	rfSourceFreq = f/rfMult
	loSourceFreq = f/loMult + loOffset
	lo.setFreq(loSourceFreq)
	rf.setFreq(rfSourceFreq)
	
	loFreq = lo.getFreq()
	rfFreq = rf.getFreq()
	
	# Wait to settle
	time.sleep(settleTime)
	
	# Trigger reading
	vvm.trigger()
	
	# Wait to settle
	time.sleep(measureTime)
	
	# Get the data
	datastr = vvm.getData("APOW,BPOW")
	
	data = datastr.split(";")
	
	
	print f/1e9, rfFreq/1e9, loFreq/1e9, data[0], data[1]
	
	outdata[i] = [f, float(data[0]), float(data[1])]
	
# Save the data
np.savetxt(outfile, outdata, delimiter=",")

# Set the synths back to the original frequencies and set VVM to free run
vvm.setTriggerFree()
vvm.setAveraging(origVVMaverage)
rf.setFreq(origRFFreq)
rf.setAmp(origRFAmp)
lo.setFreq(origLOFreq)
lo.setAmp(origLOAmp)
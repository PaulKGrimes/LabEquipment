# BeamScanner.py
#
# Paul Grimes - Jan 2015
#
# Python script to operate the SAO beam scanning system consisting of
# the Unidex 11 motion controller, HP vector voltmeter and two synth
# sources.
#
# Based on vvm2008.cpp by Edward Tong.
#
# Reads instructions from scan.use, in a similar format to scan2.use files
# for vvm2008
#
# v2 - Nov 2015 - updated to work with new PyVISA API and changes required in the four instrument drivers
#
from parse import parse

import pyvisa
import HP8508A
import AgilentE8257D
import HP83630A
import Unidex11
import time
import sys
import numpy
from datetime import datetime
#import gaussfitter as gf

class BeamScanner:
    def __init__(self):
        self.VectorVM = None
        self.RFSource = None
        self.LOSource = None
        self.Scanner = None
        
    
    def readParameterFile(self, fileName="scan2.use"):
        """Read the parameter file <fileName>
        
        File should be in format:
        <output filename> 
        """
        f = open(fileName)
        
        self.DataFileName = parse("{:^}", f.next().split("!")[0])[0]
        self.TblFileName = parse("{:^}", f.next().split("!")[0])[0]
        self.Uscan, self.Vscan = parse("{:^d} {:^d}",f.next().split("!")[0])
        self.Ustep, self.Vstep = parse("{:^d} {:^d}", f.next().split("!")[0])
        self.Averaging = parse("{:^d}", f.next().split("!")[0])[0]
        self.UcenterSearch, self.VcenterSearch  = parse("{:^d} {:^d}", f.next().split("!")[0])
        self.speed = parse("{:^d}", f.next().split("!")[0])[0]
        self.pol = parse("{:^}", f.next().split("!")[0])[0]
        self.UCalCenter, self.VCalCenter = parse("{:^d} {:^d}", f.next().split("!")[0])
        self.cs = parse("{:^}", f.next().split("!")[0])[0]
        self.ang = parse("{:^d}", f.next().split("!")[0])[0]
        self.freq = parse("{:^f}", f.next().split("!")[0])[0]*1e9
        self.multiply = parse("{:^d}", f.next().split("!")[0])[0]
        self.offset = parse("{:^f}", f.next().split("!")[0])[0]*1e6
        self.harmonic = parse("{:^d}", f.next().split("!")[0])[0]
        
        f.close()
        
        if self.cs == 'C' or self.cs == 'c':
            self.centering = True
        else:
            self.centering = False
            
        if self.pol == 'X':
            self.crossPol = True
        else:
            self.crossPol = False
        self.sideband = numpy.sign(self.offset)
        self.settlingTime = 0.01
        self.Ucenter = 0
        self.Vcenter = 0
        
    
    def initVectorVM(self):
        """Initialize communications with the Vector Voltmeter"""
        self.VectorVM.setTransmission()
        self.VectorVM.setFormatLog()
        #print(self.VectorVM.format)
        
    def setUpVectorVM(self):
        """Set parameters read from parameter file in VectorVM"""
        self.VectorVM.setAveraging(self.Averaging)
    
    def measure(self):
        """Record data from the Vector Voltmeter"""
        amp, phase = self.VectorVM.getTransmission()
        
        return amp, phase*self.sideband
    
    
    def setFrequency(self):
        """Set the sources to correct frequencies"""
        RFfreq = self.freq/self.multiply
        if self.sideband == 1:
            LOfreq = (self.freq+self.offset)/self.harmonic
        else:
            LOfreq = (self.freq-self.offset)/self.harmonic
        
        self.RFSource.setFreq(RFfreq)
        self.LOSource.setFreq(LOfreq)

    def settle(self, t):
        """Wait for the system to stabilize"""
        time.sleep(t)

    
    def initScanner(self):
        """Initialize the Unidex11"""
        self.Scanner.initialize()
        
    def setUpScanner(self):
        """Set parameters from the file to the scanner"""
        self.Scanner.setSpeed(self.speed)
        self.Scanner.setAbsolute()
        self.Scanner.waitForStop()
        
        
    def findCenter(self):
        """Find the center of the beam"""
        scanPts = self.makeScanPts(2*self.UcenterSearch+1, 2*self.VcenterSearch+1, self.Ustep/2., self.Vstep/2.)
        data = self.rasterScan(scanPts)
        self.Ucenter, self.Vcenter = self.peakSearch(data)
        return data
        
    def makeScanPts(self, Usize, Vsize, Ustep, Vstep, Uoffset = 0, Voffset = 0):
        """Make a rectangular grid of U, V points to be visited by the scan"""
        
        Ustart = -numpy.floor((Usize-1)/2.*Ustep) + Uoffset
        Ustop = numpy.ceil((Usize-1)/2.*Ustep) + Uoffset + 1
        Vstart = -numpy.floor((Vsize-1)/2.*Vstep) + Voffset
        Vstop = numpy.ceil((Vsize-1)/2.*Vstep) + Voffset + 1
        
        # Make the points array
        scanPts = numpy.mgrid[Ustart:Ustop:Ustep, Vstart:Vstop:Vstep]
        scanPts = numpy.rollaxis(scanPts, 0, start = 3)
        
        return scanPts
    
    
    def takeData(self, v, u):
        """Move to (u,v) and take a VVM measurement"""
        #print "Taking data at %d, %d" % (u, v)
        self.Scanner.move((u/5., v/5.))  # Scanner steps are in 5 micron increments
        self.settle(self.settlingTime)
        amp, phase = self.measure()
        #print amp, phase
        
        return amp, phase
    
    
    def rasterScan(self, scanPts, saveTxt = False, takeCal = False, crossPol = False):
        """Make a raster scan of the U,V points in scanpts.  Take a calibration point
        at the middle of each row
        
        Returns a data set consisting of the U, V coordinates and Amplitude and Phase
        at each point"""
        #get size of the scan region
        Uscan, Vscan, w = scanPts.shape
        middle = Vscan/2
        data = numpy.empty((Uscan, Vscan, 6))
        calData = numpy.empty((Vscan, 3))
        
        initAmp, initPhase = self.takeData(self.Ucenter, self.Vcenter)
        print("Initial CoPol amplitude and phase: %f dB, %f deg" % (initAmp, initPhase))
        
        if crossPol:
            temp = raw_input('Adjust probe to CrossPol plane')
            
        initCalAmp, initCalPhase = self.takeData(self.UCalCenter, self.VCalCenter)
        
        print("Initial Calibration amplitude and phase: %f dB, %f deg" % (initCalAmp, initCalPhase))
        
        for r, row in enumerate(scanPts):
            # Reverse direction for odd rows (remember first row is r = 0)
            reverse = False
            if r % 2 == 1: # Odd row
                row = numpy.flipud(row)
                reverse = True
            # Iterate through the row
            for c, col in enumerate(row):
                amp, phase = self.takeData(col[0], col[1])
                if reverse:
                    C = Vscan - c - 1
                else:
                    C = c
                data[r,c,:] = numpy.array((C, r, col[1]/1000., col[0]/1000., amp-initAmp, phase-initPhase))
                # If we're at the middle, take a calibration point
                if c == middle and takeCal:
                    calAmp, calPhase = self.takeData(self.UCalCenter, self.VCalCenter)
                    calData[r, :] = numpy.array((r, calAmp-initCalAmp, calPhase-initCalPhase))
                    print("Calibration amplitude and phase - row %d:  %f dB, %f deg" % (r, calAmp-initCalAmp, calPhase-initCalPhase))
            if saveTxt:        
                # At the end of each row, write out data acquired so far to data and caldata files
                numpy.savetxt(self.DataFileName, data[0:r+1].reshape(Vscan*(r+1),6), fmt='%4.0f\t%4.0f\t%8.3f\t%8.3f\t%8.3f\t%8.3f') 
                if takeCal:
                    numpy.savetxt(self.TblFileName, calData[0:r+1], fmt='%4.0f\t%8.3f\t%8.3f')
        
        # Return to the cal center and take a final point
        if crossPol:
            amp, phase = self.takeData(self.UCalCenter, self.VCalCenter)
            print("Final CrossPol amplitude and phase: %f dB, %f deg" %(amp, phase))
            temp = raw_input('Adjust probe to CoPol plane')
        
        amp, phase = self.takeData(self.Ucenter, self.Vcenter)
        
        print("Final CoPol amplitude and phase: %f dB, %f deg" %(amp, phase))
        
        return data
               
    def peakSearch(self, data):
        """Find the amplitude peak in the supplied data set, returning the U and V 
        coordinates of the peak"""
        # Find the peak amplitude in the data
        u, v = numpy.argmax(data[:,:,5])
        U = data[u,v,3]
        V = data[u,v,4]
        return U, V
        
if __name__ == "__main__":
    # Create the BeamScanner object
    bs = BeamScanner()
    
    # Create the pyvisa ResourceManager and use it create the instruments
    rm = pyvisa.ResourceManager()
    bs.VectorVM = HP8508A.HP8508A(rm.open_resource("GPIB::8"))
    bs.RFSource = AgilentE8257D.AgilentE8257D(rm.open_resource("GPIB::18"))
    bs.LOSource = HP83630A.HP83630A(rm.open_resource("GPIB::19"))
    bs.Scanner = Unidex11.Unidex11(rm.open_resource("GPIB::2"))
    
    if len(sys.argv) == 2:
        bs.readParameterFile(fileName = sys.argv[1])
    else:
        bs.readParameterFile()
    
    bs.initVectorVM()
    bs.setUpVectorVM()
    bs.setFrequency()
    print("Set RF Frequency to %.0f GHz" % (bs.freq/1e9))
    print("Init Scanner")
    bs.initScanner()
    print("Set Up Scanner")
    bs.setUpScanner()
    print("Move Scanner to (0,0)")
    bs.Scanner.move((0,0))
    #print("Settling")
    #bs.settle(5*60)

    
    print("Instruments Initialized")
    if bs.centering:
        print("Finding Center of Beam")
        bs.findCenter()
    
    t0 = datetime.now()
    print("Starting Raster Scan at " + str(t0))
    scanPts = bs.makeScanPts(bs.Uscan, bs.Vscan, bs.Ustep, bs.Vstep, Uoffset = bs.Ucenter, Voffset = bs.Vcenter)
    bs.rasterScan(scanPts, saveTxt = True, takeCal = True, crossPol = bs.crossPol)
    print("Raster Scan completed at " + str(datetime.now()) + " in " + str(datetime.now()-t0))
    
    

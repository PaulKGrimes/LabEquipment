#############################################################
# Beamscanner class and program                             #
#                                                           #
# Larry Gardner, July 2018                                  #
#############################################################

import visa
import os
import time
import sys

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.mlab import griddata
import numpy.polynomial.polynomial as poly

import HP8508A
import HMCT2240
import MSL

class Beamscanner:
    def __init__(self):

        # Instruments
        self.vvm = None
        self.msl_x = None
        self.msl_y = None
        self.RF = None
        self.LO = None

    def initTime(self):
        # Assigns start time
        self.start_time = time.time()
        print("Starting...\n")

    def readUSE(self, useFile="Beamscan.use"):
        # If use file is entered, use that file instead of default.
        if len(sys.argv) > 1:
            useFile = sys.argv[1]
        else:
            useFile = "Beamscan.use"
        print("USE file: ",useFile)

        # Reads USE file for parameters
        f = open(useFile, 'r')
        lines = f.readlines()
        f.close()

        self.save_name = lines[0].split("!")[0]
        self.Range = float(lines[1].split("!")[0])
        self.Res = float(lines[2].split("!")[0])
        self.Average = int(lines[3].split("!")[0])
        self.Format = lines[4].split("!")[0]
        self.RFfreq = float(lines[5].split("!")[0])
        self.LOfreq = float(lines[6].split("!")[0])
        self.RFpow = float(lines[7].split("!")[0])
        self.LOpow = float(lines[8].split("!")[0])
        self.conv_factor = int(lines[9].split("!")[0])
        self.searchCenter = (float(lines[10].split("!")[0].split(",")[0]), float(lines[10].split("!")[0].split(",")[0]))
        self.searchRange = float(lines[11].split("!")[0])
        self.searchRes = float(lines[12].split("!")[0])
        self.velocity = float(lines[13].split("!")[0])
        self.accel = float(lines[14].split("!")[0])
        
        self.setStep(self.Res)


    def initGPIB(self):
        """Initialize PyVisa and check it's working.

        "no langid" errors are likely a permissions issue - make sure the current user
        has access to usb port and that linux-gpib is configured with gpib-config --minor=0.

        This can be done automatically at boot with udev rules

        see http://askubuntu.com/questions/705409/udev-rule-to-run-gpib-config and
        https://github.com/pyvisa/pyvisa/issues/212
        """
        # Lists available resources
        rm = visa.ResourceManager('@py')
        try:
            lr = rm.list_resources()
        except ValueError:
            print("pyvisa list_resources failed - likely you have a permissions issue.  See Beamscanner.py Beamscanner.initGPIB() source for solutions")
        print("GPIB devices configured. \nAvailable Resources: "+str(lr))
        return rm

    def initVVM(self, format = "LOG,POLAR"):
        # Initializes voltmeter parameters
        self.vvm.setTransmission()
        self.vvm.setFormat(self.Format)
        self.vvm.setAveraging(self.Average)
        self.vvm.setTriggerBus()
        print("\nVVM format: {}".format(str(self.vvm.getFormat())))

    def initSG(self):
        # Initializes signal generator paramters
        self.RF.setFreq(self.RFfreq)
        self.RF.setPower(self.RFpow)
        self.RF.on()
        self.LO.setFreq(self.LOfreq)
        self.LO.setPower(self.LOpow)
        self.LO.on()
        print("RF: Frequency = {:f} Hz, Power = {:f} dBm".format(self.RFfreq, self.RFpow))
        print("LO: Frequency = {:f} Hz, Power = {:f} dBm".format(self.LOfreq, self.LOpow))

    def initMSL(self):
        # Sets MSL home positions to central position to synchronize between tests
        self.msl_x.center()
        self.msl_y.center()
        
        # Sets MSL motion parameters
        self.msl_x.setAccel(self.accel)
        self.msl_x.setDecel(self.accel)
        self.msl_x.setVelMax(self.velocity)
        self.msl_y.setAccel(self.accel)
        self.msl_y.setDecel(self.accel)
        self.msl_y.setVelMax(self.velocity)
        
    def setRange(self, Range):
        # Range of travel stage motion (50x50mm)
        self.pos_x_max = int((Range/2) * self.conv_factor) # 25 mm * 5000 microsteps per mm
        self.pos_y_max = self.pos_x_max
        self.pos_x_min = -self.pos_x_max
        self.pos_y_min = self.pos_x_min

    def setStep(self, res):
        # Sets step size for position increments
        # Converts resolution in mm to microsteps for MSL
        self.Step = int(res * self.conv_factor)
        
        
    def findMaxPos(self):
        # Finds the X and Y positions of maximum voltmeter amplitude
        # Function only used in "findCenter"
        max_amp = max(self.vvm_data, key = lambda x: x[0])
        index = self.vvm_data.index(max_amp)
        self.pos_x_center = int(self.pos_data[index][0])
        self.pos_y_center = int(self.pos_data[index][1])
    
    
    def findCenter(self, minRes = 0.1):
        # Runs scan over area & finds maximum amplitude peak.
        # Begins at arbitrary position and decreases range and resolution with each iteration.

        print("\nFinding center...")
        
        res = bs.searchRes
        Range = bs.searchRange
        self.pos_x_center = bs.searchCenter[0]
        self.pos_y_center = bs.searchCenter[1]
        
        while res >= minRes:
            self.setRange(Range)
            self.setStep(res)

            self.moveToCenter()
            self.initScan(Range)
            self.scan(res)
            self.findMaxPos()

            Range = Range / 5
            res = Range / 5

        print("\n")

    def moveToCenter(self):
        # Moves MSL's to center position and sets new home position
        self.msl_x.moveAbs(int(self.pos_x_center * self.conv_factor))
        self.msl_y.moveAbs(int(self.pos_y_center * self.conv_factor))
        self.msl_x.hold()
        self.msl_y.hold()
        self.msl_x.zero()
        self.msl_y.zero()

    def initScan(self, Range):
        # Get range parameters for scan
        self.setRange(Range)
        # Moves to minimum position in range to begin scan
        self.msl_x.moveAbs(self.pos_x_min)
        self.msl_y.moveAbs(self.pos_y_min)
        self.msl_x.hold()
        self.msl_y.hold()

        # Gets initial position
        self.pos_x = int(self.msl_x.getPos())
        self.pos_y = int(self.msl_y.getPos())
        
        # Create numpy arrays to store the data
        x = np.arange(self.pos_x_min, self.pos_x_max+self.Step, self.Step, dtype=float)
        y = np.arange(self.pos_y_min, self.pos_y_max+self.Step, self.Step, dtype=float)
        self.xVals, self.yVals = np.meshgrid(x, y)
        
        # reverse everyother line in self.xVals
        self.xVals[1::2,:] = self.xVals[1::2,::-1]
        
        self.transVals = np.zeros_like(self.xVals, dtype=complex)

        # VVM ready to begin collecting data
        self.vvm.trigger()

        
    def getTransmission(self):
        """Get the transmission from the VVM.  Loop if necessary to avoid
        one-off time out errors"""
        retry = 0
        while True:
            try:
                trans = self.vvm.getTransmission()
                break
            except visa.VisaIOError:
                print("Visa Timeout Error, retrying twice")
                if retry < 2:
                    retry +=1
                    pass
                else:
                    # Re-raise the exception
                    raise
                    break
            except ValueError:
                pass
        return trans
        
    
    def scan(self, res):
        """Scan over the meshgrids of the stored xVals and yVals, and record data
        in trans.
        
        initScan will set up the xVals and yVals array as a regular raster scan grid.
        however, this methods will work with any scan pattern defined in those variables."""
        
        for i, x in enumerate(self.xVals.ravel()):
            y = self.yVals.ravel()[i]
            
            # Move to position
            self.msl_x.moveAbs(x*self.conv_factor)
            self.msl_y.moveAbs(y*self.conv_factor)
            self.msl_x.hold()
            self.msl_y.hold()
            
            # Gets positions and transmissions from VVM and loops in case of error
            self.xVals.ravel()[i] = self.msl_x.getPos()
            self.yVals.ravel()[i] = self.msl_y.getPos()
            self.trans.ravel()[i] = self.getTransmission()
            print("    X: {:.3f}, Y: {:.3f}".format(self.xVals.ravel()[i]/self.conv_factor, self.xVals.ravel()[i]/self.conv_factor))
            print("    {:f} dB, {:f} deg".format(20*np.log10(transVals.ravel()[i]), np.degrees(np.angle(transVals.ravel()[i]))))
            
    def endSG(self):
        # Turns off signal generator output
        self.RF.off()
        self.LO.off()

    def spreadsheet(self):
        print("Writing data to spreadsheet...")

        # Creates document for libre office
        out = open(self.save_name, 'w')

        out.write("Time (s) \tX Position (mm) \tY Position (mm) \tAmplitude (dB) \tPhase (deg)\n")

        x_data = []
        y_data = []
        amp_data = []
        phase_data = []

        for i in range(len(self.pos_data)):
            x_data.append(self.pos_data[i][0])
            y_data.append(self.pos_data[i][1])

            # Reformats VVM data if not already in proper form
            if type(self.vvm_data[i]) == tuple:
                amp_data.append(self.vvm_data[i][0])
                phase_data.append(self.vvm_data[i][1])
            elif type(vvm_data[i]) == str:
                amp_data.append(float(self.vvm_data[i].split(",")[0]))
                phase_data.append(float(self.vvm_data[i].split(",")[1]))

            # Writes data to spreadsheet
            out.write(str(self.time_data[i]) + '\t' + str(x_data[i]) + '\t' + str(y_data[i])
                          + '\t' + str(amp_data[i]) + '\t' + str(phase_data[i]) + '\n')

        out.close()

    def contour_plot(self, file_name):
        # Makes contour plot given spreadsheet data format
        x_data = []
        y_data = []
        amp_data = []

        f = open(str(file_name), 'r')
        lines = f.readlines()
        f.close()

        for i in range(len(lines) - 1):
            x_data.append(float(lines[i+1].split()[1]))
            y_data.append(float(lines[i+1].split()[2]))
            amp_data.append(float(lines[i+1].split()[3]))

        pos_x_min = min(x_data)
        pos_x_max = max(x_data)
        pos_y_min = min(y_data)
        pos_y_max = max(y_data)

        xi = np.linspace(pos_x_min, pos_x_max, 1000)
        yi = np.linspace(pos_y_min, pos_y_max, 1000)
        zi = griddata(x_data, y_data, amp_data, xi, yi, interp = "linear")

        CS = plt.contour(xi, yi, zi)
        plt.clabel(CS, inline = 1)
        plt.xlabel("X Position (mm)")
        plt.ylabel("Y Position (mm)")
        matplotlib.rcParams['contour.negative_linestyle'] = 'solid'
        plt.xlim(pos_x_min, pos_x_max)
        plt.ylim(pos_y_min, pos_y_max)
        plt.title("Amplitude vs. Position")
        plt.show()

    def time_plot(self, file_name):
        # Makes time vs amplitude & phase plot given beamscanner data format, not spreadsheet data format
        amp_data = []
        phase_data = []

        f = open(str(file_name), 'r')
        lines = f.readlines()
        f.close()

        for i in range(len(lines) - 1):
            amp_data.append(float(lines[i+1].split()[3]))
            phase_data.append(float(lines[i+1].split()[4]))

        fig, ax1 = plt.subplots()

        ax1.plot(self.time_data, amp_data, 'bD--', label = "Amplitude (dB)")
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Amplitude (dB)', color='b')
        ax1.tick_params('y', colors='b')
        plt.legend(loc = "upper left")

        ax2 = ax1.twinx()
        ax2.plot(self.time_data, phase_data, 'r^-', label = "Phase (deg)")
        ax2.set_ylabel('Phase (deg)', color='r')
        ax2.tick_params('y', colors='r')
        plt.legend(loc = "upper right")

        fig.tight_layout()
        plt.show()

    def y_plot(self, file_name):
        # Makes plot of amplitude & phase vs. Y-position along X = 0 plane
        x_data_all = []
        y_data_all = []
        y_data = []
        amp_data_all = []
        amp_data = []
        phase_data_all = []
        phase_data = []

        f = open(str(file_name), 'r')
        lines = f.readlines()
        f.close()

        for i in range(len(lines) - 1):
            x_data_all.append(float(lines[i+1].split()[1]))
            y_data_all.append(float(lines[i+1].split()[2]))
            amp_data_all.append(float(lines[i+1].split()[3]))
            phase_data_all.append(float(lines[i+1].split()[4]))

        for i in range(len(x_data_all)):
            if x_data_all[i] == 0:
                y_data.append(y_data_all[i])
                amp_data.append(amp_data_all[i])
                phase_data.append(phase_data_all[i])

        fig, ax1 = plt.subplots()

        x_new = np.linspace(y_data[0], y_data[-1], num=len(y_data)*10)

        coefs_amp = poly.polyfit(y_data, amp_data, 2)
        fit_amp = poly.polyval(x_new, coefs_amp)
        ax1.plot(y_data, amp_data, 'bD', label = "Amp (meas)")
        ax1.plot(x_new, fit_amp, 'b--', label = "Amp (fitted)")
        ax1.set_xlabel("Y position (mm)")
        ax1.set_ylabel("Amplitude (dB)", color='b')
        ax1.tick_params('y', colors='b')
        ax1.legend(loc = "upper left")

        coefs_phase = poly.polyfit(y_data, phase_data, 2)
        fit_phase = poly.polyval(x_new, coefs_phase)
        ax2 = ax1.twinx()
        ax2.plot(y_data, phase_data, 'r^', label = "Phase (meas)")
        ax2.plot(x_new, fit_phase, 'r-', label = "Phase (fitted)")
        ax2.set_ylabel('Phase (deg)', color='r')
        ax2.tick_params('y', colors='r')
        ax2.legend(loc = "upper right")

        fig.tight_layout()
        plt.show()

    def x_plot(self, file_name):
        # Makes plot of amplitude & phase vs. X-position along Y = 0 plane
        x_data_all = []
        y_data_all = []
        x_data = []
        amp_data_all = []
        amp_data = []
        phase_data_all = []
        phase_data = []

        f = open(str(file_name), 'r')
        lines = f.readlines()
        f.close()

        for i in range(len(lines) - 1):
            x_data_all.append(float(lines[i+1].split()[1]))
            y_data_all.append(float(lines[i+1].split()[2]))
            amp_data_all.append(float(lines[i+1].split()[3]))
            phase_data_all.append(float(lines[i+1].split()[4]))

        for i in range(len(x_data_all)):
            if int(y_data_all[i]) == 0:
                x_data.append(x_data_all[i])
                amp_data.append(amp_data_all[i])
                phase_data.append(phase_data_all[i])

        fig, ax1 = plt.subplots()

        x_new = np.linspace(x_data[0], x_data[-1], num=len(x_data)*10)

        coefs_amp = poly.polyfit(x_data, amp_data, 2)
        fit_amp = poly.polyval(x_new, coefs_amp)
        ax1.plot(x_data, amp_data, 'bD', label = "Amp (meas)")
        ax1.plot(x_new, fit_amp, 'b--', label = "Amp (fitted)")
        ax1.set_xlabel("X position (mm)")
        ax1.set_ylabel("Amplitude (dB)", color='b')
        ax1.tick_params('y', colors='b')
        ax1.legend(loc = "upper left")

        coefs_phase = poly.polyfit(x_data, phase_data, 2)
        fit_phase = poly.polyval(x_new, coefs_phase)
        ax2 = ax1.twinx()
        ax2.plot(x_data, phase_data, 'r^', label = "Phase (meas)")
        ax2.plot(x_new, fit_phase, 'r-', label = "Phase (fitted)")
        ax2.set_ylabel('Phase (deg)', color='r')
        ax2.tick_params('y', colors='r')
        ax2.legend(loc = "upper right")

        fig.tight_layout()
        plt.show()


if __name__ == "__main__":

    # Begin
    bs = Beamscanner()
    bs.initTime()
    bs.readUSE()

    # Establishes instrument communication
    rm = bs.initGPIB()
    bs.vvm = HP8508A.HP8508A(rm.open_resource("GPIB0::8::INSTR"))
    bs.RF = HMCT2240.HMCT2240(rm.open_resource("GPIB0::30::INSTR"))
    bs.LO = HMCT2240.HMCT2240(rm.open_resource("GPIB0::23::INSTR"))
    bs.msl_x = MSL.MSL(rm.open_resource("ASRL/dev/ttyUSB0"), partyName="X")
    bs.msl_y = MSL.MSL(rm.open_resource("ASRL/dev/ttyUSB0"), partyName="Y")

    # Initializes instruments
    bs.initVVM()
    bs.initSG()
    bs.initMSL()

    # Find center of beam to calibrate to
#    bs.findCenter(minRes=0.5)

    # Preparing to scan
    print("Preparing for data ...")
#    bs.moveToCenter()
    bs.initScan(bs.Range)

    # Scanning
    print("\nCollecting data...")
    bs.scan(bs.Step)

    # Finished scanning
#    print("\nExecution time: " + str(time.time() - bs.start_time))
    # Don't turn off sig gens!
    # bs.endSG()

    # Writing to spread sheet
#    bs.spreadsheet()

#   print("Plotting data ...")
    # Plots position vs. amplitude contour plot
#   bs.contour_plot(bs.save_name)
    # Plots amplitude and phase vs. time
#    bs.time_plot(bs.save_name)
    # Plots amplitude and phase vs. y position for slice at center of beam
#    bs.y_plot(bs.save_name)
    # Plots amplitude and phase vs. X position for slice at center of beam
#    bs.x_plot(bs.save_name)

    print("\nEnd.")

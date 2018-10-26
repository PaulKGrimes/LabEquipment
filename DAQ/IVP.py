##################################################
#                                                #
# IV testing with Power Meter                                     #
#                                                #
# Larry Gardner, July 2018                       #
# Paul Grimes, August 2018                       #
##################################################

from __future__ import print_function, division

import sys
import os
import time
import visa
import numpy as np
import IV
import matplotlib.pyplot as plt
import PowerMeter as PM
import visa




class IVP(IV.IV):
    def __init__(self, use="IV.use", verbose=False):
        super().__init__(use, verbose)

        self.pm = None
        self.settleTime = 0.1

        self.initPM()

    def __delete__(self):
        self.endPM()
        super().__delete__()

    def readFile(self):
        super().readFile()
        self.pm_address = self._use_lines[16].split()[0]

    def initPM(self, pm_address=None):
        # Initializes Power Meter
        if pm_address==None:
            pm_address = self.pm_address

        try:
            rm = visa.ResourceManager()
            lr = rm.list_resources()
            if pm_address in lr:
                self.pm = PM.PowerMeter(rm.open_resource(pm_address))
                self.pm_address = pm_address
                if self.verbose:
                    print("Power Meter connected.\n")
            else:
                self.pm = None
                if self.verbose:
                    print("No Power Meter detected.\n")
        except gpib.GpibError:
            self.pm = None
            if self.verbose:
                print("GPIB Error connecting to Power Meter.\n")
        except:
            self.pm = None
            if self.verbose:
                print("Unknown Error connecting to Power Meter.\n")

    def bias(self, bias):
        """Short cut to set the bias point to <bias> mV and return the
        resulting bias point"""
        self.setBias(bias)
        data = self.getData()

        if self.verbose:
            print("New Bias Point: {:.4g} mV".format(bias))
            if len(data) == 3:
                print("  Voltage: {:.4g} mV, Current: {:.4g} mA, IF Power: {:.4g} W".format(data[0], data[1], data[2]))
            else:
                print("  Voltage: {:.4g} mV, Current: {:.4g} mA".format(data[0], data[1]))
        return data

    def getData(self):
        """Gets V, I and P (if PM present) data, and returns it as a tuple"""
        Vdata, Idata = super().getData()

        if self.pm != None:
            Pdata = self.pm.getData(rate="I")

            return Vdata, Idata, Pdata
        else:
            return Vdata, Idata


    def prepSweep(self):
        super().prepSweep()

        # Prepares for data collection
        self.Pdata = np.empty_like(self.BiasPts)


    def runSweep(self):
        if self.verbose:
            print("\nRunning sweep...")

        # Sets proper format for low and high channels to scan over
        channels = [self.V_channel, self.I_channel]
        low_channel, high_channel = min(channels), max(channels)

        if self.verbose:
            print("\tBias (mV)\tVoltage (mV)\tCurrent (mA)\tIF Power")

        for index, bias in enumerate(self.BiasPts):
            self.setBias(bias)

            #Collects data from scan
            data = self.getData()

            self.Vdata[index] = data[0]
            self.Idata[index] = data[1]
            if self.pm != None:
                self.Pdata[index] = data[2]
            else:
                self.Pdata[index] = 0.0

            if index%5 == 0 and self.verbose:
                print("\t{:10.6g}\t{:10.6g}\t{:10.6g}\t{:10.6g}".format(self.BiasPts[index], self.Vdata[index], self.Idata[index], self.Pdata[index]))


    def endPM(self):
        # Disconnects power meter
        if self.pm != None:
            self.pm.close()

    def spreadsheet(self):
        if self.verbose:
            print("\nWriting data to spreadsheet...")

        # Creates document for libre office
        out = open(self.save_name, 'w')

        # Writes data to spreadsheet
        # Write a header describing the data
        out.write("# Bias (mV)\t\tVoltage (mV)\t\tCurrent (mA)\t\tIF Power (W)\n")
        for i in range(len(self.Vdata)):
            out.write("{:10.6g},\t{:10.6g},\t{:10.6g},\t{:10.6g}\n".format(self.BiasPts[i], self.Vdata[i], self.Idata[i], self.Pdata[i]))

        out.close()

    def plotPV(self):
        # Plot PV curve
        self.ax2.plot(self.Vdata, self.Pdata, 'g-')
        self.ax2.set(ylabel="Power (W)")

    def plot(self, ion=True):
        """Plot the acquired data from the sweep.
        """
        if ion:
            plt.ion()
        self.fig, self.ax = plt.subplots()
        self.plotIV()
        self.ax2 = self.ax.twinx()
        self.plotPV()
        self.ax.set(title="PV Sweep")

        self.fig.show()

if __name__ == "__main__":
    # This code runs a sweep from <vmax> to <vmin> with stepsize <step> and
    # saves the data to <save_name>
    #
    # Usage: python3 <file.dat> <vmin> <vmax> <step> <*use file>

    test = IVP(verbose=True)

    if len(sys.argv) >= 5:
        test.save_name = sys.argv[1]
        test.vmin = float(sys.argv[2])
        test.vmax = float(sys.argv[3])
        test.step = float(sys.argv[4])
        if len(sys.argv) == 6:
            test.use = sys.argv[5]
            test.readFile()
            test.initDAQ()
    else:
        test.save_name = input("Output file name: ")
        test.vmin = float(input("Minimum voltage [mV]: "))
        test.vmax = float(input("Maximum voltage [mV]: "))
        test.step = float(input("Step [mV]: "))

    # Run a sweep
    test.sweep()

    # Output and plot data
    test.spreadsheet()
    plt.ion()
    test.plot()
    # Wait until the plot is done
    try:
        input("Press [enter] to continue.")
    except SyntaxError:
        pass


    # Close down the IV object cleanly, releasing the DAQ and PM
    del test

    print("End.")

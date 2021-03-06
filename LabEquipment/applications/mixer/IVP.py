#! /usr/bin/env python
##################################################
#                                                #
# IV testing with IF power from power meter or   #
# ADC                                            #
#                                                #
# Larry Gardner, July 2018                       #
# Paul Grimes, November 2018                     #
##################################################

from __future__ import print_function, division

import sys
import time
import visa
import numpy as np
import pprint

import matplotlib.pyplot as plt
import LabEquipment.drivers.Instrument.HP436A as PM

from LabEquipment.applications.mixer import _default_IVP_config
from LabEquipment.applications.mixer import IV


class IVP(IV.IV):
    """An object that can set and measure the bias on an SIS device, and measure
    the IF power with either a GPIB connected power meter or an analog power
    signal connected to the bias DAQ unit"""
    def __init__(self, config=None, configFile=None, verbose=False, vverbose=False):
        super().__init__(config=config, configFile=configFile, verbose=verbose, vverbose=vverbose)
        self.setConfig(_default_IVP_config.defaultConfig)

        if self.vverbose:
            print("IVP.__init__: Default Config Loaded: Current config:")
            pprint.pprint(self.config)

        if configFile != None:
            self.readConfig(configFile)
            if self.vverbose:
                print("IVP.__init__: Config Loaded from: {:s}".format(configFile))
                pprint.pprint(self.config)
        if config != None:
            if self.vverbose:
                print("IVP.__init__: Config passed to __init__:")
                pprint.pprint(config)

            self.setConfig(config)

            if self.vverbose:
                print("IVP.__init__: Config now:")
                pprint.pprint(self.config)

        if self.vverbose:
            print("IVP.__init__: Done setting configFile and config: Current config:")
            pprint.pprint(self.config)

        self.columnHeaders = "Bias (mV)\tVoltage (mV)\tCurrent (mA)\tIF Power"
        self.pm = None

        self.initPM()

    def __delete__(self):
        self.endPM()
        super().__delete__()

    def _applyConfig(self):
        super()._applyConfig()
        try:
            self.pm_address = self.config["power-meter"]["address"]
            if self.verbose:
                print("GPIB IF power meter configuration found")
            try:
                self.pm_averaging = self.config["power-meter"]["averaging"]
            except KeyError:
                self.pm_averaging = None
            try:
                self.pm_Navg = self.config["power-meter"]["Navg"]
            except KeyError:
                self.pm_Navg = 3
        except KeyError:
            try:
                self.pm_address = None
                self.pIn_channel = self.config["power-meter"]["channel"]
                self.pIn_gain = self.config["power-meter"]["gain"]
                self.pIn_offset = self.config["power-meter"]["offset"]
                if self.verbose:
                    print("Analog input IF power configuration found")
            except KeyError:
                if self.verbose:
                    print("No IF power configuration found")
            self.pm = None

    def initPM(self, pm_address=None):
        # Initializes Power Meter
        if pm_address==None:
            pm_address = self.pm_address

        if pm_address==None:
            # We don't have configuration for GPIB power meter, so we will
            # assume an analog signal is connected to the DAQ ADC input
            if self.verbose:
                print("No GPIB power meter configured, using ADC input {:d}".format(self.pIn_channel))
            return

        try:
            self.rm = visa.ResourceManager()
            lr = self.rm.list_resources()
            if pm_address in lr:
                self.pm = PM.PowerMeter(self.rm.open_resource(pm_address), averaging=self.pm_averaging, Navg=self.pm_Navg)
                self.pm_address = pm_address
                if self.verbose:
                    print("Power Meter connected on {:}.\n".format(self.pm_address))
            else:
                self.pm = None
                if self.verbose:
                    print("No Power Meter detected on {:}.\n".format(self.pm_address))
        except visa.VisaIOError:
            self.pm = None
            if self.verbose:
                print("GPIB Error connecting to Power Meter on {:}.\n".format(self.pm_address))
        except:
            self.pm = None
            if self.verbose:
                print("Unknown Error connecting to Power Meter on {:}.\n".format(self.pm_address))
                print("PM settings:")
                print("\tPM Averaging: {:}".format(self.pm_averaging))
                raise

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

        if self.pm != None:
            data = super().getData()
            Vdata = data[self.vIn_channel]
            Idata = data[self.iIn_channel]
            Pdata = self.pm.getData(rate="I")

        else:
            Vdata, Idata, Pdata = self.getDataAin()

        return Vdata, Idata, Pdata

    def getDataAin(self):
        """Get the data for bias and IF power from the DAQ"""
        data = self.getRawDataAin()

        # Get the output voltage/current data
        Vdata = self.calcV(data[self.vIn_channel])
        Idata = self.calcI(data[self.iIn_channel])
        Pdata = self.calcP(data[self.pIn_channel])

        return Vdata, Idata, Pdata

    def getRawDataAin(self):
        """Gets the voltages for the bias and power meter from the DAQ"""
        # Sets proper format for low and high channels to scan over
        channels = [self.vIn_channel, self.iIn_channel, self.pIn_channel]
        low_channel, high_channel = min(channels), max(channels)
        data = self.daq.AInScan(low_channel, high_channel, self.Rate, self.Navg)
        return np.mean(data[:, self.vIn_channel]), np.mean(data[:, self.iIn_channel]), np.mean(data[:, self.pIn_channel])

    def calcP(self, volts):
        """Convert ADC voltage to IF power"""
        return (volts - self.pIn_offset) / self.pIn_gain

    def prepSweep(self):
        super().prepSweep()

        # Prepares for data collection
        self.Pdata = np.empty_like(self.SweepPts)


    def runSweep(self):
        if self.verbose:
            print("\nRunning sweep...")

        if self.verbose:
            print("\t{:s}\n".format(self.columnHeaders))

        for index, bias in enumerate(self.SweepPts):
            self.setSweep(bias)

            #Collects data from scan
            data = self.getData()

            self.Vdata[index] = data[0]
            self.Idata[index] = data[1]
            if len(data) >= 3:
                self.Pdata[index] = data[2]
            else:
                self.Pdata[index] = 0.0

            if index%5 == 0 and self.verbose:
                print("\t{:.3f}\t\t{:.3f}\t\t{:.3f}\t\t{:.3g}".format(self.SweepPts[index], self.Vdata[index], self.Idata[index], self.Pdata[index]))


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
        out.write("# {:s}\n".format(self.columnHeaders))
        for i in range(len(self.Vdata)):
            out.write("{:.6g},\t{:.6g},\t{:.6g},\t{:.6g}\n".format(self.SweepPts[i], self.Vdata[i], self.Idata[i], self.Pdata[i]))

        out.close()

    def plotPV(self):
        # Plot PV curve
        self.ax2.plot(self.Vdata, self.Pdata, 'b-')
        self.ax2.set(ylabel="Power")
        self.ax2.set(title="IV Sweep")

    def plot(self, ion=True):
        """Plot the acquired data from the sweep.
        """
        self.fig, self.ax = plt.subplots()
        self.plotIV()
        self.ax2 = self.ax.twinx()
        self.plotPV()
        plt.show()

if __name__ == "__main__":
    # This code runs a sweep from <max> to <min> with stepsize <step> and
    # saves the data to <save_name>
    #
    # Usage: python3 <file.dat> <min> <max> <step> <*use file>

    test = IVP(verbose=True, vverbose=True)

    if len(sys.argv) >= 5:
        if len(sys.argv) == 6:
            test.readFile(sys.argv[5])
            test.initDAQ()
        test.save_name = sys.argv[1]
        test.sweepmin = float(sys.argv[2])
        test.sweepmax = float(sys.argv[3])
        test.step = float(sys.argv[4])
    else:
        test.save_name = input("Output file name: ")
        test.sweepmin = float(input("Minimum voltage [mV]: "))
        test.sweepmax = float(input("Maximum voltage [mV]: "))
        test.step = float(input("Step [mV]: "))

    # Run a sweep
    test.sweep()

    # Output and plot data
    test.spreadsheet()
    test.plot()
    # Wait until the plot is done
    try:
        save = input("Save Plot? [Y/N]")
        if save =="Y":
            test.savefig()
    except SyntaxError:
        pass


    # Close down the IV object cleanly, releasing the DAQ and PM
    del test

    print("End.")

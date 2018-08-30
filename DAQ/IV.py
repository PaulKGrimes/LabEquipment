##################################################
#                                                #
# IV testing                                     #
#                                                #
# Larry Gardner, July 2018                       #
# Paul Grimes, August 2018                       #
# Edited Aug 2018 to remove power meter code.    #
# Aim is to have simple IV code that can be      #
# subclassed to produce more complex sweep       #
# code                                           #
##################################################

import sys
import os
import time
import visa
import numpy as np
import DAQ
import matplotlib.pyplot as plt


class IV:
    def __init__(self, use="IV.use", verbose=False):
        self.verbose = verbose

        self.pm = None
        self.reverseSweep = True
        self.settleTime = 0.1
        self._bias = 0.0
        self.use = use

        self.save_name = "iv.dat"
        self.vmin = 0.0
        self.vmax = 5.0
        self.step = 0.05

        if self.vmin > self.vmax:
            self.vmin, self.vmax = self.vmax, self.vmin
        self.readFile()
        self.initDAQ()

    def __delete__(self):
        self.endDAQ()


    def readFile(self):
        # Opens use file and assigns corresponding parameters
        if self.verbose:
            print("\nUSE file: ",self.use)
        f = open(self.use, 'r')
        lines = f.readlines()
        f.close()

        self.Vs_min = float(lines[0].split()[0])
        self.Vs_max = float(lines[1].split()[0])
        self.MaxDAC = float(lines[2].split()[0])
        self.Rate = int(lines[3].split()[0])
        self.Navg = int(lines[4].split()[0])
        self.G_v = float(lines[5].split()[0])
        self.G_i = float(lines[6].split()[0])
        self.Boardnum = int(lines[7].split()[0])
        self.Out_channel = int(lines[8].split()[0])
        self.V_channel = int(lines[9].split()[0])
        self.I_channel = int(lines[10].split()[0])
        # Bias range is +/- 15mV, DAQ output range is 0-5V. Voltage offset is required for Volt < 0.
        self.V_offset = float(lines[11].split()[0])

    def voltOut(self, bias):
        """Converts bias voltage to output voltage from DAQ"""
        return bias * self.G_v / 1000 + self.V_offset

    def biasIn(self, volt):
        """Converts input voltage to bias voltage at device"""
        return (volt - self.V_offset) * 1000 / self.G_v

    def currIn(self, volt):
        """Converts input voltage from current channel to bias current at device"""
        return (volt - self.V_offset) / self.G_i

    def crop(self):
        # Limits set voltages to max and min sweep voltages
        if self.vmin < self.Vs_min:
            self.vmin = self.Vs_min
        if self.vmin > self.Vs_max:
            self.vmin = self.Vs_max
        if self.vmax < self.Vs_min:
            self.vmax = self.Vs_min
        if self.vmax > self.Vs_max:
            self.vmax = self.Vs_max

    def initDAQ(self):
        # Lists available DAQ devices and connects the selected board
        self.daq = DAQ.DAQ()
        self.daq.listDevices()
        self.daq.connect(self.Boardnum)

    def bias(self, bias):
        """Short cut to set the bias point to <bias> mV and return the
        resulting bias point"""
        self.setBias(bias)
        data = self.getData()

        if self.verbose:
            print("New Bias Point: {:.4g} mV".format(bias))
            print("  Voltage: {:.4g} mV, Current: {:.4g} mA".format(data[0], data[1]))
        return data

    def setBias(self, bias):
        """Sets the bias point to request value in mV"""
        # Converts desired bias amount [mV] to DAQ output voltage value [V]
        self._bias = bias
        self.setVoltOut(self.voltOut(self._bias))

    def getData(self):
        """Gets V, I and P (if PM present) data, and returns it as a tuple"""
        # Sets proper format for low and high channels to scan over
        channels = [self.V_channel, self.I_channel]
        low_channel, high_channel = min(channels), max(channels)
        data = self.daq.AInScan(low_channel, high_channel, self.Rate, self.Navg)
        # Get the output voltage/curret data
        Vdata = self.calcV(data[self.V_channel])
        Idata = self.calcI(data[self.I_channel])

        return Vdata, Idata

    def calcV(self, volts):
        """Converts ADC reading in volts to bias voltage in mV"""
        return (volts - self.V_offset) * 1000 / self.G_v

    def calcI(self, volts):
        """Converts ADC reading in volts to bias current in uA"""
        return (volts - self.V_offset) / self.G_i

    def setVoltOut(self, volt):
        """Sets the DAC output voltage and waits to settle"""
        # Sets bias to specified voltage
        self.daq.AOut(volt, self.Out_channel)
        time.sleep(self.settleTime)

    def sweep(self):
        """Short cut to prep, run and end sweep"""
        self.prepSweep()
        self.runSweep()
        self.endSweep()


    def prepSweep(self):
        # Sanity check values to make sure that requested bias range is
        # within bias limits
        self.crop()

        print("Preparing for sweep...")
        # Calculate sweep values
        self.BiasPts = np.arange(self.vmin, self.vmax+self.step, self.step)
        if self.reverseSweep:
            self.BiasPts = np.flipud(self.BiasPts)

        # Prepares for data collection
        self.Vdata = np.empty_like(self.BiasPts)
        self.Idata = np.empty_like(self.BiasPts)

        # Setting voltage to max in preparation for sweep
        if self.reverseSweep:
            if self.verbose:
                print("\nChanging voltage to maximum...")
        else:
            if self.verbose:
                print("\nChanging voltage to minimum...")

        self.setVoltOut(self.voltOut(self.BiasPts[0]))


    def runSweep(self):
        if self.verbose:
            print("\nRunning sweep...")

        # Sets proper format for low and high channels to scan over
        channels = [self.V_channel, self.I_channel]
        low_channel, high_channel = min(channels), max(channels)

        if self.verbose:
            print("\tBias (mV)\tVoltage (mV)\tCurrent (mA)")

        for index, bias in enumerate(self.BiasPts):
            self.setVoltOut(self.voltOut(bias))

            #Collects data from scan
            data = self.getData()

            self.Vdata[index] = data[0]
            self.Idata[index] = data[1]

            if index%5 == 0 and self.verbose:
                print("\t{:.3f}\t\t{:.3f}\t\t{:.3f}".format(self.BiasPts[index], self.Vdata[index], self.Idata[index]))


    def endSweep(self):
        # Sets bias to zero to end sweep.
        self.setBias(self._bias)
        if self.verbose:
            print("Sweep is over.  Bias reset to {:.3f} mV.".format(self._bias))


    def endDAQ(self):
        # Disconnects and releases selected board number
        self.daq.disconnect(self.Boardnum)


    def spreadsheet(self):
        if self.verbose:
            print("\nWriting data to spreadsheet...")

        out = open(str(self.save_name), 'w')

        # Writes data to spreadsheet
        out.write("Bias (mV)\t\tVoltage (mV)\t\tCurrent (mA)\n")
        for i in range(len(self.Vdata)):
            out.write("{:.6g},\t{:.6g},\t{:.6g}\n".format(self.BiasPts[i], self.Vdata[i], self.Idata[i]))
        out.close()

    def plotIV(self):
        # Plot IV curve
        plt.plot(self.Vdata,self.Idata, 'ro-')
        plt.xlabel("Voltage (mV)")
        plt.ylabel("Current (mA)")
        plt.title("IV Sweep - 15mV")
        plt.axis([min(self.Vdata), max(self.Vdata), min(self.Idata), max(self.Idata)])
        plt.show()


if __name__ == "__main__":
    # This code runs a sweep from <vmax> to <vmin> with stepsize <step> and
    # saves the data to <save_name>
    #
    # Usage: python3 <file.dat> <vmin> <vmax> <step> <*use file>

    test = IV(verbose=True)

    if len(sys.argv) >= 5:
        test.save_name = sys.argv[1]
        test.vmin = float(sys.argv[2])
        test.vmax = float(sys.argv[3])
        test.step = float(sys.argv[4])
        if len(sys.argv) == 6:
            test.use = sys.argv[5]
    else:
        test.save_name = input("Output file name: ")
        test.vmin = float(input("Minimum voltage [mV]: "))
        test.vmax = float(input("Maximum voltage [mV]: "))
        test.step = float(input("Step [mV]: "))
        if test.step <= 0:
            while test.step <= 0:
                print("Step size must be greater than 0.")
                test.step = float(input("Step [mV]: "))

    # Set up the IV object
    test.readFile()
    test.initDAQ()

    # Run a sweep
    test.sweep()

    # Output and plot data
    test.spreadsheet()
    test.plotIV()

    # Close down the IV object cleanly, releasing the DAQ and PM
    del test

    print("\nEnd.")

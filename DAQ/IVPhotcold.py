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
import IVP
import matplotlib.pyplot as plt
import PowerMeter as PM
import visa

np.seterr(all='raise')

class IVPhotcold(IVP.IVP):
    def __init__(self, use="IV.use", verbose=False):
        super().__init__(use, verbose)

    def __delete__(self):
        super().__delete__()

    def readFile(self):
        super().readFile()
        self.load_bit = int(self._use_lines[17].split()[0])
        self.load_out = bool(self._use_lines[18].split()[0])
        self.load_sleep = float(self._use_lines[19].split()[0])
        self.load_in = not self.load_out
        self.Tcold = float(self._use_lines[20].split()[0])
        self.Thot = float(self._use_lines[21].split()[0])
        self.loadCycle = int(self._use_lines[22].split()[0])


    def getTsys(self):
        """Take a hot/cold load measurement and return the values"""
        # Set load out
        self.loadOut()
        coldData = self.getData()
        if len(coldData) < 3:
            raise RuntimeError("No IF power data - is Power Meter configured correctly?")

        self.loadIn()
        hotData = self.getData()

        vBias, iBias, cPower = coldData
        hPower = hotData[2]
        yFact = self.Yfact(cPower, hPower)
        tsys = self.Tsys(yFact)

        if self.verbose:
            print("Bias     : {:.3f} mV".format(self._bias))
            print("Voltage  : {:.3g} mV".format(vBias))
            print("Current  : {:.3g} mA".format(iBias))
            print("Cold IF  : {:.3g} W".format(cPower))
            print("Hot IF   : {:.3g} W".format(hPower))
            print("Y Factor : {:.3g}".format(yFact))
            print("Tsys     : {:.3g}".format(tsys))

        return vBias, iBias, cPower, hPower, yFact, tsys

    def Yfact(self, cPower, hPower):
        """Calculate the Y Factor, defaulting to sensible value if data is faulty"""
        try:
            Yfact = hPower/cPower
        except (ZeroDivisionError, FloatingPointError):
            Yfact = -1
        return Yfact

    def Tsys(self, yFact):
        """Convert a Y Factor to Tsys, using stored values of hot and cold load temperatures"""
        if yFact==-1:
            return 1.0e99

        try:
             tsys = (self.Thot - self.Tcold*yFact)/(yFact-1)
        except (ZeroDivisionError, FloatingPointError):
             tsys = 1.0e99
        return tsys

    def loadOut(self):
        """Take the load out of the beam"""
        self.daq.DOut(self.load_out, self.load_bit)
        time.sleep(self.load_sleep)

    def loadIn(self):
        """Put the load into the beam"""
        self.daq.DOut(self.load_in, self.load_bit)
        time.sleep(self.load_sleep)


    def prepSweep(self):
        super().prepSweep()

        # Prepares for data collection
        self.Hdata = np.empty_like(self.BiasPts)
        self.Cdata = np.empty_like(self.BiasPts)
        self.Ydata = np.empty_like(self.BiasPts)
        self.Tdata = np.empty_like(self.BiasPts)


    def runSweep(self):
        if self.verbose:
            print("\nRunning sweep...")

        # Sets proper format for low and high channels to scan over
        channels = [self.V_channel, self.I_channel]
        low_channel, high_channel = min(channels), max(channels)

        if self.verbose:
            print("\tBias (mV)\tVoltage (mV)\tCurrent (mA)\tCold IF (W)\tHot IF (W)\tY Factor\tTsys (K)")

        # Start the loop over the BiasPts
        i = 0
        while True:
            try:
                biasPts = self.BiasPts[i:i+self.loadCycle]
            except IndexError:
                biasPts = self.BiasPts[i:]

            self.loadOut()
            # Start the first run through the inner loop over self.loadCycle points
            for index, bias in enumerate(biasPts):
                index +=i
                self.setBias(bias)
                data = self.getData()

                self.Vdata[index] = data[0]
                self.Idata[index] = data[1]
                if self.pm != None:
                    self.Cdata[index] = data[2]
                else:
                    self.Cdata[index] = 0.0
            # End of first inner loop over self.loadCycle points

            self.loadIn()
            # Start the second run through the inner loop over self.loadCycle points
            for index, bias in enumerate(biasPts):
                index +=i
                self.setBias(bias)
                data = self.getData()
                if self.pm != None:
                    self.Hdata[index] = data[2]
                    self.Ydata[index] = self.Yfact(self.Cdata[index], self.Hdata[index])
                    self.Tdata[index] = self.Tsys(self.Ydata[index])
                else:
                    self.Hdata[index] = 0.0
                    self.Ydata[index] = -1
                    self.Tdata[index] = 1.0e99
                # End of second inner loop over self.loadCycle points

            print("\t{: <10.6f}\t{: <10.6g}\t{: <10.6g}\t{: <10.6g}\t{: <10.6g}\t{: <10.6g}\t{: <10.6g}".format(self.BiasPts[i], self.Vdata[i], self.Idata[i], self.Cdata[i], self.Hdata[i], self.Ydata[i], self.Tdata[i]))

            # increment starting index for inner loops by self.loadCycle
            i = i + self.loadCycle
            # break out of outer loop if we are done
            if i >= len(self.BiasPts):
                break

    def spreadsheet(self):
        if self.verbose:
            print("\nWriting data to spreadsheet...")

        # Creates document for libre office
        out = open(self.save_name, 'w')

        # Writes data to spreadsheet
        # Write a header describing the data
        out.write("# Bias (mV),\tVoltage (mV),\tCurrent (mA),\tCold IF (W),\tHot IF (W),\tY Factor,\tTsys (K)\n")
        for index in range(len(self.Vdata)):
            out.write("{: >10.6f},\t{: >10.6g},\t{: >10.6g},\t{: >10.6g},\t{: >10.6g},\t{: >10.6g},\t{: >10.6g}\n".format(self.BiasPts[index], self.Vdata[index], self.Idata[index], self.Cdata[index], self.Hdata[index], self.Ydata[index], self.Tdata[index]))

        out.close()

    def plotPV(self):
        # Plot PV curve
        self.ax2.plot(self.Vdata, self.Cdata, 'b-')
        self.ax2.plot(self.Vdata, self.Hdata, 'r-')
        self.ax2.set(ylabel="Power (W)")
        self.ax.set(title="PV Sweep")

    def plotYFact(self):
        # Plot PV curve
        self.ax2.plot(self.Vdata, self.Ydata, 'g-')
        self.ax2.set(ylabel="Y Factor")
        self.ax2.set_ylim(0, np.amax(self.Ydata)+0.2)
        self.ax.set(title="Y Factor Sweep")
        self.ax.yaxis.grid(False)
        self.ax2.grid()

    def plotTsys(self):
        # Plot PV curve
        self.ax2.plot(self.Vdata, self.Tdata, 'r-')
        self.ax2.set_ylim(0,np.amax(np.where(self.Tdata<2000.0, self.Tdata, 0)))
        self.ax2.set(ylabel="Tsys (K)")
        self.ax.set(title="Tsys Sweep")
        self.ax.yaxis.grid(False)
        self.ax2.grid()

    def plot(self, ion=True):
        """Plot the acquired data from the sweep.
        """
        if ion:
            plt.ion()
        self.fig, self.ax = plt.subplots()
        self.plotIV()
        self.ax2 = self.ax.twinx()
        self.plotPV()
        self.fig.show()
        self.fig, self.ax = plt.subplots()
        self.plotIV()
        self.ax2 = self.ax.twinx()
        self.plotYFact()
        self.fig.show()
        self.fig, self.ax = plt.subplots()
        self.plotIV()
        self.ax2 = self.ax.twinx()
        self.plotTsys()
        self.fig.show()


if __name__ == "__main__":
    # This code runs a sweep from <vmax> to <vmin> with stepsize <step> and
    # saves the data to <save_name>
    #
    # Usage: python3 <file.dat> <vmin> <vmax> <step> <*use file>

    test = IVPhotcold(verbose=True)

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

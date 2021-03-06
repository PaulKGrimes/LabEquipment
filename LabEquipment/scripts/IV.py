#! /usr/bin/env python
#
# This code runs a sweep from <max> to <min> with stepsize <step> and
# saves the data to <save_name>.  Uses an optional <*config file>
#
# Usage: iv.py <*config file> <file.dat> <min> <max> <step>
from LabEquipment.applications.mixer.IV import *
import sys, time
from pprint import pprint
import matplotlib

def main():
    if len(sys.argv) == 6 or len(sys.argv) == 2:
        confFile = sys.argv.pop(1)
    else:
        confFile = "IV-config.hjson"

    test = IV(configFile=confFile, verbose=True, vverbose=False)

    # See if sweep parameters are on the command line
    if len(sys.argv) >= 5:
        test.save_name = sys.argv[1]
        test.sweepmin = float(sys.argv[2])
        test.sweepmax = float(sys.argv[3])
        test.step = float(sys.argv[4])
    else:
        # See if the config file defined a sweep, if not, ask for values
        try:
            sweepConf = test.config["sweep"]
        except (KeyError, TypeError):
            print("test.config error caught")
            pprint(test.config)
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

    # Close down the IV object cleanly, releasing the DAQ
    del test

    print("End.")

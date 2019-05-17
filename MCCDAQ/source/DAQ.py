#! /usr/bin/env python
##################################################
#                                                #
# Wrapper around platform specific drivers          #
# for MCC DAQ devices                            #
#                                                #
# Paul Grimes, 2018                              #
#                                                #
##################################################

from __future__ import print_function, division

import platform
if platform.system().lower().startswith('win'):
    from .DAQ_windows import *
else:
    from .DAQ_linux import *

if __name__ == "__main__":
    daq = DAQ()
    data = daq.AIn(0)
    print(data)
    data = daq.AInScan(0,1,10000,1000,1)
    print(data)
    daq.AOut(0.0)
    daq.DOut(1)
    daq.disconnect()

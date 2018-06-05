# HP 436A Power Meter operation code
# Paul Grimes, May 2018

import Instrument
import time

class PowerMeter(Instrument.Instrument):
    def __init__(self, resource):
        """Create Spectrum Analyzer object from a PyVISA resource:
        rm = pyvisa.ResourceManager()
        pm = PowerMeter(rm.open_resource("GPIB::12"))

        InstAddr is the address of the spectrum analyzer - try "GPIB::12" by default"""
        self.resource = resource
        
        # Set up the connection.
        # HP 436A needs a null line ending on write
        self.resource.write_termination = ""
        self.resource.timeout = 5000
        
        self._readRanges = list(" IJKLM")
        self._modes = { "A":"Watts", "B":"dB Relative", "C": "dB Ref", "D":"dBm"}
        
    @property
    def idn(self):
        """This device can't respond to an "IDN?" type request"""
        return None
        
        
    def getDataStr(self, range="9", mode="A", cal_factor="+", rate="V"):
        """Get data str from power meter using <range> <mode> and <rate>"""
        # Range is one of :
        #   1-5 : Most to least sensitive
        #   9   : Auto
        #
        # Mode is one of:
        #   A : Watts
        #   B : dB Relative
        #   C : dB Ref (switch pressed)
        #   D : dBm
        #
        # Cal Factor is one of:
        #   + : Disable
        #   - : Enable (front-panel switch setting)
        #
        # Measurement Rate is one of:
        #   H : Hold
        #   T : Trigger with settling time
        #   I : Trigger immediately
        #   R : Free-run at maximum rate
        #   V : Free-run with settling timeout
        
        return self.resource.query("{}{}{}{}".format(range, mode, cal_factor, rate)
        
    def unpackDataStr(self, dataStr):
        """Unpack the data string, returning the value in whatever mode we're in"""
        self.status = dataStr[0]
        # Status is one of:
        #   P - Measured value valid
        #   Q - Watts mode under range
        #   R - Over range
        #   S - Under range dBm or dB (rel) mode
        #   T - Power Sensor Auto Zero Loop Enabled; Range 1
        #           Under range: (normal for auto zeroing on Range 1)
        #   U - Power Sensor Auto Zero Loop Enabled; Range !=1
        #           Under range: (normal for auto zeroing on Range 2-5)
        #   V - Power Sensor Auto Zero Loop Enabled; Over Range
                    
        # Range is one of:
        #   I-M, range 1-5
        #
        # Convert to numerical range
        self.range = self._ranges.index(dataStr[1])
        
        
        self.mode = self._modes[dataStr[2]]
        # Mode is one of:
        #   A - Watts
        #   B - dB Relative
        #   C - dB Ref (switch pressed)
        #   D - dBm
        
        sign = dataStr[3]
        if sign == " ":
            s = 1
        elif sign == "-":
            s = -1
        else:
            raise ValueError("Got wrong sign character from Power Meter - {}".format(sign)
            
        value = s*float(dataStr[3:12])
        
        return value
        
    def getData(self, range, mode, cal_factor, 
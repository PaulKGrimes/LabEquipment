# HP 436A Power Meter operation code
# Paul Grimes, May 2018

import Instrument
import time
import statistics

class PowerMeter(Instrument.Instrument):
    def __init__(self, resource, range="9", mode="A", averaging="None", rate="V", calFactor="+", Navg=3):
        """Create Spectrum Analyzer object from a PyVISA resource:
        rm = pyvisa.ResourceManager()
        pm = PowerMeter(rm.open_resource("GPIB0::13::INST"))

        InstAddr is the address of the spectrum analyzer - try "GPIB0::13::INST" by default"""
        self.resource = resource

        # Set up the connection.
        # HP 436A needs a null line ending on write
        self.resource.read_termination = "\r\n"
        self.resource.timeout = 5000

        self._ranges = list(" IJKLM")
        self._rranges = ["1", "2", "3", "4", "5", "9"]
        self.range = range
        self._modes = { "A":"Watts", "B":"dB Relative", "C": "dB Ref", "D":"dBm"}
        self.mode = mode
        self._rates = { "H":"Hold", "T":"Trigger with settling time", "I":"Trigger immediately", "R":"Free-run at maximum rate", "V":"Free-run with settling timeout"}
        self.rate = rate
        self._calFactors = ["+", "-"]
        self.calFactor = calFactor
        self._statuses = {"P":"Data Valid", "Q":"Watts, under range", "R":"Over range", "S":"dB, under range", "T":"Auto zero under range, 1", "U":"Auto zero under range, 2-5", "V":"Auto zero over range"}
        self._averagingModes = ['None', 'Mean', 'Settle']
        self.averaging = averaging
        self.readSleep = 0.15
        self.Navg = Navg

    @property
    def idn(self):
        """This device can't respond to an "IDN?" type request"""
        return None

    @property
    def range(self):
        """Return the current range"""
        return self._range

    @range.setter
    def range(self, range):
        """Set the range"""
        assert range in self._rranges, "HP436A: Tried to set invalid range"
        self._range = range

    @property
    def mode(self):
        """Return the current mode"""
        return self._mode

    @mode.setter
    def mode(self, mode):
        """Set the mode"""
        assert mode in self._modes.keys(), "HP436A: Tried to set invalid mode"
        self._mode = mode

    @property
    def rate(self):
        """Return the current rate"""
        return self._rate

    @rate.setter
    def rate(self, rate):
        """Set the rate"""
        assert rate in self._rates.keys(), "HP436A: Tried to set invalid rate"
        self._rate = rate

    @property
    def calFactor(self):
        """Return the current calFactor"""
        return self._calFactor

    @calFactor.setter
    def calFactor(self, calFactor):
        """Set the calFactor"""
        assert calFactor in self._calFactors, "HP436A: Tried to set invalid calFactor"
        self._calFactor = calFactor

    @property
    def averaging(self):
        """Return the current averaging mode"""
        return self._averaging

    @averaging.setter
    def averaging(self, averaging):
        """Set the averaging mode"""
        if averaging == None:
            averaging = "None"
        assert averaging in self._averagingModes, "HP436A: Tried to set invalid averaging mode"
        self._averaging = averaging

    def getDataStr(self, range="9", mode="A", calFactor="+", rate="V"):
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

        return self.resource.query("{}{}{}{}".format(range, mode, calFactor, rate))

    def unpackDataStr(self, dataStr):
        """Unpack the data string, returning the value in whatever mode we're in"""
        self.status = self._statuses[dataStr[0]]
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
        self.returnedRange = self._ranges.index(dataStr[1])


        self.units = self._modes[dataStr[2]]
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
            raise ValueError("Got wrong sign character from Power Meter - {}".format(sign))

        value = s*float(dataStr[3:12])

        return value

    def getData(self, range="9", mode="A", calFactor="+", rate="V"):
        """Return the power as a float, and set the properties of the PowerMeter
        object to describe the status and what the measurement represents

        Range is one of :
          1-5 : Most to least sensitive
          9   : Auto

        Mode is one of:
          A : Watts
          B : dB Relative
          C : dB Ref (switch pressed)
          D : dBm

        Cal Factor is one of:
          + : Disable
          - : Enable (front-panel switch setting)

        Measurement Rate is one of:
          H : Hold
          T : Trigger with settling time
          I : Trigger immediately
          R : Free-run at maximum rate
          V : Free-run with settling timeout
        """
        dataStr = self.getDataStr(range, mode, calFactor, rate)
        data = self.unpackDataStr(dataStr)
        return data

    def getPower(self):
        """Return the power in the current mode, and using the current averaging
        set up"""
        if self._averaging == "Settle":
            d1 = self.getData(range=self.range, mode=self.mode, calFactor=self.calFactor, rate=self.rate)
            time.sleep(self.readSleep)
            d2 = self.getData(range=self.range, mode=self.mode, calFactor=self.calFactor, rate=self.rate)
            if ( abs((d1-d2)/(d1+d2)) < 0.05 ):
                return ((d1+d2)*0.5)
            else:
                time.sleep(self.readSleep)
                d3 = self.getData(range=self.range, mode=self.mode, calFactor=self.calFactor, rate=self.rate)
                if ( abs(d2-d3) < abs(d1-d3) ):
                    return ((d2+d3)*0.5)
                else:
                    return ((d1+d3)*0.5)

        elif self._averaging == "Mean":
            data = []
            for i in range(self.Navg):
                data.append(self.getData(range=self.range, mode=self.mode, calFactor=self.calFactor, rate=self.rate))
                time.sleep(self.readSleep)
            return statistics.mean(data)
        else: # self._averaging == "None":
            return self.getData(range=self.range, mode=self.mode, calFactor=self.calFactor, rate=self.rate)

if __name__ == "__main__":
    import visa
    rm = visa.ResourceManager()
    res = rm.open_resource("GPIB0::13::INST")
    pm = PowerMeter(res, averaging=Settle)

    print("Power : {:g} {:s}".format(pm.getData(), pm.units))
    print("Range : {:d}".format(pm.returnedRange))
    print("Status: {:s}".format(pm.status))

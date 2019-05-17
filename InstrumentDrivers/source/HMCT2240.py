import Instrument

class HMCT2240(Instrument.Instrument):
    """Class for communicating with an HMC-T2240 signal generator"""

    def __init__(self, resource, strict=False, idString="HMC-T2240"):
        """Create Signal Generator object from PyVisa resource.

        rm = pyvisa.ResourceManager()
        sg = HMCT2240(rm.open_resource(<InstAddr>))
        InstAddr is the PyVisa address of the SG - try "GPIB0::30::INSTR" by default"""

        super().__init__(resource, strict, idString)

        self.freq = self.getFreq()
        self.power = self.getPower()

    def on(self):
        """ Turns on RF output"""
        self.write("OUTP ON")

    def off(self):
        """ Turn off RF output"""
        self.write("OUTP OFF")

    def setFreq(self, freq):
        """ Set frequency - range of 10MHz to 2GHz (2GHz is max for HP8508A vvm) Freq must be in form "10000000" or "10e6" """
        self.write("FREQ "+str(freq))

    def getFreq(self):
        """ Returns frequency """
        self.freq = self.query("FREQ?")
        return self.freq

    def setPower(self, pow):
        """ Set power in dBm"""
        self.write("POW "+str(pow))

    def getPower(self):
        """ Returns power """
        self.power = self.query("POW?")
        return self.power

    def local(self):
        """ User retains local control """
        self.write("SYST:COMM:GTL")

    def remote(self):
        """ User retains remote control """
        self.write("SYST:COMM:GTR")

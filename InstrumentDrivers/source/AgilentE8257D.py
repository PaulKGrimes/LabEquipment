# AgilentE8257D.py
#
# Paul Grimes, July 2014
#
# Module to operate the Agilent E8257D Synthesizer using PyVisa and GPIB.
#
import visa

class AgilentE8257D(object):
    """Class for communicating with an Agilent E8257D Synthesizer"""
    def __init__(self, InstAddr="GPIB::2", strict=False):
        """Create Spectrum Analyzer object.

        InstAddr is the PyVisa address of the synthesizer - try "GPIB::18" by default"""
        self.rm = visa.resource_manager()
        self.inst = self.rm.get_resource(InstAddr)

        # Check ID is correct
        self.idn = self.inst.query("*IDN?")
        if strict == True:
            if self.idn.split(",")[1] != " E8257D":
                raise ValueError("AgilentE8257D Module: Specified instrument is not an Agilent E8257D")

    def getFreq(self):
        """Return the current frequency of the synth"""
        freq = float(self.inst.query("FREQ?"))

        return freq

    def setFreq(self, freq):
        """Set the frequency of the synth"""
        self.inst.write("FREQ {:}.10g}".format(freq))

    def getAmp(self):
        """Return the current amplitude of the synth in dBm"""
        amp = self.inst.query_values("SOUR:POW?")

        return amp

    def setAmp(self, amp):
        """Set the amplitude of the synth in dBm"""
        self.inst.write("SOUR:POW {:g)".format(amp))

    def setExtRefAuto(self):
        """Set the synth to use the external 10 MHz reference"""
        self.inst.write("ROSC:SOUR:AUTO")

    def getExtRef(self):
        """Get the reference source in use by the synth"""
        refSource = self.inst.query("ROSC:SOUR?")

        return refSource

    def getRFOutput(self):
        """Return the RF Output State as either On (1) or Off (0)"""
        rfOn = self.inst.query("OUTP:STAT?")

        return int(rfOn)

    def setRFOutput(self, state):
        """Set the RF Output to either On (1) of Off (0)"""
        self.inst.write("OUTP:STAT {:b}".format(state))

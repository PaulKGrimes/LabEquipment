# HP83630A.py
#
# Paul Grimes, July 2014
#
# Module to operate the HP 83630A Synthesizer using PyVisa and GPIB.
#
import Instrument

class HP83630A(Instrument.Instrument):
    """Class for communicating with an HP 83630A Synthesizer"""
    def __init__(self, resource, strict=False, idString="83630A"):
        """Create Synthesizer object.

        InstAddr is the PyVisa address of the Synthesizer - try "GPIB::19" by default in the lab"""

        super().__init__(resource, strict, idString)

        self.resource.read_termination = '\n'
        self.resource.write_termination = '\r\n'

        # Available sweep modes
        self.freqModes = {
                "cw":"CW",
                "sweep":"SWE",
                "list":"LIST"
            }

        # default to CW mode
        self.setCW()

    def on(self):
        """ Turns on RF output"""
        self.setRFOutput(True)

    def off(self):
        """ Turn off RF output"""
        self.setRFOutput(False)

    # Frequency control methods
    def getFreqMode(self):
        """Return the frequency output mode"""
        mode = self.query("FREQ:MODE?")
        return list(self.freqModes.keys())[list(self.freqModes.values()).index(mode)]

    def setFreqMode(self, mode):
        """Set the frequency mode.

        One of:
            cw
            sweep
            list
        """
        self.write("FREQ:MODE {:s}".format(self.freqModes[mode]))

    def setCW(self):
        """Set source to CW mode"""
        self.setFreqMode("cw")

    def setSweep(self):
        """Set source to SWEEP mode"""
        self.setFreqMode("sweep")

    def setList(self):
        """Set source to LIST mode"""
        self.setFreqMode("list")

    def getFreq(self):
        """Return the current CW frequency of the synth"""
        return float(self.query("FREQ?"))

    def setFreq(self, freq):
        """Set the CW frequency of the synth"""
        self.write("FREQ {:.10g}".format(freq))

    def getFreqStart(self):
        """Return the current start frequency of the synth"""
        return float(self.query("FREQ:STAR?"))

    def setFreqStart(self, freq):
        """Set the start frequency for sweeps"""
        self.write("FREQ:STAR {:.10g}".format(freq))

    def getFreqStop(self):
        """Return the current stop frequency of the synth"""
        return float(self.query("FREQ:STOP?"))

    def setFreqStop(self, freq):
        """Set the stop frequency for sweeps"""
        self.write("FREQ:STOP {:.10g}".format(freq))

    def getFreqCenter(self):
        """Return the current center frequency for sweeps of the synth"""
        return float(self.query("FREQ:CENT?"))

    def setFreqCenter(self, freq):
        """Set the center frequency for sweeps"""
        self.write("FREQ:CENT {:.10g}".format(freq))

    def getFreqSpan(self):
        """Return the current frequency span for sweeps of the synth"""
        return float(self.query("FREQ:SPAN?"))

    def setFreqSpan(self, freq):
        """Set the frequency span for sweeps"""
        self.write("FREQ:SPAN {:.10g}".format(freq))

    def getFreqStep(self):
        """Return the current frequency step for sweeps of the synth"""
        return float(self.query("FREQ:STEP?"))

    def setFreqStep(self, step):
        """Set the frequency step for sweeps"""
        self.write("FREQ:STEP {:.10g}".format(step))


    # Power control methods
    def getPower(self):
        """Return the current amplitude of the synth in dBm"""
        amp = float(self.query("POW?"))

        return amp

    def setPower(self, amp):
        """Set the amplitude of the synth in dBm"""
        self.write("POW {:g}".format(amp))

    def setExtRefAuto(self):
        """Set the synth to use the external 10 MHz reference"""
        # TODO: Replace with correct command
        #self.write("ROSC:SOUR:AUTO")
        pass

    def getExtRef(self):
        """Get the reference source in use by the synth"""
        # TODO: Replace with correct command
        #refSource = self.query("ROSC:SOUR?")
        #return refSource
        pass

    def getRFOutput(self):
        """Return the RF Output State as either On (1) or Off (0)"""
        # TODO: Replace with correct command
        rfOn = self.query("POW:STAT?")
        return bool(int(rfOn))

    def setRFOutput(self, state):
        """Set the RF Output to either On (True) of Off (False)"""
        # TODO: Replace with correct command
        self.write("POW:STAT {:d}".format(int(state)))

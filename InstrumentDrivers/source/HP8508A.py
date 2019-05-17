import Instrument
import numpy as np

def dBdeg2complex(amp, phase):
    """Convert amplitude in dB and phase in degrees to cartesian complex number"""
    return np.power(10.0, amp/20) * np.exp(1j*np.deg2rad(phase))

class HP8508A(Instrument.Instrument):
    '''Class for communicating with an HP 8508A Vector Voltmeter'''
    def __init__(self, resource, strict=False, idString="8508A-050"):
        """Create Vector Voltmeter object from PyVisa resource.

        rm = pyvisa.ResourceManager()
        pm = HP8508A(rm.open_resource(<InstAddr>))
        InstAddr is the PyVisa address of the VVM - try "GPIB0::8::INSTR" by default"""

        super().__init__(resource, strict, idString)

        # Set some internal state parameters to allow return values to be interpreted
        self.mode = "UNKNOWN"
        self.format = self.getFormat()
        self.average = self.getAveraging()
        self.triggersource = "UNKNOWN"
        self.triggered = False

        # Set termination characters
        self.resource.read_termination = '\n'
        self.resource.write_termination = '\r\n'

        # Get current format
        self.getFormat()

    def setTransmission(self):
        '''Set the VVM to output transmission data - relative amplitude (A/B) and phase (A-B)'''
        self.write("SENSE TRANSMISSION")
        self.mode = "TRANSMISSION"

    def setMode(self, mode):
        '''Set the VVM measurement mode

        mode can be any of:
        AVOLtage, BVOLtage - A and B voltages
        APOWer, BPOWer - A and B powers
        PHASe - phase between A and B
        TRANSMISSION - power and phase difference between A and B
        GDELay - Group delay between A and B
        SWR -
        RHO -
        Y
        Z
        CORE
        modes can be concatenated with comma separation'''
        self.write("SENSE {:s}".format(mode))
        self.mode = mode

    def setTrigger(self, trigger):
        '''Set the trigger for the VVM data acquisition
        Valid options for the trigger are:
            BUS  - Trigger from Bus clock
            FREE - Freerunning'''
        self.write("TRIG:SOUR {:s}".format(trigger))
        self.triggersource = trigger


    def setTriggerBus(self):
        '''Set the trigger to the Bus clock'''
        self.setTrigger("BUS")


    def setTriggerFree(self):
        '''Set the trigger to free run'''
        self.setTrigger("FREE")


    def setFormat(self, format):
        '''Set the output format of the VVM
        Valid options are:
            LIN - (Volts)
            LOG - (dB)
            POL - (amp in dB or volts, phase in deg)
            RECT - volts as (real, imag)
            CART - volts as (real, imag)
            '''
        self.write("FORMAT {:s}".format(format))
        self.getFormat()


    def getFormat(self):
        '''Return the current output format of the VVM'''
        self.format = self.query("FORMAT?")

        return self.format


    def setFormatLog(self):
        '''Set the output format of the VVM to LOG - (dB) or (dB, deg) for TRANSMISSION'''
        self.setFormat("LOG")


    def setAveraging(self, window):
        '''Set the VVM to average <window> samples before returning data'''
        '''Window range from 0 to 10 (2^window)'''
        self.write("AVER:COUN {:d}".format(window))


    def getAveraging(self):
        '''Get the number of samples averaged for each data point'''
        self.averaging = int(self.query("AVER:COUN?"))
        return self.averaging


    def trigger(self):
        '''Trigger a measurement with the VVM'''
        self.write("*TRG")
        self.triggered = True


    def getTransmission(self):
        '''Return the data from the VVM'''
        # TODO: Get the correct "format" strings to allow parsing of datastr

        # Get the data
        datastr = self.getData("TRANSMISSION")

        if self.format == "LOGARITHMIC,POLAR" or self.format == "LINEAR,POLAR":
            amp = float(datastr.split(",")[0])
            phase = float(datastr.split(",")[1])
            data = dBdeg2complex(amp, phase)

        elif self.format == "LINEAR,RECTANGULAR" or self.format == "LOGARITHMIC,RECTANGULAR":
            x = float(datastr.split(",")[0])
            y = float(datastr.split(",")[1])
            data = complex(x, y)

        else: # Unknown format, probably single valued
            try:
                # Try to convert unknown format to a float, if not return raw string
                data = float(datastr)
            except ValueError:
                data = datastr
        return data


    def getUnits(self):
        ''' Returns units for format types'''
        x = str(self.format.split(",")[0])
        y = str(self.format.split(",")[1])

        if x == "LINEAR":
            x_units = "volts"
        elif x == "LOGARITHMIC":
            x_units = "dB"

        if y == "POLAR":
            y_units = "deg"
        elif y == "RECTANGULAR":
            y_units = "Real + Imag"

        units = (x_units, y_units)

        return units


    def getData(self, meas=None):
        '''Return the requested measurement(s) from the VVM<meas> is one of:

        AVOLtage, BVOLtage - A and B voltages
        APOWer, BPOWer - A and B powers
        PHASe - phase between A and B
        TRANSMISSION - power and phase difference between A and B
        GDELay - Group delay between A and B
        SWR -
        RHO -
        Y
        Z
        CORE
        <meas> can be concatenated with comma separation
        '''
        if meas==None:
            if self.mode != "UNKNOWN":
                meas = self.mode
            else:
                meas = "APOW"

        # Trigger the measurement if required
        if self.triggersource == "BUS" and self.triggered == False:
            self.trigger()

        # Get the data
        datastr = self.query("MEAS? {:s}".format(meas))

        # Reset the triggered state
        self.triggered = False
        # code to decipher the response according to the mode or measurement
        # if self.format == "LOGARITHMIC,POLAR" or self.format == "LINEAR,POLAR":
        #     amp = float(datastr.split(",")[0])
        #     phase = float(datastr.split(",")[1])
        #     data = (amp, phase)
        # elif self.format == "LINEAR,RECTANGULAR" or self.format == "LOGARITHMIC,RECTANGULAR":
        #     x = float(datastr.split(",")[0])
        #     y = float(datastr.split(",")[1])
        #     data = complex(x, y)
        # else: # Unknown format, probably single valued
        #     try:
        #         # Try to convert unknown format to a float, if not return raw string
        #         data = float(datastr)
        #     except ValueError:
        #         data = datastr

        return datastr

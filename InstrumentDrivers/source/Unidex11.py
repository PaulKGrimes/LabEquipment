# Unidex11.py
#
# Paul Grimes, March 2018
#
# Module to operate the Unidex11 motion controller using PyVisa and GPIB.
#
import pyvisa
from numpy import sign

class Unidex11(object):
    """Class for communicating with a Unidex 11 motion controller"""
    def __init__(self, InstAddr="GPIB::2", strict=False):
        """Create Unidex11 motion controller object.

          InstAddr is the address of the motion controller - try "GPIB::2" by default"""

        rm = pyvisa.ResourceManager()

        read_termination="\r\n"

        if InstAddr[0:3] == "COM": # We are using RS232 and need to set up the instrument more carefully
            self.inst = rm.open_resource(InstAddr, baud_rate=9600, data_bits=7, stop_bits=1, parity=pyvisa.odd_parity, term_chars=read_termination, delay = 0.05)
        else:  # We are probably using GPIB, but don't really know.
            self.inst = rm.open_resource(InstAddr)

        self.verbose = False
        self.Uspeed = 100
        self.Vspeed = 100
        self.posMode = "Abs"


    def setSpeed(self, speed):
        """Set the speed for the U and V axes

        Can cope with value or tuple like input"""
        try:
            if len(speed) == 1:
                self.Uspeed = speed[0]
                self.Vspeed = speed[0]
            elif len(speed) == 2:
                self.Uspeed = speed[0]
                self.Vspeed = speed[1]
            else:
                raise ValueError("Incorrect number of elements in speed.  Must be 1 or 2 elements only.")
        except TypeError:
            self.Uspeed = speed
            self.Vspeed = speed


    def rmove(self, step, dir=(1,1)):
        """Move incrementally by step=(Ustep, Vstep) in direction dir=(Udir, Vdir)"""
        if self.posMode == "Abs":
            self.inst.write("I IN *\n")

        Ustep = step[0]*sign(dir[0])
        Vstep = step[1]*sign(dir[1])

        self.inst.write("I U F{:d} D{:d} V F{:d} D{:d} *\n".format(self.Uspeed, Ustep, self.Vspeed, Vstep))

        if self.posMode == "Abs":
            self.inst.write("I AB *\n")


    def move(self, pos):
        """Move to absolute position pos = (xpos, ypos)"""
        if self.posMode == "Inc":
            self.inst.write("I AB *\n")
        cmd = "I U F{:d} D{:d} V F{:d} D{:d} *\n".format(self.Uspeed, pos[0], self.Vspeed, pos[1])
        self.inst.write(cmd)

        if self.posMode == "Inc":
            self.inst.write("I IN *\n")

    def waitForStop(self):
        """Wait until the current move command finishes"""
        while not (self.inst.stb & 64):
            time.sleep(0.1)
        while (self.inst.stb & 64):
            time.sleep(0.1)


    def getUAxisPosition(self):
        """Return the U axis position"""
        self.Upos = float(self.inst.query("PU\n"))

        return self.Upos

    def getVAxisPosition(self):
        """Return the U axis position"""
        self.Vpos = float(self.inst.query("PV\n"))

        return self.Vpos

    def getUVPosition(self):
        """Return a tuple holding the current UV position"""
        Upos = self.getUAxisPosition()
        Vpos = self.getVAxisPosition()
        return (Upos, Vpos)

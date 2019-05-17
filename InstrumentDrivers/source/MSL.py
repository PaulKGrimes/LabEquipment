# MSL.py
#
# Driver code from Newmark MDrive MSL linear slide
#
#  - Lawrence Gardner, Aug 2018
#  - Paul Grimes, Oct 2018
#


from ..Instrument import Instrument

class MSL(Instrument.Instrument):
    ''' Class for communicating with a Newmark Systems MSL Linear Stage
        with MDrive Motor'''

    def __init__(self, resource, partyName=None, strict=False, softLimits=True):
        super().__init__(resource)

        self.resource.read_termination = '\r\n'

        if partyName == None:
            self.resource.write_termination = '\r'
            self.prefix = ""
        else:
            self.resource.write_termination = '\n'
            self.prefix = partyName + " "

        # Turns off echo for each command
        self.write("EM = 2")

        self.posLimit = None
        self.negLimit = None
        self.softLimits = softLimits


    def write(self, cmd):
        super().write(self.prefix+cmd)

    def query(self, cmd):
        return super().query(self.prefix+cmd)

    def setVelInit(self, vel):
        'Set Initial Velocity'
        self.write("VI=" +str(vel))

    def setVelMax(self, vel):
        'Set max velocity'
        self.write("VM="+str(vel))

    def getVelInit(self):
        'Returns Initial Velocity'
        self.VelInit = int(self.query("PR VI"))
        return self.VelInit

    def getVelMax(self):
        'Returns Max Velocity'
        self.VelMax = int(self.query("PR VM"))
        return self.VelMax

    def getVel(self):
        'Returns current velocity'
        self.velocity = int(self.query("PR V"))
        return self.velocity

    def setAccel(self, acl):
        'Sets acceleration'
        self.write("A="+str(acl))

    def setDecel(self, dec):
        'Sets deceleration'
        self.write("D="+str(dec))

    def getAccel(self):
        'Returns acceleration'
        self.accel = int(self.query("PR A"))
        return self.accel

    def getParam(self):
        'Returns all parameters'
        self.param = self.query("PR AL")
        return self.param

    def moveAbs(self, pos):
        """Moves to an absolute position from 0"""
        if self.softLimits:
            if self.posLimit:
                if self.posLimit < pos:
                    raise ValueError("Requested position {:f} beyond positive limit {:f} of motion of MSL {}".format(pos, self.prefix[:-1], self.posLimit))
            if self.negLimit:
                if self.negLimit > pos:
                    raise ValueError("Requested position {:f} beyond negative limit {:f} of motion of MSL {}".format(pos, self.prefix[:-1], self.negLimit))
        self.write("MA {:d}".format(int(pos)))

    def moveRel(self, pos):
        """Moves distance from current position"""
        if self.softLimits:
            currPos = self.getPos()
            if self.posLimit:
                if self.posLimit < pos+currPos:
                    raise ValueError("Requested position {:f} beyond positive limit {:f} of motion of MSL {}".format(pos, self.prefix[:-1], self.posLimit))
            if self.negLimit:
                if self.negLimit > pos+currPos:
                    raise ValueError("Requested position {:f} beyond negative limit {:f} of motion of MSL {}".format(pos, self.prefix[:-1], self.negLimit))
        self.write("MR {:d}".format(int(pos)))

    def setHome(self, pos):
        """Set a specific position to home"""
        currPos = self.getPos()
        self.write("P={d}".format(int(currPos-pos)))

    def home(self):
        """Move to the home position

        Since the MSL's don't have home switches, we move to whatever the current
        zero position is"""
        self.moveAbs(0)

    def getPos(self):
        'Returns position relative to 0'
        self.position = int(self.query("PR P"))
        return self.position

    def isMoving(self):
        self.moving = self.query("PR MV")
        return self.moving

    def hold(self):
        'Holds instruction till motion has stopped'
        while self.isMoving() == '1':
            None

    def zero(self):
        """Sets current position to home (0 position)

        Also updates stored limits if any"""
        oldPos = self.getPos()
        self.write("P=0")
        if self.posLimit:
            self.posLimit = self.posLimit - oldPos
        if self.negLimit:
            self.negLimit = self.negLimit - oldPos


    def calibrate(self):
        'Calibration'
        self.write("SC")

    def findLimits(self):
        """Find the limits of travel of the stage, using the built in limit
        switches"""
        # Run forward until we run into the limit switch
        self.moveRel(10000000)
        self.hold()
        self.posLimit = self.getPos()

        # Step backward until we run into the limit switch
        self.moveRel(-10000000)
        self.hold()
        self.negLimit = self.getPos()

    def center(self):
        """Move to the center of the range of motion and set that to be the home position"""
        # Check that we know where the limits are
        if (not self.posLimit) or (not self.negLimit):
            self.findLimits()

        center = (self.posLimit + self.negLimit)/2
        self.moveAbs(center)
        self.hold()
        self.zero()

    def initialize(self):
        'Returns all variables to default'
        self.write("IP")
        self.read()
        'Turns off echo for each command'
        self.write("EM = 2")


if __name__ == "__main__":
    import visa

    # Run test code
    rm = visa.ResourceManager()
    m = MSL(rm.open_resource("ASRL/dev/ttyUSB0", partyName="X"))
    print("Set up MSL Translation stage on {}".format(MSL.resource.resource_name))

    print("Current Position: {:d}".format(m.getPos()))

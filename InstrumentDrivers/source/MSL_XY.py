# MSL_XY.py
#
# Paul Grimes, Aug 2018
# from code by Larry Gardner, Jul 2018
#

from ..Instrument import Instrument

class MSL_XY(Instrument.Instrument):
    ''' Class for communicating with two Newmark Systems MSL Linear Stages
        with MDrive Motors, set up as an X/Y scanner on a single IEEE-485 bus.

        MDrive Motors must have been configured to Party Mode, with
        device names X and Y, with command echo turned off

        Commands can be sent to either or both drives using drv keywords,
        where drv is either device name or "*" for both devices.

        Default device names for the X and Y drives are built into the
        object as msl.X and msl.Y'''

    def __init__(self, resource, strict=False):

        super().__init__(resource)

        self.resource.read_termination = '\r\n'
        self.resource.write_termination = '\n'

        self.X = "X"
        self.Y = "Y"

    def setVelInit(self, vel, drv="*"):
        'Set Initial Velocity'
        self.write("{} VI={:d}".format(drv, vel))

    def setVelMax(self, vel, drv="*"):
        'Set max velocity'
        self.write("{} VM={:d}".format(drv, vel))

    def getVelInit(self, drv="*"):
        'Returns Initial Velocity'
        return int(self.query("{} PR VI".format(drv)))

    def getVelMax(self, drv="*"):
        'Returns Max Velocity'
        return int(self.query("{} PR VM".format(drv)))

    def getVel(self, drv="*"):
        'Returns current velocity'
        return int(self.query("{} PR V".format(drv)))

    def setAccel(self, acl, drv="*"):
        'Sets acceleration'
        self.write("{} A={:d}".format(drv, acl))

    def setDecel(self, dec, drv="*"):
        'Sets deceleration'
        self.write("{} D={:d}".format(drv, dec))

    def getAccel(self, drv="*"):
        'Returns acceleration'
        return int(self.query("{} PR A".format(drv)))

    def getParams(self, drv="*"):
        'Returns all parameters'
        self.write("{} PR AL".format(drv))
        params = []
        while True:
            rd = self.read()
            if rd=="":
                break
            else:
                params.append(rd)
        return params

    def moveAbs(self, pos, drv="*"):
        'Moves to an absolute position from 0'
        self.write("{} MA {:d}".format(drv, pos))

    def moveRel(self, pos, drv="*"):
        'Moves distance from current position'
        self.write("{} MR {:d}".format(drv, pos))

    def setHome(self, drv="*"):
        'Sets current position to home (0 position)'
        self.write("{} P=0".format(drv))

    def getPos(self, drv="*"):
        'Returns position relative to 0'
        return int(self.query("{} PR P".format(drv)))

    def isMoving(self, drv="*"):
        return bool(int(self.query("{} PR MV".format(drv))))

    def hold(self, drv="*"):
        'Holds instruction till motion has stopped'
        while self.isMoving(drv):
            None

    def zero(self, drv="*"):
        'Makes the minimum position the home'
        self.moveAbs(-550000, drv)
        self.hold(drv)
        while self.getPos(drv) != '0':
            self.setHome(drv)

    def calibrate(self, drv="*"):
        'Calibration'
        self.write("{} SC".format(drv))

    def initialize(self, drv="*"):
        'Returns all variables to values stored in NVM'
        self.write("{} IP".format(drv))

if __name__ == "__main__":
    import visa

    # Run test code
    rm = visa.ResourceManager('@py')
    m = MSL_XY(rm.open_resource("ASRL/dev/ttyUSB0"))
    print("Set up communication with MSL Translation stages on {}".format(m.resource.resource_name))
    print()
    print("Current Position of X drive: {:d}".format(m.getPos(m.X)))
    print("Current Position of Y drive: {:d}".format(m.getPos(m.Y)))
    print()
    print("Parameters of X drive:")
    params = m.getParams(m.X)
    for p in params:
        print("\t{}".format(p))
    print()
    print("Parameters of Y drive:")
    params = m.getParams(m.Y)
    for p in params:
        print("\t{}".format(p))

class Instrument(object):
    """Base class for pyvisa based instruments

    Encapsulates the pyvisa resource, and provides basic communications
    functions which can be used to implement instrument specific functions"""
    def __init__(self, resource, strict=False, idString=None):
        self.resource = resource
        # Check ID is correct
        if strict == True and idString:
            if self.idn.split(",")[1] != idString:
                raise ValueError("Instrument ID is not {:s}: got {:s}".format(idString, self.idn))

    def write(self, *args, **kwargs):
        """Writes a command string to the instrument"""
        return self.resource.write(*args, **kwargs)

    def read(self, *args, **kwargs):
        """Reads a string from the instrument"""
        return self.resource.read(*args, **kwargs)

    def query(self, *args, **kwargs):
        """Writes a command string to the instrument and reads the response"""
        return self.resource.query(*args, **kwargs)

    def idn(self):
        """Read the return value from the semi-standard "*IDN?" VISA command"""
        return self.query("*IDN?")

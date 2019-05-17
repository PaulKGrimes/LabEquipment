import socket

class MLBF(object):
    """Class for operating the Micro Lambda Wireless MLBF series of
    benchtop YIG filters, using UDP sockets over ethernet"""
    def __init__(self, ip_address, port=30303):
        self._ip_address = ip_address
        self._port = port

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(1)

        # Get some initial data
        self._fmax = self.getFMax()
        self._fmin = self.getFMin()
        self._f = self.getF()
        self._model = self.getModel()
        self._serial = self.getSerial()

    def read(self, bytesize=1024):
        """Listen for <bytesize> bytes from UDP client"""
        data, addr = self.sock.recvfrom(bytesize)
        if data:
            # decode to a string and remove extraneous stuff
            data = data.decode("utf-8").strip().strip("\x00")
        return data

    def write(self, message):
        """Write message to UDP client"""
        self.sock.sendto(bytes(message, "UTF-8"), (self.ip_address, self.port))

    @property
    def ip_address(self):
        """The IP address of the YIG filter"""
        return self._ip_address

    @ip_address.setter
    def ip_address(self, ip):
        """Set the IP address. Since this likely changes the instrument,
        we need to get all new data about the instrument"""
        self.__init__(ip, port=self._port)

    @property
    def port(self):
        """The port of the instrument"""
        return self._port

    @port.setter
    def port(self, p):
        """Set the port.

        Communication probably didn't work before this was set, but we
        have lazy checking of the values, so we'll rely on that."""
        self._port = p

    @property
    def f(self):
        """The current frequency of the YIG filter."""
        try:
            freq = self._f
        except AttributeError:
            self._f = self.getF()
            freq = self._f
        return freq

    @f.setter
    def f(self, freq):
        self.setF(freq)

    @property
    def fmin(self):
        """The minimum frequency of the YIG filter.  This can't change
        so we only read it the first time"""
        try:
            freqmin = self._fmin
        except AttributeError:
            self._fmin = self.getFMin()
            freqmin = self._fmin
        return freqmin

    @property
    def fmax(self):
        """The maximum frequency of the YIG filter.  This can't change
        so we only read it the first time"""
        try:
            freqmax = self._fmax
        except AttributeError:
            self._fmax = self.getFMax()
            freqmax = self._fmax
        return freqmax

    @property
    def model(self):
        """The model number of the YIG filter.  This can't change so we
        only read it the first time"""
        try:
            mod = self._model
        except AttributeError:
            self._model = self.getModel()
            mod = self._model
        return mod

    @property
    def serial(self):
        """The serial number of the YIG filter.  This can't changes so we
        only read it the first time"""
        try:
            ser = self._serial
        except AttributeError:
            self._serial = self.getSerial()
            ser = self._serial
        return ser


    def getFMin(self):
        """Get the minimum frequency setting in MHz"""
        self.write("R0003")
        f = self.read()
        return float(f)

    def getFMax(self):
        """Get the maximum frequency setting in MHz"""
        self.write("R0004")
        f = self.read()
        return float(f)

    def getF(self):
        """Get the current frequency setting in MHz"""
        self.write("R0016")
        f = self.read()
        return float(f)

    def setF(self, freq):
        """Set the frequency in MHz"""
        if freq > self.fmax:
            raise ValueError("MLBF: Requested frequency of {:f} MHz too high".format(freq))
        if freq < self.fmin:
            raise ValueError("MLBF: Requested frequency of {:f} MHz too low".format(freq))
        self.write("F{:.3f}".format(freq))
        self._f = self.getF()

    def getModel(self):
        """Get the Model Number"""
        self.write("R0000")
        return self.read()

    def getSerial(self):
        """Get the serial number"""
        self.write("R0001")
        return self.read()

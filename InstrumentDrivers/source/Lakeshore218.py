# Lakeshore 218 Temperature Monitor module
# Paul Grimes, Sept. 2008, June 2018

import pyvisa
import string

class Lakeshore(object):
    def __init__(self, InstAddr="GPIB::11", strict=False, idString="83630A"):
        """Create Lakeshore Temperature Monitor object.

        if InstAddr[0:3] == "COM": # We are using RS232 and need to set up the instrument more carefully
        self.inst = rm.open_resource(InstAddr, baud_rate=9600, data_bits=7, stop_bits=1, parity=visa.odd_parity, term_chars="\r\n", delay = 0.05)

        rm = pyvisa.ResourceManager()
        pm = HP8508A(rm.open_resource(<InstAddr>))
        InstAddr is the PyVisa address of the VVM - try "GPIB::11" by default"""

        super().__init__(resource, strict, idString)



    ### Device specific Visa commands that wrap around the above generic commands
    def get_temp_log(self, outfilename, sensor_list):
        """ Get an entire temperature log off the lakeshore:
        Takes output text filename and  python list of sensors to read from
        Dumps output (in ohms, Kelvin or whatever) into a space seperated
        text file"""


        last_log=int(self.query("LOGNUM?"))
        print("Last log was {:d}".format(last_log))

        f=open(outfilename,'w')

        for i in range(1,last_log+1):
            print("fetching record {:d}".format(i))
            output_string=""
            log_str=self.query("LOGVIEW? {:d} 1".format(i))
            log_list=log_str.split(",")
            output_string += (log_list[0]+" "+log_list[1])
            for j in sensor_list:
                log_str=self.query("LOGVIEW? {:d} {:d}".format(i,j))
                log_list=log_str.split(",")
                output_string +=(log_list[2]+" ")

            f.write(output_string+"\n")
            print(output_string)
        f.close
        print("...done")


    def get_log(self):
        """Read the logged data to a python list of readings.
        This functions checks to see which sensors are active, and which
        units are in use.
        This header data is included in position 0 of the list of readings,
        and should be treated as a file header"""

        # Get number of log readings per record
        readings = self.get_logreadings()

        # Get number of log records
        records = self.get_lognum()

        # Set up the header, getting the input and units for each log record
        logsetup = []
        for i in range(1, readings+1):
            logsetup.append([self.get_loginput(i), self.get_logunits(i)])

        logheader = ["# Date,Time"]

        for r in logsetup:
            logheader.append("T{:d} ({:s})".format(r[0], r[1]))


        # Start reading the log
        log = [logheader]

        for record in range(1, records+1):
            logrecord = [self.get_logdatetime(record)]
            for reading in range(1, readings+1):
                logrecord.append(self.get_logvalue(record, reading))

            log.append(logrecord)

        return log


    def get_logvalue(self, record, reading):
        """Returns a single reading from a record in the log"""
        retval = self.query("LOGVIEW? {:d} {:d}".format(record, reading))

        return float(retval.split(",")[2])


    def get_logdatetime(self, record):
        """Return the date and time that a log record was recorded"""
        retval = self.query("LOGVIEW? {:d} {:d}".format(record, 1))

        datetime = retval.split(",")[0:2]

        return string.join(datetime, ",")


    def get_lognum(self):
        """Returns the number of records in the log"""

        return int(self.query("LOGNUM?"))


    def get_logreadings(self):
        """Returns the number of readings per log record"""
        logset = self.query("LOGSET?")

        return int(logset.split(",")[4])


    def get_logunits(self, reading):
        """Returns the unit string for a reading within each log record"""

        retval = self.query("LOGREAD? {:d}".format(reading))

        unitnum = retval.split(",")[1]

        if unitnum == "1":
            unitstr = "K"
        elif unitnum == "2":
            unitstr = "C"
        elif unitnum == "3":
            unitstr = "S"
        else:
            unitstr = "L"

        return unitstr


    def get_loginput(self, reading):
        """Return the input number for the specified log reading"""
        retval = self.query("LOGREAD? %d" % reading)

        inputnum = retval.split(",")[1]

        return int(inputnum)


    def get_temp(self, sensor, unit="K"):
        """Get the current reading from sensor (int), in specified units
        (default is Kelvin).  Returns reading as float.

        Raises exception if sensor is inactive, or if K or C is requested
        for a sensor with no calibration curve"""

        # Check if sensor is active
        if self.sensor_enabled(sensor) != True:
            raise ValueError("LAKESHORE: Sensor {:d} is not enabled".format(sensor))

        # If temperature is reqested, check for calibration curve
        if (unit == "K" or unit == "C"):
            if self.sensor_calibrated(sensor) != True:
                raise ValueError("LAKESHORE: Sensor {:d} has no calibration curve".format(sensor))

        if unit=="K": # get reading in Kelvin
            reading = self.query("KRDG? {:d}".format(sensor))

        elif unit=="C": # get reading in Celsius
            reading = self.query("CRDG? {:d}".format(sensor))

        elif unit=="L": # get reading in Linear number
            reading = self.query("LRDG? {:d}".format(sensor))
        else: # get reading in Sensor units
            reading = self.query("SRDG? {:d}".format(sensor))

        return float(reading)


    def sensor_enabled(self, sensor):
        """Checks whether sensor (int) is enabled, returns Python Boolean"""

        onoff = self.query("INPUT? {:d}".format(sensor))

        if onoff == "1":
            return True
        else:
            return False


    def sensor_calibrated(self, sensor):
          """Checks whether sensor (int) has a calibration curve.  Returns
          Python Boolean"""

          calibrated = self.query("INCRV? {:d}".format(sensor))

          if calibrated == "00":
              return False
          else:
              return True

    def get_datetime(self):
          """Gets the data and time from the lakeshore
          - may not be accurate!"""
          datetime = self.query("DATETIME?")

          dl = datetime.split(",")

          return "{:s}/{:s}/{:s};{:s}:{:s}:{:s}".format(dl[1], dl[0], dl[2], dl[3], dl[4], dl[5])

    def write_log(self, filename, log):
          """Write the contents of the log object returned by get_log() to a
          file

          File is tab seperated."""

          f = open(filename, "w")

          for l in log:
              line = l[0]
              for a in l[1:]:
                  line = line + "\t" + str(a)

              f.write(line+"\n")

          f.close()

# HP 8562A Spectrum Analyzer operation code
# Paul Grimes, March 2016

import Instrument
import time

class SpecA(Instrument.Instrument):
  def __init__(self, resource):
    """Create Spectrum Analyzer object from a PyVISA resource:
    rm = pyvisa.ResourceManager()
    sa = SpecA(rm.open_resource("GPIB::21"))

    InstAddr is the address of the spectrum analyzer - try "GPIB::21" by default"""
    self.resource = resource
    self.id = self.idn()

    self.traceSleep = 0.1

    # Get initial frequency sweep data
    self.getFreqSpan()
    self.getFreqCenter()
    self.getFreqStart()
    self.getFreqStop()
    self.getFreqStep()
    self.rbw = self.getRBW()
    self.vbw = self.getVBW()

    self.sweepRun = False

  def idn(self):
    """Get the ID of the instrument"""
    return self.query("ID?")

  def setFreqSpan(self, span):
    """Set frequency span to <span> GHz"""
    self.resource.write("SP " + str(span*1000.0) + "MHZ")

    # Get new frequency sweep data
    self.getFreqSpan()
    self.getFreqCenter()
    self.getFreqStart()
    self.getFreqStop()
    self.getFreqStep()

    self.sweepRun = False

  def getFreqSpan(self):
    """Read the frequency span from the Spectrum Analyzer"""
    self.freq_span = float(self.query("SP?"))/1.0e9
    return self.freq_span


  def setFreqCenter(self, cfreq):
    """Set center frequency to <cfreq> GHz"""
    self.resource.write("CF " + str(cfreq*1000.0) + "MHZ")

    self.getFreqSpan()
    self.getFreqCenter()
    self.getFreqStart()
    self.getFreqStop()
    self.getFreqStep()

    self.sweepRun = False

  def getFreqCenter(self):
    """Read the frequency center from the Spectrum Analyzer"""
    self.freq_center = float(self.query("CF?"))/1.0e9
    return self.freq_center

  def setFreqStart(self, start):
    """Set start frequency to <start> GHz"""
    self.resource.write("FA " + str(start*1000.0) + "MHZ")

    # Get new frequency sweep data
    self.getFreqSpan()
    self.getFreqCenter()
    self.getFreqStart()
    self.getFreqStop()
    self.getFreqStep()

    self.sweepRun = False

  def getFreqStart(self):
    """Read the frequency center from the Spectrum Analyzer"""
    self.freq_start = float(self.query("FA?"))/1.0e9
    return self.freq_start

  def setFreqStop(self, stop):
    """Set start frequency to <stop> GHz"""
    self.resource.write("FB " + str(stop*1000.0) + "MHZ")

    # Get new frequency sweep data
    self.getFreqSpan()
    self.getFreqCenter()
    self.getFreqStart()
    self.getFreqStop()
    self.getFreqStep()

    self.sweepRun = False

  def getFreqStop(self):
    """Read the stop frequency from the Spectrum Analyzer"""
    self.freq_stop = float(self.query("FB?"))/1.0e9

    return self.freq_stop

  def getFreqStep(self):
    """Calculate the frequency step in the trace.

    The HP8562A uses 601 data points per trace."""
    self.freq_step = (self.freq_stop-self.freq_start)/600.

    return self.freq_step


  def setRBW(self, rbw):
    """Set resolution bandwidth in Hz

    Resolution bandwidth should be 1 or 3 times power of 10 in
    range (10Hz - 3MHz).  If other value is passed, valid value above
    requested value will be set.
    (i.e. 101kHz become 300kHz, 99kHz becomes 100kHz)"""
    self.resource.write("RB " + str(rbw) + "HZ")

    self.rbw = self.getRBW()

    self.sweepRun = False

  def getRBW(self):
    """Return the current resolution bandwidth in Hz"""
    self.rbw = float(self.resource.query("RB?"))
    return self.rbw


  def setVBW(self, vbw):
    """Set video bandwidth in Hz

    Video bandwidth should be 1 or 3 times power of 10 in
    range (1Hz - 3MHz).  If other value is passed, valid value above
    requested value will be set.
    (i.e. 101kHz become 300kHz, 99kHz becomes 100kHz)"""
    self.resource.write("VB " + str(vbw) + "HZ")

    self.vbw = self.getVBW()

    self.sweepRun = False

  def getVBW(self):
    """Return the current resolution bandwidth in Hz"""
    self.vbw = float(self.resource.query("VB?"))
    return self.vbw


  def sweep(self, wait=True):
    """Runs a single sweep and waits until complete if wait==True"""
    self.resource.write("TS")

    self.sweepRun = False

    if wait:
        while self.sweepRun == False:
            time.sleep(self.traceSleep)
            if self.resource.query("DONE?") == "1\n":
                break

    self.sweepRun = True
    return self.sweepRun

  def getTrace(self):
    """Return whole trace as [freq, amplitude] pairs"""
    if self.sweepRun == False:
      print "Sweep not run - running now"
      self.sweep()

    # Set the trace data format to real ASCII numbers
    self.resource.write("TDF P")

    # Get the format of the data
    self.log = self.resource.query("LG?")
    self.aunit = self.resource.query("AUNITS?")
    self.refLevel = float(self.resource.query("RL?"))


    # Get trace data from instrument
    # this is in units of 0.01 dBm
    rawData = self.resource.query("TRA?")

    traceData = rawData.strip().split(",")

    data = []
    for f in range(601):
      data.append([(self.freq_start + f*self.freq_step), float(traceData[f])])

    self.trace = data

    return self.trace


# Function to aid in saving trace data to a file
def saveTraceToCSV(trace_data, filename, comment="Spectrum analyzer data"):
  """Save trace data to csv file"""

  header = """
  # {}
  #
  # Frequency Range {} - {}
  # Resolution Bandwidth {}
  # Video Bandwidth {}
  # Amplitude Units {} {}
  # Ref Level {}
  #
  # Freq     Amp
  """.format(comment, self.freq_start, self.freq_stop, self.rbw, self.vbw, self.log, self.aunit, self.refLevel)

  file = open(filename, "w")

  file.write(header+"\n\r")

  for p in trace_data:
    line = str(p[0]) + ", " + str(p[1]) + "\n"
    file.write(line)

  file.close()

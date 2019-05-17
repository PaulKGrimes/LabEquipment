# Anritsu MS26xxx Spectrum Analyzer operation code
# Paul Grimes, Sept. 2008

import visa

class SpecA(object):
  def __init__(self, InstAddr="GPIB::2"):
    """Create Spectrum Analyzer object.

      InstAddr is the address of the spectrum analyzer - try "GPIB::2" by default"""

    self.rm = visa.resource_manager()
    self.inst = self.rm.get_resource(InstAddr)

    self.inst.query("INI?")

    # Get initial frequency sweep data
    self.freq_span = self.inst.query_values("SP?")[0]/1.0e9
    self.freq_centre = self.inst.query_values("CF?")[0]/1.0e9
    self.freq_start = self.inst.query_values("FA?")[0]/1.0e9
    self.freq_stop = self.inst.query_values("FB?")[0]/1.0e9
    self.freq_step = (self.freq_stop-self.freq_start)/500.0
    self.rbw = self.inst.query_values("RB?")[0]
    self.vbw = self.inst.query_values("VB?")[0]

    self.sweep_run = False

  def visa_cmd(self, cmd):
    """Pass VISA command through to instrument

    No checking is done"""
    self.inst.write(cmd)


  def visa_query(self, cmd):
    """Pass VISA query through to instrument and return result

    No checking is done"""
    return self.inst.query(cmd)


  def set_freq_span(self, span):
    """Set frequency span to <span> GHz"""
    self.inst.write("SP " + str(span*1000.0) + "MHZ")

    self.freq_span = self.inst.query_values("SP?")[0]/1.0e9
    # Get new frequency sweep data
    self.freq_start = self.inst.query_values("FA?")[0]/1.0e9
    self.freq_stop = self.inst.query_values("FB?")[0]/1.0e9
    self.freq_step = (self.freq_stop-self.freq_start)/500.0

    self.sweep_run = False

  def get_freq_span(self):
    """Read the frequency span from the Spectrum Analyzer"""
    self.freq_span = self.query_values("SP?")[0]/1.0e9
    return freq_span


  def set_freq_center(self, cfreq):
    """Set center frequency to <cfreq> GHz"""
    self.inst.write("CF " + str(cfreq*1000.0) + "MHZ")

    self.get_freq_center()
    # Get new frequency sweep data
    self.freq_start = self.inst.query_values("FA?")[0]/1.0e9
    self.freq_stop = self.inst.query_values("FB?")[0]/1.0e9
    self.freq_step = (self.freq_stop-self.freq_start)/500.0

    self.sweep_run = False

  def get_freq_center(self):
    """Read the frequency center from the Spectrum Analyzer"""
    self.freq_center = self.query_values("CF?")[0]/1.0e9
    return self.freq_center

  def set_freq_start(self, start):
    """Set start frequency to <start> GHz"""
    self.inst.write("FA " + str(start*1000.0) + "MHZ")

    # Get new frequency sweep data
    self.freq_span = self.inst.query_values("SP?")[0]/1.0e9
    self.freq_centre = self.inst.query_values("CF?")[0]/1.0e9
    self.freq_start = self.inst.query_values("FA?")[0]/1.0e9
    self.freq_stop = self.inst.query_values("FB?")[0]/1.0e9
    self.freq_step = (self.freq_stop-self.freq_start)/500.0

    self.sweep_run = False


  def set_freq_stop(self, stop):
    """Set start frequency to <stop> GHz"""
    self.inst.write("FB " + str(stop*1000.0) + "MHZ")

    # Get new frequency sweep data
    self.freq_span = self.inst.query_values("SP?")[0]/1.0e9
    self.freq_centre = self.inst.query_values("CF?")[0]/1.0e9
    self.freq_start = self.inst.query_values("FA?")[0]/1.0e9
    self.freq_stop = self.inst.query_values("FB?")[0]/1.0e9
    self.freq_step = (self.freq_stop-self.freq_start)/500.0

    self.sweep_run = False


  def sweep(self):
    """Run a single sweep"""
    self.inst.write("TS")

    self.sweep_run = True


  def get_trace(self):
    """Return whole trace as [freq (GHz), amplitude (dBm)] pairs"""
    if self.sweep_run == False:
      print("Sweep not run - running now")
      self.sweep()

    # Get trace data from instrument
    # this is in units of 0.01 dBm
    trace_data = self.inst.query_values("XMA? 0,501")

    data = []
    for f in range(501):
      data.append([(self.freq_start + f*self.freq_step), trace_data[f]/100.0])

    return data


  def set_rbw(self, rbw):
    """Set resolution bandwidth in Hz

    Resolution bandwidth should be 1 or 3 times power of 10 in
    range (10Hz - 3MHz).  If other value is passed, valid value above
    requested value will be set.
    (i.e. 101kHz become 300kHz, 99kHz becomes 100kHz)"""
    self.inst.write("RB " + str(rbw) + "HZ")

    self.rbw = self.inst.query_values("RB?")[0]

    self.sweep_run = False


  def set_vbw(self, vbw):
    """Set video bandwidth in Hz

    Video bandwidth should be 1 or 3 times power of 10 in
    range (1Hz - 3MHz).  If other value is passed, valid value above
    requested value will be set.
    (i.e. 101kHz become 300kHz, 99kHz becomes 100kHz)"""
    self.inst.write("VB " + str(vbw) + "HZ")

    self.vbw = self.inst.query_values("VB?")[0]

    self.sweep_run = False


# Function to aid in saving trace data to a file
def save_trace_to_csv(trace_data, filename, header="# Spectrum analyzer data"):
  """Save trace data to csv file"""

  file = open(filename, "w")

  file.write(header+"\n\r")

  for p in trace_data:
    line = str(p[0]) + ", " + str(p[1]) + "\n"
    file.write(line)

  file.close()

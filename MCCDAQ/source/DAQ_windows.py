#! /usr/bin/env python
##################################################
#                                                #
# Driver for DAQ devices using the MCC UL        #
# for Windows                                    #
#                                                #
# Import this via the DAQ.py wrapper that        #
# selects which of DAQ_windows and DAQ_linux to  #
# import.                                        #
#                                                #
# Note that the windows version works somewhat   #
# differently to the object orientated linux     #
# version.                                       #
#                                                #
# Larry Gardner, July 2018                       #
# Paul Grimes, Oct, 2018                         #
#                                                #
##################################################

from __future__ import print_function, division

from mcculw.ul import *
from .props import ai, ao, digital
from mcculw import enums
from time import sleep
import numpy as np
import ctypes
import hjsonConfig
import pprint

from . import _default_DAQ_config



# Stop InstaCal configurations being used to manage DAQ devices
ignore_instacal()

# For handling memory pointers
def memhandle_as_ctypes_array_scaled(memhandle):
    return ctypes.cast(memhandle, ctypes.POINTER(ctypes.c_double))

class DAQ:
    """A DAQ object representing a MCC DAQ device.

    Differences from Linux version:
        self.daq_device contains the DaqDeviceDescriptor for the
        connect DAQ board, rather than the Daq object.  In combination with self.boardnum,
        this contains all the information available for connnections.
    """
    def __init__(self, config=None, configFile=None, verbose=False, vverbose=False, autoConnect=True):
        """Create the DAQ device, and if autoConnect, automatically connect to
        board number 0"""
        self.verbose = verbose or vverbose
        self.vverbose = vverbose # Set to true to set config object to be verbose

        # Load the default config
        self.config = None
        if self.verbose:
            print("DAQ.__init__: Loading default config")
            pprint.pprint(_default_DAQ_config.defaultConfig)
        self.setConfig(_default_DAQ_config.defaultConfig)

        self.boardnum = None
        self.devices = None
        self.daq_device = None

        self.interface_type = enums.InterfaceType.USB

        if configFile != None:
            if self.verbose:
                print("DAQ.__init__: Reading config from {:s}".format(configFile))
            self.readConfig(configFile)

        if config != None:
            if self.verbose:
                print("DAQ.__init__: Applying passed config:")
                pprint(config)
            self.setConfig(config)


        if autoConnect:
            self.connect(self.config["boardnum"])

    def readConfig(self, filename):
        """Read the .hjson configuration file to set up the DAQ unit."""
        # Opens use file
        self.configFile = filename

        if self.verbose:
            print("DAQ.readConfig: Reading config file: ",self.configFile)
        try:
            newConfig = hjsonConfig.hjsonConfig(filename=filename, verbose=self.vverbose)
            self.setConfig(newConfig)
        except OSError:
            if self.verbose:
                print("DAQ.readConfig: No DAQ config file found, using existing DAQ config.")

    def setConfig(self, config):
        """Merge a new config into the existing config.

        Called automatically from readFile()"""
        if self.verbose:
            print("DAQ.setConfig: Merging config")
            pprint.pprint(config)
            print("DAQ.setConfig: with old config:")
            pprint.pprint(self.config)
        self.config = hjsonConfig.merge(self.config, config)
        self._applyConfig()

    def _applyConfig(self):
        """Apply the configuration to set up the object variables.  Will get
        called automatically from setConfig

        This should be overridden to read any additional configuration values
        when subclassing DAQ.py"""
        if self.verbose:
            print("DAQ._applyConfig: Applying Config:")
            pprint.pprint(self.config)
        try:
            self.AoRange = self.lookUpRange(self.config["DACrange"], "unipolar")
            self.AiMode = self.lookUpMode(self.config["ADCmode"])
            self.AiRange = self.lookUpRange(self.config["ADCrange"], self.config["ADCpolarity"])
            self.DoPort = self.lookUpDioPort(self.config["DOutPort"])
            self.DiPort = self.lookUpDioPort(self.config["DInPort"])
            self.sleepTime = self.config["sleepTime"]
        except KeyError:
            if self.verbose:
                print("DAQ._applyConfig: Got KeyError while applying DAQ config")
                pprint.pprint(self.config)
            raise


    def lookUpMode(self, mode):
        """Look up an Analog Input Mode and return the enum value"""
        return enums.AnalogInputMode[mode.upper()]

    def lookUpRange(self, rang, polarity):
        """Look up a range by maximum voltage and polarity and return the enum value"""
        ulout = None
        for ulr in list(enums.ULRange):
            if ulr.name.startswith(polarity.upper()[0:2]):
                if ulr.range_max == rang:
                    ulout = ulr
                    break
        return ulout

    def lookUpDioPort(self, portName):
        """Look up the DioPort by port name and return the enum value"""
        return enums.DigitalPortType[portName.upper()]


    def listDevices(self):
        """List DAQ devices connected to this machine"""
        try:
            self.devices = get_daq_device_inventory(self.interface_type)
            self.number_of_devices = len(self.devices)
            if self.number_of_devices == 0:
                raise RuntimeError('Error: No DAQ devices found')
            if self.verbose:
                print("Found {:d} DAQ device(s): ".format(self.number_of_devices))
                for i in range(self.number_of_devices):
                    print("    {:s} ({:s})".format(self.devices[i].product_name, self.devices[i].unique_id))
        except (KeyboardInterrupt, ValueError):
            print("Could not find DAQ device(s).")

    def connect(self, boardnum=None):
        """Connects to DAQ device <boardnum>, or to boardnum in config.
        If device is already connected, this will access that device.

        Sets self.daq_device to the DaqDeviceDescriptor for that device."""
        if boardnum == None:
            boardnum = self.config["boardnum"]

        try:
            # Search for devices to get the DAQ ids
            if self.devices == None:
                self.listDevices()
            # Register the board with mcculw and store the descriptor internally
            # if the board is already in use, just steal it...
            try:
                create_daq_device(boardnum, self.devices[boardnum])
            except ULError as err:
                if err.errorcode == enums.ErrorCode.BOARDNUMINUSE:
                    pass
            self.daq_device = self.devices[boardnum]
            self.boardnum = boardnum
            if self.verbose:
                print("Connected to {:s} : {:s}".format(self.daq_device.dev_string, self.daq_device.unique_id))
        except (KeyboardInterrupt, ValueError):
            print("Could not connect to DAQ device {:d}.".format(boardnum))

        # Get some basic info on the device
        self.getAiInfo()
        self.getAoInfo()
        self.getDioInfo()

        # Set the Ai Input mode and range to that specified in __init__
        self.setAiMode(self.AiMode)
        self.setAiRange(self.AiRange)

        self.numChannels()
        self.getAiRange()
        self.getAoRange()

    def disconnect(self):
        """Disconnect DAQ device"""
        if self.daq_device != None:
            boardnum = get_board_number(self.daq_device)
            if boardnum >=0:
                release_daq_device(boardnum)
                if self.verbose:
                    print("DAQ device {:s} is disconnected.".format(self.devices[boardnum].product_name))
            else:
                if self.verbose:
                    print("DAQ device {:s} not connected".format(self.devices[boardnum].product_name))
        self.daq_device = None
        self.boardnum = None
        self.number_of_channels = None

    def name(self, index=0):
        if self.daq_device != None:
            name = self.daq_device.product_name
        else:
            name = None
        return name

    def numChannels(self):
        """Get the number of AI channels"""
        self.number_of_channels = self.AiInfo.num_ai_chans

    def getAiInfo(self):
        """Get AI information using the mcculw examples/props/ai.AnalogInputProps class"""
        if self.daq_device == None:
            raise RuntimeError("DAQ device is not connected")
        self.AiInfo = ai.AnalogInputProps(self.boardnum)

    def getAoInfo(self):
        """Get AO information using the mcculw examples/props/ao.AnalogOutputProps class"""
        if self.daq_device == None:
            raise RuntimeError("DAQ device is not connected")
        self.AoInfo = ao.AnalogOutputProps(self.boardnum)

    def getDioInfo(self):
        """Get DIO information using the mcculw examples/props/digital.DigitalProps class"""
        if self.daq_device == None:
            raise RuntimeError("DAQ device is not connected")
        self.DioInfo = digital.DigitalProps(self.boardnum)

    def setAiMode(self, mode):
        """Sets the AiMode to one of the modes in enums.AnalogInputMode"""
        if self.verbose:
            print("Setting AiMode to {:}".format(mode))
        a_input_mode(self.boardnum, mode)
        self.getAiInfo()
        self.getAiMode()
        self.numChannels()
        self.setAiRange(self.AiRange)
        self.getAiRange()

    def getAiMode(self):
        """Getes the AiMode for the current daq device"""
        self.AiMode = enums.AnalogInputMode(get_config(enums.InfoType.BOARDINFO, self.boardnum, 0, enums.BoardInfo.ADAIMODE))
        return self.AiMode

    def setAiRange(self, range):
        """Sets the AI Range to one of the ranges in enums.ULRange"""
        if self.verbose:
            print("Setting AiRange to {:}".format(range))
        set_config(enums.InfoType.BOARDINFO, self.boardnum, 0, enums.BoardInfo.RANGE, range)
        self.AiRange = range

    def getAiRange(self):
        """Returns the current range of the DAQ"""
        self.AiRange = enums.ULRange(get_config(enums.InfoType.BOARDINFO, self.boardnum, 0, enums.BoardInfo.RANGE))
        return self.AiRange

    def setAiRangeIndex(self, r):
        """Set the Ai Range by the index of the range in self.getRanges()"""
        ranges = self.getAiRanges()
        if r < len(ranges):
            self.AiRange = ranges[r]
        else:
            raise ValueError("Specified Range Index not found")

    def getAiRangeIndex(self):
        """Returns the id of the current AiRange in the list of self.AiInfo.get_ranges(self.AiMode)"""
        ranges = self.getAiRanges()
        return ranges.index(self.AiRange)

    def setAiRangeValue(self, v):
        """Set the AiRange by value"""
        self.setAiRange(enums.ULRange(v))

    def getAiRangeValue(self):
        """Get the value of the current AiRange"""
        return self.getAiRange().value

    def getAiRanges(self):
        return self.AiInfo.available_ranges

    def setAoRange(self, range):
        """Sets the AI Range to one of the ranges in enums.ULRange"""
        set_config(enums.InfoType.BOARDINFO, self.boardnum, 0, enums.BoardInfo.DACRANGE, range)
        self.AoRange = range

    def getAoRangeIndex(self):
        """Returns the id of the current AiRange in the list of avaible ranges"""
        return self.AoInfo.available_ranges.index(self.AoRange)

    def getAoRange(self):
        """Returns the current range of the DAQ"""
        self.AoRange = enums.ULRange(get_config(enums.InfoType.BOARDINFO, self.boardnum, 0, enums.BoardInfo.DACRANGE))
        return self.AoRange

    def AIn(self, channel = 0):
        """Reads input analog data from specified channel - returns value in volts"""
        if self.daq_device == None:
            raise RuntimeError("DAQ device is not connected")
        if channel > self.number_of_channels:
            raise ValueError("channel index requested is higher than number of channels")
        if channel < 0:
            raise ValueError("channel index must be 0 or positive")

        data = v_in(self.boardnum, channel, self.AiRange)
        return data

    def AOut(self, data, channel=0):
        """Write output analog data to the specified channel.  Value is in volts"""
        if self.daq_device == None:
            raise RuntimeError("DAQ device is not connected")
        if channel < 0:
            raise ValueError("channel index must be 0 or positive")

        # Write output analog data to specified channel
        v_out(self.boardnum, channel, self.AoRange, data)

    def DOut(self, data, channel=0, port=None):
        """Write output digital data to specified channel.

        If port is None, look up port in self.DOPort"""
        if self.daq_device == None:
            raise RuntimeError("DAQ device is not connected")

        if port == None:
            port = self.DoPort

        # Look up port in DioInfo - will raise value error if port doesn't exist
        if port == enums.DigitalPortType.FIRSTPORTA:
            port_n = 0
        elif port == enums.DigitalPortType.FIRSTPORTB:
            port_n = 1
        elif port == enums.DigitalPortType.AUXPORT:
            # Guess the AUXPORT is the only one on hardware with it - we don't have any
            port_n = 0
        port_info = self.DioInfo.port_info[port_n]

        # Configure port
        d_config_port(self.boardnum, port_info.type, enums.DigitalIODirection.OUT)

        # Writes output for bit
        d_bit_out(self.boardnum, port_info.type, channel, data)

    def AInScan(self, low_channel, high_channel, rate, samples_per_channel, scan_time = None):
        """Runs a scan across multiple channels, with multiple samples per channel.  Returns a numpy array of
        shape (samples_per_channel, channel_count)"""
        # Verify that the specified device supports hardware pacing for analog input.
        if not self.AiInfo.supports_scan:
            raise Exception('Error: The specified DAQ device does not support scanning analog inputs')

        # Verify the high channel does not exceed the number of channels, low channel is
        #0 or positive and set the channel count.
        if high_channel >= self.number_of_channels:
            high_channel = self.number_of_channels - 1
        if low_channel < 0:
            low_channel = 0

        channel_count = high_channel - low_channel + 1

        # Allocate a buffer to receive the data.
        total_count = samples_per_channel*channel_count
        data = scaled_win_buf_alloc(total_count)
        ctypes_array = memhandle_as_ctypes_array_scaled(data)

        # Set up the scan options
        scan_options = (enums.ScanOptions.CONTINUOUS | enums.ScanOptions.SCALEDATA  | enums.ScanOptions.BACKGROUND)
        try:
            # Start the acquisition.
            a_in_scan(self.boardnum, low_channel, high_channel, total_count,
                                        rate, self.AiRange, data, scan_options)

            status, curr_count, curr_index = get_status(
                    self.boardnum, enums.FunctionType.AIFUNCTION)

            while status != enums.Status.IDLE:
                sleep(self.sleepTime)
                # Get the status of the background operation
                status, curr_count, curr_index = get_status(
                    self.boardnum, enums.FunctionType.AIFUNCTION)

                # Check to see if we are done
                if curr_count >= total_count:
                    break

        finally:
            stop_background(self.boardnum, enums.FunctionType.AIFUNCTION)

        eng_values = []
        for i in range(total_count):
            eng_values.append(ctypes_array[i])
        d = np.array(eng_values)
        d = d.reshape((samples_per_channel, channel_count))

        win_buf_free(data)

        return d


if __name__ == "__main__":
    daq = DAQ()
    data = daq.AIn(0)
    print(data)
    data = daq.AInScan(0,1,10000,1000,1)
    print(data)
    daq.DOut(1)
    daq.disconnect()

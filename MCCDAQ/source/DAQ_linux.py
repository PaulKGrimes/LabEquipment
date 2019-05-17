#! /usr/bin/env python
##################################################
#                                                #
# Driver for DAQ devices using the MCC UL        #
# for linux                                      #
#                                                #
# Import this via the DAQ.py wrapper that        #
# selects which of DAQ_windows and DAQ_linux to  #
# import.                                        #
#                                                #
# Larry Gardner, July 2018                       #
#                                                #
##################################################

from __future__ import print_function, division

from uldaq import *
from time import sleep
import numpy as np
import hjsonConfig

from . import _default_DAQ_config


class DAQ:
    def __init__(self, config=None, configFile=None, verbose=False, vverbose=True, autoConnect=True):
        """Create the DAQ device, and if autoConnect, automatically connect to
        board number 0"""
        self.verbose = verbose or vverbose
        self.vverbose = vverbose # Set to true to set config object to be verbose

        # Load the default config
        self.config = None
        self.setConfig(_default_DAQ_config.defaultConfig)

        self.devices = None
        self.daq_device = None
        self.boardnum = None

        self.interface_type = enums.InterfaceType.USB

        if configFile != None:
            self.readConfig(configFile)

        if config != None:
            self.setConfig(config)

        if autoConnect:
            self.connect(self.config["boardnum"])

    def readConfig(self, filename):
        """Read the .hjson configuration file to set up the DAQ unit."""
        # Opens use file
        self.configFile = filename

        if self.verbose:
            print("Reading config file: ",self.configFile)
        try:
            newConfig = hjsonConfig.hjsonConfig(filename=filename, verbose=self.vverbose)
            self.setConfig(newConfig)
        except OSError:
            if self.verbose:
                print("No DAQ config file found, using existing DAQ config.")

    def setConfig(self, config):
        """Merge a new config into the existing config.

        Called automatically from readFile()"""
        self.config = hjsonConfig.merge(self.config, config)
        self._applyConfig()

    def _applyConfig(self):
        """Apply the configuration to set up the object variables.  Will get
        called automatically from setConfig

        This should be overridden to read any additional configuration values
        when subclassing DAQ.py"""
        self.AoRange = self.lookUpRange(self.config["DACrange"], "unipolar")
        self.AiMode = self.lookUpMode(self.config["ADCmode"])
        self.AiRange = self.lookUpRange(self.config["ADCrange"], self.config["ADCpolarity"])
        self.DoPort = self.lookUpDioPort(self.config["DOutPort"])
        self.DiPort = self.lookUpDioPort(self.config["DInPort"])
        self.sleepTime = self.config("sleepTime")


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
                raise Exception('Error: No DAQ devices found')
            if self.verbose:
                print("Found {:d} DAQ device(s): ".format(self.number_of_devices))
                for i in range(self.number_of_devices):
                    print("    {:s} ({:s})".format(self.devices[i].product_name, self.devices[i].unique_id))
        except (KeyboardInterrupt, ValueError):
            print("Could not find DAQ device(s).")

    def connect(self, boardnum=None):
        """Connects to DAQ device <boardnum>.  If device is already connected,
        this will access that device.

        Sets self.daq_device to the resulting uldaq object."""
        if boardnum == None:
            boardnum = self.config["boardnum"]

        try:
            if self.devices == None:
                self.listDevices()
            if self.daq_device != None:
                del self.daq_device
            self.daq_device = DaqDevice(self.devices[boardnum])
            self.boardnum = boardnum
            # Connect to DAQ device
            descriptor = self.daq_device.get_descriptor()
            if not self.daq_device.is_connected():
                self.daq_device.connect()
            if self.verbose:
                print("Connected to {:s} {:s}".format(descriptor.product_name, descriptor.unique_id))
        except (KeyboardInterrupt, ValueError):
            print("Could not connect to DAQ device.")

        # Get some basic info on the device
        self.AiDevice = self.daq_device.get_ai_device()
        self.getAiInfo()
        self.AoDevice = self.daq_device.get_ao_device()
        self.getAoInfo()
        self.DioDevice = self.daq_device.get_dio_device()
        self.getDioInfo()

        # Set the Ai Input mode and range to that specified in __init__
        self.setAiMode(self.AiMode)
        self.setAiRange(self.AiRange)
        self.setAoRange(self.AoRange)

        self.numChannels()
        self.getAiRange()
        self.getAoRange()

    def disconnect(self):
        """Disconnects DAQ device"""
        if self.daq_device != None:
            del self.daq_device
            if self.verbose:
                    print("DAQ device {:s} {:s} is disconnected.".format(self.devices[self.boardnum].product_name, self.devices[self.boardnum].unique_id))
        else:
            if self.verbose:
                print("DAQ device {:s} not connected".format(self.devices[self.boardnum].product_name))
        self.daq_device = None
        self.boardnum = None
        self.number_of_channels = None


    def name(self, index = 0):
        if self.devices != None:
            name = self.devices[index].product_name
        else:
            name = None
        return name

    def numChannels(self):
        """Get the number of channels in the current AI Mode"""
        self.number_of_channels = self.AiInfo.get_num_chans_by_mode(self.AiMode)

    def getAiInfo(self):
        """Get the AI Info object"""
        if self.daq_device == None:
            raise RuntimeError("DAQ device is not connected")
        self.AiInfo = self.AiDevice.get_info()

    def getAoInfo(self):
        """Get the AO Info object"""
        if self.daq_device == None:
            raise RuntimeError("DAQ device is not connected")
        self.AoInfo = self.AoDevice.get_info()

    def getDioInfo(self):
        """Get the DIO Info object"""
        if self.daq_device == None:
            raise RuntimeError("DAQ device is not connected")
        self.DioInfo = self.DioDevice.get_info()

    def setAiMode(self, mode):
        """Set the AiMode to one of the modes in AnalogInputMode"""
        self.AiMode = mode
        self.getAiInfo()
        self.numChannels()
        self.setAiRange(self.AiInfo.get_ranges(self.AiMode)[0])
        self.getAiRange()

    def getAiMode(self):
        """Get the AiMode"""
        return self.AiMode

    def setAiRange(self, r):
        """Set the AI Range to one of the members of Range class"""
        self.AiRange = r

    def getAiRange(self):
        """Get the AI Range"""
        return self.AiRange

    def setAiRangeIndex(self, r):
        """Sets the AI Range to the index r in the list of ranges returned by
        self.AiInfo.get_ranges(self.AiMode)"""
        ranges = self.getAiRanges()
        if r < len(ranges):
            self.AiRange = ranges[r]
        else:
            raise ValueError("Specified range index not found")

    def getAiRangeIndex(self):
        """Returns the index of the current AiRange in the list of
        self.AiInfo.get_ranges(self.AiMode)"""
        ranges = self.getAiRanges()
        return ranges.index(self.AiRange)

    def setAiRangeValue(self, v):
        """Set the AiRange by value"""
        self.setAiRange(Range(v))

    def getAiRangeValue(self):
        """Set the value of the AiRange"""
        return self.getAiRange().value

    def getAiRanges(self):
        """Returns the list of valid ranges for this DAQ"""
        return self.AiInfo.get_ranges(self.AiMode)

    def setAoRange(self, r):
        """Sets the AO Range to one of the members of the Range class"""
        self.AoRange = r

    def getAoRange(self):
        """Returns the current AO Range"""
        return self.AoRange

    def setAiRangeIndec(self, r):
        """Sets the AO Range to one of the ranges returned by AoGetRanges()"""
        ranges = self.getAoInfoRanges()
        if r < len(ranges):
            self.AoRange = ranges[r]
        else:
            raise ValueError("Specified range index not found")

    def getAiRangeIndex(self):
        """Returns the index of the current AoRange in the list of ranges
        returned by self.getAoRanges()"""
        ranges = self.getAoRanges()
        return ranges.index(self.AoRange)

    def getAiRanges(self):
        """Returns the list of available AoRanges"""
        self.AoInfo.get_ranges()


    def AIn(self, channel = 0):
        """Reads input analog data from specified channel"""
        if self.daq_device == None:
            raise RuntimeError("DAQ device is not connected")
        if channel > self.number_of_channels:
            raise ValueError("channel index requested is higher than number of channels")
        if channel < 0:
            raise ValueError("channel index must be 0 or positive")
        data = self.AiDevice.a_in(channel, self.AiMode, self.AiRange, AInFlag.DEFAULT)
        return data

    def AOut(self, data, channel=0):
        """Write output analog data to specified channel"""
        if self.daq_device == None:
            raise RuntimeError("DAQ device is not connected")
        if channel < 0:
            raise ValueError("channel index must be 0 or positive")
        self.AoDevice.a_out(channel, self.AoRange, AOutFlag.DEFAULT, data)

    def DOut(self, data, channel=0, port=DigitalPortType.FIRSTPORTA):
        """Write output digital data to specified channel"""
        # Configure port
        self.DioDevice.d_config_port(port, DigitalDirection.OUTPUT)

        # Writes output for bit
        self.DioDevice.d_bit_out(port, channel, data)

    def AInScan(self, low_channel, high_channel, rate, samples_per_channel, scan_time = None):
        """Runs a scan across multiple channels, with multiple samples per channel.  Returns a numpy array of
        shape (samples_per_channel, channel_count)"""
        # Verify that the specified device supports hardware pacing for analog input.
        if not self.AiInfo.has_pacer():
            raise Exception('Error: The specified DAQ device does not support hardware paced analog input')

        # Verify the high channel does not exceed the number of channels, and
        # set the channel count.
        if high_channel >= self.number_of_channels:
            high_channel = self.number_of_channels - 1
        channel_count = high_channel - low_channel + 1

        # Allocate a buffer to receive the data.
        data = create_float_buffer(channel_count, samples_per_channel)

        try:
            # Start the acquisition.
            self.AiDevice.a_in_scan(low_channel, high_channel, self.AiMode, self.AiRange, samples_per_channel,
                                            rate, ScanOption.CONTINUOUS, AInScanFlag.DEFAULT, data)

            start_time = time.time()

            # Set scan time to a high number of seconds if it isn't set
            if scan_time == None:
                scan_time = 500000

            while (time.time() - start_time) <= scan_time:
                # Get the status of the background operation
                status, transfer_status = self.AiDevice.get_scan_status()
                index = transfer_status.current_index

                # Check to see if we are done
                if transfer_status.current_scan_count >= samples_per_channel:
                    break

                sleep(self.sleepTime)
        finally:
            if self.daq_device:
                # Stop the acquisition if it is still running.
                if status == ScanStatus.RUNNING:
                    self.AiDevice.scan_stop()

        d = np.array(data)
        d = d.reshape((samples_per_channel, channel_count))

        return d


if __name__ == "__main__":
    daq = DAQ()
    data = daq.AIn(0)
    print(data)
    data = daq.AInScan(0,1,10000,1000,1)
    print(data)
    daq.DOut(1)
    daq.disconnect()

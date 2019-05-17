# creates a default configuration for a DAQ object

import hjsonConfig
from pkg_resources import resource_filename
from pprint import pprint

verbose=False

filename = resource_filename("MCCDAQ", "config/DAQ-default.hjson")

if verbose:
    print("_default_DAQ_config: reading defaultConfig from {:s}".format(filename))
defaultConfig = hjsonConfig.hjsonConfig(filename=filename, verbose=verbose)

if verbose:
    print("_default_DAQ_config: Got defaultConfig:")
    pprint(defaultConfig)

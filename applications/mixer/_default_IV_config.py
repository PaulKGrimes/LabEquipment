# creates a default configuration for a DAQ object

from lib import hjsonConfig
import os

fileName = os.path.join(os.path.dirname(__file__), "config/IV_default.hjson")
defaultConfig = hjsonConfig.hjsonConfig(fileName=fileName)
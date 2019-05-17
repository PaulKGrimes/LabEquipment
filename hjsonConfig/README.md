# hjsonConfig
Implements a method for reading configurations from hjson files into a python dictionary structure.  Other hjson config files can be included into the top level config file, with settings in the higher level config files overriding those duplicated in the included files.

The code should work equally well with strict json inputs, and would work with json 5 if the comment character was changed from "#" to "//"

This code has been developed for use in the Smithsonian Astrophysical Observatory's Receiver Lab's software.

# Installation
## Prerequisites

* jsonmerge
* hjson

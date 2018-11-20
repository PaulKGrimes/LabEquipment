#! /usr/bin/env python
from __future__ import print_function

import jsonmerge
import hjson
import copy
from pprint import pprint
from pkg_resources import resource_filename

def merge(base, head):
    """Merge two hjsonConfig objects together, using jsonmerge.merge"""
    try:
        if base !=None:
            verbose = base.verbose or head.verbose
        else:
            verbose = head.verbose
    except AttributeError:
        verbose = False

    if base != None:
        out = hjsonConfig(verbose=verbose)
    else:
        out = hjsonConfig(verbose=verbose)

    merged = jsonmerge.merge(base, head)
    out._copyIn(merged)
    return out

class hjsonConfig(hjson.OrderedDict):
    """A class to handle reading configurations in hjson files, which
    may include references to other hjson files via "config-file" entries.

    Entries duplicated in the top level file override the entries in an included file."""
    def __init__(self, *args, fileName=None, verbose=False, **kwds):
        """Very basic set up"""
        super(hjson.OrderedDict, self).__init__(*args, **kwds)
        self.verbose = verbose
        self.fileName = fileName
        if fileName != None:
            if self.verbose:
                print("hjsonConfig: Initializing from {:s}".format(fileName))
            self.readFile(fileName)

    def _readFile(self, fileName):
        """Read an .hjson configuration file and return"""
        # Opens use file and assigns corresponding parameters
        if self.verbose:
            print("hjsonConfig: Reading file: ", fileName)
        try:
            f = open(fileName, 'r')
            newConfig = hjsonConfig(verbose=self.verbose)
            newConfig._copyIn(hjson.load(f))
            f.close()
            if self.verbose:
                print("    hjsonConfig: Got config:")
                pprint(newConfig)
            newConfig.importConfigFiles()
        except OSError:
            print("OS Error received")
            try:
                # File not found in pwd
                # Look in same directory as current file
                print("hjsonConfig: Couldn't find config file: ", fileName)
                if self.fileName != None:
                    print("hjsonConfig: looking in {:s}config".format(__name__))
                    newFileName = resource_filename(__name__, "config/{:s}".format(fileName))
                    if self.verbose:
                        print("hjsonConfig: New fileName:", newFileName)
                else:
                    return None

                # check we aren't setting up an infinite loop
                if newFileName != fileName:
                    print("hjsonConfig: Trying config file: ", newFileName)
                    newConfig = hjsonConfig(fileName=newFileName, verbose=self.verbose)
                else:
                    return None
            except OSError:
                if self.verbose:
                    print("hjsonConfig: File {:s} not found.".format(fileName))
                return None
        return newConfig

    def _copyIn(self, odict):
        """Delete all this objects data and copy in data from odict"""
        if odict != None:
            self.clear()
            for k in odict.keys():
                self[k] = odict[k]
        else:
            pass

    def readFile(self, fileName):
        """Read a config file from fileName"""
        # Have to delete data from self and then copy data from readFile return value.
        if self.fileName == None:
            print("hjsonConfig: setting fileName: ", fileName)
            self.fileName = fileName
        self._copyIn(self._readFile(fileName))
        self.importConfigFiles()


    def importConfigFiles(self):
        """Merge in referenced config files if present.

        Entries in the current config overwrite any entries read from the file.
        This allows this function to be called recursively to build up a complete
        config that refers to default settings stored in default configs."""
        # If a config json OrderedDict is passed, merge it with the existing configuration
        # Try and parse a config-file if it is passed to us
        configFile = None
        try:
            if self["config-file"] != None:
                configFile = self["config-file"]
                if self.verbose:
                    print("hjsonConfig: Import from {:s}".format(configFile))

        except KeyError:
            if self.verbose:
                print("hjsonConfig: No config-files to import")
            configFile = None

        if configFile != None:
            # Might be a list of fileNames or a single fileName
            if type(configFile) is type(list()):
                if self.verbose:
                    print("hjsonConfig: Importing config-files {:s}".format(configFile))
                fileConfig = hjsonConfig(verbose=self.verbose)
                for c in configFile:
                    f = self._readFile(c)
                    fileConfig._copyIn(jsonmerge.merge(fileConfig, f))
            else:
                if self.verbose:
                    print("hjsonConfig: Importing config-file {:s}".format(configFile))
                fileConfig = self._readFile(configFile)
            if self.verbose:
                pprint(fileConfig)

            # We will move imported config-files to "imported-config-file"
            self["config-file"] = None
            try:
                 self["imported-config-file"].append(configFile)
            except KeyError:
                self["imported-config-file"] = [configFile]


            # clear self and copy the merged ODict from jsonmerge in
            self._copyIn(jsonmerge.merge(fileConfig, self))

if __name__ == "__main__":
    config = hjsonConfig(fileName="test/test.hjson", verbose=True)

    print("Final config:")
    pprint(config)

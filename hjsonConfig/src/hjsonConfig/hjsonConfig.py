#! /usr/bin/env python
from __future__ import print_function

import jsonmerge
import hjson
import copy
from pprint import pprint
from pkg_resources import resource_filename

defaultDir = None

def merge(base, head):
    """Merge two config objects together, using jsonmerge.merge(). Keys in head
    will overwrite duplicate keys in base.

    Parameters:
        base: hjsonConfig object or other type understood by jsonmerge
        head: hjsonConfig object or other type understoof by jsonmerge.
    Returns:
        hjsonConfig object that is a combination of base and head.
    """
    try:
        if base !=None:
            verbose = base.verbose or head.verbose
        else:
            verbose = head.verbose
    except AttributeError:
        verbose = False

    out = hjsonConfig(verbose=verbose)

    merged = jsonmerge.merge(base, head)
    out._copyIn(merged)
    return out


class hjsonConfig(hjson.OrderedDict):
    """A class to handle reading configurations in hjson files, which
    may include references to other hjson files via "config-file" entries.

    Entries duplicated in the top level file override the entries in an included file."""
    def __init__(self, *args, filename=None, verbose=False, **kwds):
        """Very basic set up"""
        super(hjson.OrderedDict, self).__init__(*args, **kwds)
        self.verbose = verbose
        self.filename = filename
        if filename != None:
            if self.verbose:
                print("hjsonConfig.__init__: Initializing from {:s}".format(filename))
            self.readFile(filename)

    def _readFile(self, filename, dir=None):
        """Read an .hjson configuration file and return.

        If <filename> is not found in the current directory, look in dir first, then
        module level defaultDir."""
        assert filename != None
        if self.verbose:
            print("hjsonConfig._readFile: Reading file: ", filename)
        try:
            f = open(filename, 'r')
            newConfig = hjsonConfig(verbose=self.verbose)
            newConfig._copyIn(hjson.load(f))
            f.close()
            if self.verbose:
                print("hjsonConfig._readFile: Got config:")
                pprint(newConfig)
            newConfig.importConfigFiles()
            return newConfig
        except OSError:
            if dir != None:
                try:
                    if self.verbose:
                        print("hjsonConfig._readFile: Couldn't find config file {:s} in current directory, trying {:s}", (filename, dir))
                    ### FIX THIS ###
                    newFileName = resource_filename("LabEquipment", "/config/{:s}".format(filename))
                    # check we aren't setting up an infinite loop
                    if newFileName == filename:
                        if self.verbose:
                            raise RunTimeError("hjsonConfig._readFile: Circular reference to config file {:s}".format(newFileName))
                        return None
                    if self.verbose:
                        print("hjsonConfig._readFile: Trying config file: ", newFileName)
                    newConfig = hjsonConfig(filename=newFileName, verbose=self.verbose)
                    return newConfig
                except OSError:
                    if self.verbose:
                        print("hjsonConfig._readFile: File {:s} not found.".format(newFileName))

            # We either fall through to here if filename isn't in dir, or get here directly if dir == None
            try:
                if self.verbose:
                    print("hjsonConfig._readFile: Couldn't find config file {:s}, trying {:s}", (filename, defaultDir))
                ### FIX THIS ###
                newFileName = resource_filename(defaultDir, "/config/{:s}".format(filename))
                # check we aren't setting up an infinite loop
                if newFileName == filename:
                    if self.verbose:
                        raise RunTimeError("hjsonConfig._readFile: Circular reference to config file {:s}".format(newFileName))
                    return None
                if self.verbose:
                    print("hjsonConfig._readFile: Trying config file: ", newFileName)
                newConfig = hjsonConfig(filename=newFileName, verbose=self.verbose)
                return newConfig
            except OSError:
                # Raise an error this time, because we just can't find the file
                raise RunTimeError("hjsonConfig._readFile: File {:s} not found.".format(filename))
        return None

    def _copyIn(self, odict):
        """Delete all this objects data and copy in data from odict"""
        if odict != None:
            self.clear()
            for k in odict.keys():
                self[k] = odict[k]
        else:
            pass

    def readFile(self, filename):
        """Read a config file from filename"""
        # Have to delete data from self and then copy data from readFile return value.
        if self.filename == None:
            if self.verbose:
                print("hjsonConfig.readFile: setting filename: ", filename)
            self.filename = filename
        self._copyIn(self._readFile(filename))



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
                    print("hjsonConfig.importConfigFiles: Import from {:s}".format(configFile))

        except KeyError:
            if self.verbose:
                print("hjsonConfig.importConfigFiles: No config-files to import")
            configFile = None

        if configFile != None:
            # Might be a list of fileNames or a single filename
            if type(configFile) is type(list()):
                if self.verbose:
                    print("hjsonConfig.importConfigFiles: Importing config-files {:s}".format(configFile))
                fileConfig = hjsonConfig(verbose=self.verbose)
                for c in configFile:
                    f = self._readFile(c)
                    fileConfig._copyIn(jsonmerge.merge(fileConfig, f))
            else:
                if self.verbose:
                    print("hjsonConfig.importConfigFiles: Importing config-file {:s}".format(configFile))
                fileConfig = hjsonConfig(filename=configFile, verbose=self.verbose)
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
    config = hjsonConfig(filename="test/test.hjson", verbose=True)

    print("Final config:")
    pprint(config)

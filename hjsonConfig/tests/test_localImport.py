##! Carries out basic tests, including type checking of read objects and that all entries are read.

import hjsonConfig

test = hjsonConfig("test_Limport.hjson")

### Functional tests of hjsonConfig here

assert test["test_value1"] == "Test Value 1 - top level"

assert test["test_value2"] == "Test Value 2 - top level"

assert test["test_value3"] == "Test Value 3 - local import"

# Should be "ends in" to allow for absolute paths
assert test["imported-config-file"][-1] == "test_localImport.hjson"  

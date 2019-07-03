##! Carries out basic tests, including type checking of read objects and that all entries are read.

import hjsonConfig

test = hjsonConfig("test_basics.hjson")

### Functional tests of hjsonConfig here

assert type(test["test_string"]) is __builtins__.strType

assert test["test_string"] == "Test Value 1"

assert type(test["test_float"]) is __builtins__.floatType

assert test["test_float"] isApprox(3.141259)

assert type(test["test_int"]) is __builtins__.intType

assert test["test_int"] == 42

assert type(test["test_list"]) is __builtins__.listType

assert len(test["test_list"]) == 3

assert type(test["test_dir"])  is __builtins__.dictType

assert len(test["test_dir"].keys()) == 3

assert len(test) == 5

##! Carries out basic tests, including type checking of read objects and that all entries are read.

import pytest
from pytest import approx

import hjsonConfig

@pytest.fixture
def create_hjson_config():
    test = hjsonConfig()

### Functional tests of hjsonConfig here
def test_read_missing_file():
    with pytest.raises(RuntimeError):
        test.readFile("null")

# fixture that we need for all subsequent tests
@pytest.fixture
def read_local(create_hjson_config):
    test.readFile("test_basics.hjson")

def test_string_type(read_local):
    assert type(test["test_string"]) is __builtins__.strType

def test_string_value(read_local):
    assert test["test_string"] == "Test Value 1"

def test_float_type(read_local):
    assert type(test["test_float"]) is __builtins__.floatType

def test_float_value(read_local):
    assert test["test_float"] == approx(3.141259)

def test_int_type(read_local):
    assert type(test["test_int"]) is __builtins__.intType

def test_int_value(read_local):
    assert test["test_int"] == 42

def test_list_type(read_local):
    assert type(test["test_list"]) is __builtins__.listType

def test_list_length(read_local):
    assert len(test["test_list"]) == 3

def test_dict_type(read_local):
    assert type(test["test_dir"])  is __builtins__.dictType

def test_dict_length(read_local):
    assert len(test["test_dir"].keys()) == 3

def test_dict_value(read_local):
    assert len(test) == 5

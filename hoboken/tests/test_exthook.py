# -*- coding: utf-8 -*-

import sys
import types

from mock import patch, MagicMock
from hoboken.exthook import ImportRedirector

module_list = []

def sys_modules_side_effect(import_name):
    temp_mod = MagicMock()
    module_list.append(temp_mod)
    sys.modules[import_name] = temp_mod
    return temp_mod


def sys_modules_builtins_side_effect(import_name):
    if 'builtins' in import_name:
        return None

    temp_mod = MagicMock()
    module_list.append(temp_mod)
    sys.modules[import_name] = temp_mod
    return temp_mod


def cleanup_sys_modules():
    keys = []
    for m in module_list:
        for k, v in sys.modules.items():
            if v is m:
                keys.append(k)

    for k in keys:
        del sys.modules[k]


def test_has_module():
    i = ImportRedirector('foobar1', 'foobar1_%s')
    assert isinstance(i.module, types.ModuleType)


def test_will_ignore_properly():
    i = ImportRedirector('foobar2', 'foobar2_%s')

    assert i.find_module('asdf') is None
    assert i.find_module('another.two') is None


def test_will_return_existing():
    i = ImportRedirector('foobar3', 'foobar3_%s')

    m = i.load_module('sys')
    assert m is sys


def test_will_import_basic():
    i = ImportRedirector('foobar4', 'foobar4_%s')
    i.import_func = MagicMock(side_effect=sys_modules_side_effect)

    mod = i.load_module('foobar4.another')
    i.import_func.assert_called_with('foobar4_another')

    assert mod is sys.modules['foobar4.another']
    assert mod is sys.modules['foobar4_another']
    assert mod is i.module.another

def test_will_import_from_builtins():
    i = ImportRedirector('foobar5', 'foobar5_%s', builtins='foobar5.builtins')
    i.import_func = MagicMock(side_effect=sys_modules_side_effect)

    mod = i.load_module('foobar5.another')
    i.import_func.assert_called_once_with('foobar5.builtins.another')

    assert mod is sys.modules['foobar5.another']
    assert mod is sys.modules['foobar5.builtins.another']
    assert mod is i.module.another


def test_will_import_from_regular_when_builtins_fail():
    i = ImportRedirector('foobar6', 'foobar6_%s', builtins='foobar6.builtins')
    i.import_func = MagicMock(side_effect=sys_modules_side_effect)

    mod = i.load_module('foobar6.another')
    i.import_func.assert_called_once_with('foobar6.builtins.another')

    assert mod is sys.modules['foobar6.another']
    assert mod is sys.modules['foobar6.builtins.another']
    assert mod is i.module.another

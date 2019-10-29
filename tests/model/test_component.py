# -*- coding: utf-8 -*-
import unittest

from .. import flowlib_test_utils


class TestComponent(unittest.TestCase):

    def test_load_components(self):
        flowlib_test_utils.load_test_component('component.yaml')

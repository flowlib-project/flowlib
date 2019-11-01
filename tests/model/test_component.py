# -*- coding: utf-8 -*-
import unittest

from tests import utils


class TestComponent(unittest.TestCase):

    def test_load_components(self):
        utils.load_test_component('test-component.yaml')

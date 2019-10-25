# -*- coding: utf-8 -*-
import os
import unittest

from flowlib.parser import init_flow, replace_flow_element_vars_recursive

from . import flowlib_test_utils

class TestParser(unittest.TestCase):

    def test_init_flow(self):
        component_dir = os.path.join(flowlib_test_utils.INIT_DIR, 'components')
        flow = flowlib_test_utils.load_test_flow(init=False)
        init_flow(flow, component_dir)

        self.assertIsInstance(flow.raw, dict)
        self.assertTrue(len(flow._elements.keys()) > 0)
        self.assertTrue(len(flow.components.keys()) == 3)
        self.assertIsNotNone(flow._controllers)
        self.assertTrue(len(flow._controllers) == 1)

    def test_var_injection(self):
        flow = flowlib_test_utils.load_simple_flow()
        replace_flow_element_vars_recursive(flow, flow._elements, flow.components)

        self.assertEqual(flow._elements.get('debug').config.properties['property'], 'xyz')
        # todo:

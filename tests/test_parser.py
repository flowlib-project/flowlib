# -*- coding: utf-8 -*-
import os
import unittest

from flowlib.model import FlowLibException
from flowlib.parser import init_flow, replace_flow_element_vars_recursive

from . import flowlib_test_utils

class TestParser(unittest.TestCase):

    def test_init_flow(self):
        component_dir = os.path.join(flowlib_test_utils.RESOURCES_DIR, 'components')
        flow = flowlib_test_utils.load_test_flow(init=False)
        init_flow(flow, component_dir)

        self.assertIsInstance(flow.raw, dict)
        self.assertTrue(len(flow._elements.keys()) > 0)
        self.assertTrue(len(flow.components.keys()) == 1)
        self.assertIsNotNone(flow._controllers)
        self.assertTrue(len(flow._controllers) == 1)


    def test_required_controller(self):
        component_dir = os.path.join(flowlib_test_utils.RESOURCES_DIR, 'components')
        flow = flowlib_test_utils.load_test_flow(init=False)

        pg = [e for e in flow.canvas if e['name'] == 'test-process-group'][0]
        pg['controllers'] = dict()
        self.assertRaisesRegex(FlowLibException, '^Missing required_controllers.*', init_flow, flow, component_dir)


    def test_required_var(self):
        component_dir = os.path.join(flowlib_test_utils.RESOURCES_DIR, 'components')
        flow = flowlib_test_utils.load_test_flow(init=False)

        pg = [e for e in flow.canvas if e['name'] == 'test-process-group'][0]
        pg['vars'] = dict()
        self.assertRaisesRegex(FlowLibException, '^Missing required_vars.*', init_flow, flow, component_dir)


    def test_var_injection(self):
        # unset env for jinja helper lookup
        os.environ.clear()
        os.environ['NO_DEFAULT'] = 'env value set'

        flow = flowlib_test_utils.load_test_flow()
        replace_flow_element_vars_recursive(flow, flow._elements, flow.components)

        # check env lookup and controller var injection
        controller = flow._elements.get('test-process-group').controllers.get('test_controller')
        self.assertIsNotNone(controller)
        self.assertEqual(controller.config.properties['no_default'], 'env value set')
        self.assertEqual(controller.config.properties['with_default'], 'default value set')

        # check canvas-level processor var injection
        self.assertEqual(flow._elements.get('debug').config.properties['prop1'], 'constant-value')
        self.assertEqual(flow._elements.get('debug').config.properties['prop2'], flow.global_vars['global_var'])

        # check component var injection
        component = flow.find_component_by_path('component.yaml')
        pg = flow._elements.get('test-process-group')
        props = flow._elements.get('test-process-group')._elements.get('debug').config.properties
        self.assertEqual(props['prop1'], 'constant-value') # test constant
        self.assertEqual(props['prop2'], flow.global_vars['global_var']) # test global
        self.assertEqual(props['prop3'], component.defaults['default_var1']) # test component default
        self.assertEqual(props['prop4'], pg.vars['default_var2']) # test override component default

        # We can't test the controller lookup because the controller has not been created in NiFi yet
        # so there is no uuid to lookup. This should probably be refactored so that it can be unit tested.
        # For now it will be tested by the itests
        # self.assertEqual(props['controller-lookup'], 'controller') # test controller

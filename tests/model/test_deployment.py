# -*- coding: utf-8 -*-
import os
import json
import unittest

from flowlib.model import FlowLibException
from flowlib.model.deployment import FlowDeployment, DeployedComponent

from .. import flowlib_test_utils

class TestDeployment(unittest.TestCase):

    def test_from_dict(self):
        with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'resources', 'deployment.json'), 'r') as f:
            d = json.load(f)
        deployment = FlowDeployment.from_dict(d)
        self.assertIsNotNone(deployment)
        self.assertTrue(deployment.flow['name'] == 'pdf-processor-demo-flow')
        self.assertTrue(len(deployment.components) == 3)
        self.assertIsInstance(deployment.get_component('Process PDFs'), DeployedComponent)

    def test_add_get_component(self):
        flow = flowlib_test_utils.load_init_flow()
        deployment = FlowDeployment(flow.raw)
        component = flowlib_test_utils.load_init_component('common/s3_write_with_retry.yaml')
        deployment.add_component(DeployedComponent(component.raw))

        self.assertTrue(len(deployment.components) == 1)
        deployed_component = deployment.get_component('S3 Write With Retry')
        self.assertIsInstance(deployed_component, DeployedComponent)
        self.assertEqual(component.raw, deployed_component.component)
        self.assertRaisesRegex(FlowLibException, "^A component named\s.*\salready exists$", deployment.add_component, DeployedComponent(component.raw))

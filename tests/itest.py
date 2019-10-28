# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import unittest
from unittest import TestSuite, TestResult, TestLoader

import flowlib.api
from flowlib.nifi.rest import wait_for_nifi_api
from flowlib.model.config import FlowLibConfig
from flowlib.model import FlowLibException

from flowlib_test_utils import RESOURCES_DIR


class ITestFlowLib(unittest.TestCase):

    tmp_dir = tempfile.TemporaryDirectory()
    endpoint = 'http://127.0.0.1:8080'

    @classmethod
    def setUpClass(cls):
        try:
            flowlib.api.gen_flow_scaffold(os.path.join(cls.tmp_dir.name, 'dataflow'))
            wait_for_nifi_api(cls.endpoint, retries=2, delay=3)
        except FlowLibException:
            raise unittest.SkipTest("NiFi Rest endpoint is not available on {}, will not run ITestFlowLibApi TestCase".format(cls.endpoint))

    @classmethod
    def tearDownClass(cls):
        cls.tmp_dir.cleanup()

    def setUp(self):
        os.chdir(os.path.join(self.__class__.tmp_dir.name, 'dataflow'))

    def test_configure_flow_controller(self):
        with open(os.path.join(self.__class__.tmp_dir.name, 'dataflow', '.flowlib.yml'), 'r') as f:
            config = FlowLibConfig.new_from_file(f)
        config.nifi_endpoint = self.__class__.endpoint
        flowlib.api.configure_flow_controller(config)

    def test_deploy_flow(self):
        with open(os.path.join(self.__class__.tmp_dir.name, 'dataflow', '.flowlib.yml'), 'r') as f:
            config = FlowLibConfig.new_from_file(f)
        config.nifi_endpoint = self.__class__.endpoint
        config.zookeeper_connection = '127.0.0.1:2181'
        config.flow_yaml = os.path.join(self.__class__.tmp_dir.name, 'dataflow', 'flow.yaml')
        flowlib.api.deploy_flow(config)

    def test_redeploy_flow(self):
        with open(os.path.join(self.__class__.tmp_dir.name, 'dataflow', '.flowlib.yml'), 'r') as f:
            config = FlowLibConfig.new_from_file(f)
        config.nifi_endpoint = self.__class__.endpoint
        config.zookeeper_connection = '127.0.0.1:2181'
        config.force = True
        config.flow_yaml = os.path.join(self.__class__.tmp_dir.name, 'dataflow', 'flow.yaml')
        flowlib.api.deploy_flow(config)

    def test_gen_flowlib_docs(self):
        with open(os.path.join(self.__class__.tmp_dir.name, 'dataflow', '.flowlib.yml'), 'r') as f:
            config = FlowLibConfig.new_from_file(f)
        config.nifi_endpoint = self.__class__.endpoint
        config.force = True
        flowlib.api.gen_flowlib_docs(config, config.docs_directory)

    def test_list_components(self):
        with open(os.path.join(self.__class__.tmp_dir.name, 'dataflow', '.flowlib.yml'), 'r') as f:
            config = FlowLibConfig.new_from_file(f)
        flowlib.api.list_components(config, 'processors')
        self.assertRaisesRegex(FlowLibException, '^Invalid component type.*', flowlib.api.list_components, config, 'invalid-type')

    def test_describe_component(self):
        with open(os.path.join(self.__class__.tmp_dir.name, 'dataflow', '.flowlib.yml'), 'r') as f:
            config = FlowLibConfig.new_from_file(f)
        flowlib.api.describe_component(config, 'controller', 'org.apache.nifi.processors.aws.credentials.provider.service.AWSCredentialsProviderControllerService')
        self.assertRaisesRegex(FlowLibException, '^Invalid component type.*', flowlib.api.describe_component, config, 'invalid-type', 'not.a.valid.package.id')
        self.assertRaisesRegex(FlowLibException, '^Component descriptor\s.*\sdoes not exist', flowlib.api.describe_component, config, 'processor', 'not.a.valid.package.id')


def suite():
    suite = unittest.TestSuite()
    # addTest in the order that they should run

    # TODO: Better assertions for these tests
    suite.addTest(ITestFlowLib('test_configure_flow_controller'))
    suite.addTest(ITestFlowLib('test_deploy_flow'))
    suite.addTest(ITestFlowLib('test_redeploy_flow'))
    # TODO: Set the zookeeper state for the lists3 processor
    # and confirm that state is migrated after the re-deploy

    # TODO: Fix these tests but leave them commented
    # suite.addTest(ITestFlowLib('test_gen_flowlib_docs'))
    # suite.addTest(ITestFlowLib('test_list_components'))
    # suite.addTest(ITestFlowLib('test_describe_component'))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner(failfast=True)
    runner.run(suite())

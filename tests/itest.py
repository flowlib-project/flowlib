# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import unittest
from unittest import TestSuite, TestResult, TestLoader

import nipyapi
from nipyapi.nifi.models import ProcessorEntity, ProcessGroupEntity

import flowlib.api
from flowlib.nifi.state import ZookeeperClient
from flowlib.nifi.rest import wait_for_nifi_api
from flowlib.model.config import FlowLibConfig
from flowlib.model import FlowLibException

from tests.flowlib_test_utils import RESOURCES_DIR


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
        self.assertTrue(len(nipyapi.nifi.apis.FlowApi().get_controller_services_from_controller().controller_services) == 1)
        self.assertTrue(len(nipyapi.nifi.apis.FlowApi().get_reporting_tasks().reporting_tasks) == 1)

    def test_deploy_flow(self):
        with open(os.path.join(self.__class__.tmp_dir.name, 'dataflow', '.flowlib.yml'), 'r') as f:
            config = FlowLibConfig.new_from_file(f)
        config.nifi_endpoint = self.__class__.endpoint
        config.zookeeper_connection = '127.0.0.1:2181'
        config.flow_yaml = os.path.join(self.__class__.tmp_dir.name, 'dataflow', 'flow.yaml')
        flowlib.api.deploy_flow(config)
        self.assertIsInstance(nipyapi.canvas.get_process_group('pdf-processor-demo-flow'), ProcessGroupEntity)

    def test_redeploy_flow(self):
        with open(os.path.join(self.__class__.tmp_dir.name, 'dataflow', '.flowlib.yml'), 'r') as f:
            config = FlowLibConfig.new_from_file(f)
        config.nifi_endpoint = self.__class__.endpoint
        config.zookeeper_connection = '127.0.0.1:2181'
        config.flow_yaml = os.path.join(self.__class__.tmp_dir.name, 'dataflow', 'flow.yaml')

        listS3 = nipyapi.canvas.get_processor('list-s3')
        self.assertIsInstance(listS3, ProcessorEntity)
        state = {'asdf': 'This is state'}
        zk = ZookeeperClient(config.zookeeper_connection)
        zk.set_processor_state(listS3.id, state)

        config.force = True
        flowlib.api.deploy_flow(config)
        listS3 = nipyapi.canvas.get_processor('list-s3')
        self.assertIsInstance(listS3, ProcessorEntity)
        self.assertEqual(state, zk.get_processor_state(listS3.id))

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
    suite.addTest(ITestFlowLib('test_configure_flow_controller'))
    suite.addTest(ITestFlowLib('test_deploy_flow'))
    suite.addTest(ITestFlowLib('test_redeploy_flow'))
    # suite.addTest(ITestFlowLib('test_gen_flowlib_docs'))
    # suite.addTest(ITestFlowLib('test_list_components'))
    # suite.addTest(ITestFlowLib('test_describe_component'))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner(failfast=True)
    runner.run(suite())

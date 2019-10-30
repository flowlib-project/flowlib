# -*- coding: utf-8 -*-
import os
import tempfile
import unittest

import nipyapi.nifi.apis
from nipyapi.nifi import ProcessGroupEntity, ProcessorEntity

import flowlib.api
from flowlib.model import FlowLibException
from flowlib.model.config import FlowLibConfig
from flowlib.nifi.rest import wait_for_nifi_api
from flowlib.nifi.state import ZookeeperClient

from tests.integration import ITestBase


class ITestScaffoldDeploy(ITestBase):

    def runTest(self):
        self._test_configure_flow_controller()
        self._test_deploy_flow()
        self._test_redeploy_flow()

    def _test_configure_flow_controller(self):
        with open('.flowlib.yml', 'r') as f:
            config = FlowLibConfig.new_from_file(f)
        config.nifi_endpoint = self.nifi
        flowlib.api.configure_flow_controller(config)
        self.assertTrue(len(nipyapi.nifi.apis.FlowApi().get_controller_services_from_controller().controller_services) == 1)
        self.assertTrue(len(nipyapi.nifi.apis.FlowApi().get_reporting_tasks().reporting_tasks) == 1)

    def _test_deploy_flow(self):
        with open('.flowlib.yml', 'r') as f:
            config = FlowLibConfig.new_from_file(f)
        config.nifi_endpoint = self.nifi
        config.zookeeper_connection = self.zookeeper
        config.flow_yaml = 'flow.yaml'

        flowlib.api.deploy_flow(config)
        self.assertIsInstance(nipyapi.canvas.get_process_group('pdf-processor-demo-flow'), ProcessGroupEntity)

    def _test_redeploy_flow(self):
        with open('.flowlib.yml', 'r') as f:
            config = FlowLibConfig.new_from_file(f)
        config.nifi_endpoint = self.nifi
        config.zookeeper_connection = self.zookeeper
        config.flow_yaml = 'flow.yaml'

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

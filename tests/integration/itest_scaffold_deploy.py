# -*- coding: utf-8 -*-
import os
import tempfile
import unittest

import nipyapi.nifi.apis
from nipyapi.nifi import ProcessGroupEntity, ProcessorEntity

import flowlib.api
import flowlib.nifi.rest
from flowlib.exceptions import FlowLibException, FlowNotFoundException
from flowlib.model.config import FlowLibConfig
from flowlib.nifi.rest import wait_for_nifi_api
from flowlib.nifi.state import ZookeeperClient

from tests.integration import ITestBase


class ITestScaffoldDeploy(ITestBase):

    def tearDown(self):
        with open('.flowlib.yml', 'r') as f:
            config = FlowLibConfig.new_from_file(f)
        config.nifi_endpoint = self.nifi
        flowlib.nifi.rest._force_cleanup_reporting_tasks()
        try:
            flow_pg = flowlib.nifi.rest._find_flow_by_name('pdf-processor-demo-flow')
            flowlib.nifi.rest._remove_flow(flow_pg.id, force=True)
        except FlowNotFoundException:
            pass

    def runTest(self):
        initial_state = {'asdf': 'This is state'}
        deployment_state = {'test': 'This state will overwrite initial state'}

        self._test_configure_flow_controller()
        self._test_deploy_flow()
        self._test_redeploy_flow(initial_state)
        self._test_export_flow(initial_state)
        self._test_deploy_from_deployment_json(deployment_state)

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
        flow_pg = nipyapi.canvas.get_process_group('pdf-processor-demo-flow')
        ITestScaffoldDeploy.flow_pg_id = flow_pg.id
        self.assertIsInstance(flow_pg, ProcessGroupEntity)

    def _test_redeploy_flow(self, state):
        with open('.flowlib.yml', 'r') as f:
            config = FlowLibConfig.new_from_file(f)
        config.nifi_endpoint = self.nifi
        config.zookeeper_connection = self.zookeeper
        config.flow_yaml = 'flow.yaml'

        listS3 = nipyapi.canvas.get_processor('list-s3')
        self.assertIsInstance(listS3, ProcessorEntity)

        zk = ZookeeperClient(config.zookeeper_connection)
        zk.set_processor_state(listS3.id, state)

        config.force = True
        flowlib.api.deploy_flow(config)
        listS3 = nipyapi.canvas.get_processor('list-s3')
        self.assertIsInstance(listS3, ProcessorEntity)
        self.assertEqual(state, zk.get_processor_state(listS3.id))

    def _test_export_flow(self, state):
        with open('.flowlib.yml', 'r') as f:
            config = FlowLibConfig.new_from_file(f)
        config.nifi_endpoint = self.nifi
        config.export = 'pdf-processor-demo-flow'
        with open('deployment.json', 'w') as f:
            flowlib.api.export_flow(config, fp=f)

        with open('deployment.json', 'r') as f:
            flow, deployment = flowlib.api.new_flow_from_deployment(f)

        lists3 = deployment.get_component('s3-list-fetch-with-retry')
        self.assertEqual(list(lists3.stateful_processors.values())[0]['state'], state)

    def _test_deploy_from_deployment_json(self, state):
        with open('.flowlib.yml', 'r') as f:
            config = FlowLibConfig.new_from_file(f)
        config.nifi_endpoint = self.nifi
        config.zookeeper_connection = self.zookeeper

        with open('./deployment.json', 'r') as f:
            flow, deployment = flowlib.api.new_flow_from_deployment(f)

        # overwrite the deployment's state
        lists3 = deployment.get_component('s3-list-fetch-with-retry')
        list(lists3.stateful_processors.values())[0]['state'] = state

        self.assertRaisesRegex(FlowLibException, "^A flow with that name already exists, use the --force option to overwrite it$",
            flowlib.nifi.rest.deploy_flow, flow, config, deployment=deployment, force=False)

        # overwrite the currently deployed flow with the provided deployment
        flowlib.nifi.rest.deploy_flow(flow, config, deployment=deployment, force=True)

        # make sure that the newly deployed flow has the same state that was set explicitly in the deployment,
        # not the state that it had initially
        listS3 = nipyapi.canvas.get_processor('list-s3')
        zk = ZookeeperClient(config.zookeeper_connection)
        self.assertEqual(state, zk.get_processor_state(listS3.id))

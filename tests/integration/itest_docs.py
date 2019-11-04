# -*- coding: utf-8 -*-
import os
import tempfile
import unittest

import nipyapi

import flowlib.api
from flowlib.exceptions import FlowLibException
from flowlib.model.config import FlowLibConfig
from flowlib.nifi.rest import wait_for_nifi_api

from tests.integration import ITestBase


class ITestDocs(ITestBase):

    def runTest(self):
        self._test_gen_flowlib_docs()
        self._test_list_components()
        self._test_describe_component()

    def _test_gen_flowlib_docs(self):
        with open('.flowlib.yml', 'r') as f:
            config = FlowLibConfig.new_from_file(f)
        config.nifi_endpoint = self.nifi
        config.force = True
        flowlib.api.gen_flowlib_docs(config, config.docs_directory)

    def _test_list_components(self):
        with open('.flowlib.yml', 'r') as f:
            config = FlowLibConfig.new_from_file(f)
        list_processors = flowlib.api.list_components(config, 'processors')
        actual_results = nipyapi.nifi.apis.flow_api.FlowApi().get_processor_types().processor_types
        self.assertEqual(len(list_processors), len(actual_results))
        list_controllers = flowlib.api.list_components(config, 'controllers')
        actual_controllers = nipyapi.nifi.apis.flow_api.FlowApi().get_controller_service_types().controller_service_types
        self.assertEqual(len(list_controllers), len(actual_controllers))
        list_tasks = flowlib.api.list_components(config, 'reporting-tasks')
        actual_tasks = nipyapi.nifi.apis.flow_api.FlowApi().get_reporting_task_types().reporting_task_types
        self.assertEqual(len(list_tasks), len(actual_tasks))
        self.assertRaisesRegex(FlowLibException, '^Invalid component type.*', flowlib.api.list_components, config, 'invalid-type')

    def _test_describe_component(self):
        with open('.flowlib.yml', 'r') as f:
            config = FlowLibConfig.new_from_file(f)

        self.assertTrue(len(flowlib.api.describe_component(config, 'controller', 'org.apache.nifi.xml.XMLReader').keys()) > 0)
        self.assertTrue(len(flowlib.api.describe_component(config, 'reporting-task', 'org.apache.nifi.controller.MonitorMemory').keys()) > 0)
        self.assertTrue(len(flowlib.api.describe_component(config, 'processor', 'org.apache.nifi.processors.standard.DebugFlow').keys()) > 0)
        self.assertRaisesRegex(FlowLibException, '^Invalid component type.*', flowlib.api.describe_component, config, 'invalid-type', 'not.a.valid.package.id')
        self.assertRaisesRegex(FlowLibException, '^Component descriptor\s.*\sdoes not exist', flowlib.api.describe_component, config, 'processor', 'not.a.valid.package.id')

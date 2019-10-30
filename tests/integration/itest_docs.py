# -*- coding: utf-8 -*-
import os
import tempfile
import unittest

import flowlib.api
from flowlib.model import FlowLibException
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
        flowlib.api.list_components(config, 'processors')
        self.assertRaisesRegex(FlowLibException, '^Invalid component type.*', flowlib.api.list_components, config, 'invalid-type')

    def _test_describe_component(self):
        with open('.flowlib.yml', 'r') as f:
            config = FlowLibConfig.new_from_file(f)
        flowlib.api.describe_component(config, 'controller', 'org.apache.nifi.processors.aws.credentials.provider.service.AWSCredentialsProviderControllerService')
        self.assertRaisesRegex(FlowLibException, '^Invalid component type.*', flowlib.api.describe_component, config, 'invalid-type', 'not.a.valid.package.id')
        self.assertRaisesRegex(FlowLibException, '^Component descriptor\s.*\sdoes not exist', flowlib.api.describe_component, config, 'processor', 'not.a.valid.package.id')

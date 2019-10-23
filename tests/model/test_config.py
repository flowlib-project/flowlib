# -*- coding: utf-8 -*-
import os
import unittest

import flowlib
from flowlib.model.config import FlowLibConfig
from flowlib.cli import FlowLibCLI


class TestFlowLibConfig(unittest.TestCase):

    def test_defaults(self):
        config = FlowLibConfig()
        for k in FlowLibConfig.DEFAULTS:
            self.assertEqual(FlowLibConfig.DEFAULTS[k], getattr(config, k))

    def test_new_from_file(self):
        init_dir = os.path.abspath(os.path.join(os.path.dirname(flowlib.__file__), 'init'))
        with open(os.path.join(init_dir, '.flowlib.yml')) as f:
            config = FlowLibConfig.new_from_file(f)

        self.assertIsNotNone(config)
        self.assertEqual(config.nifi_endpoint, 'http://nifi-dev:8080')
        self.assertEqual(config.zookeeper_connection, 'nifi-dev:2181')
        self.assertEqual(config.component_dir, 'components')
        self.assertEqual(len(config.reporting_task_controllers), 1)
        self.assertEqual(len(config.reporting_tasks), 1)
        self.assertIsNone(config.flow_yaml)
        self.assertIsNone(config.scaffold)
        self.assertIsNone(config.generate_docs)
        self.assertIsNone(config.force)
        self.assertIsNone(config.export)
        self.assertIsNone(config.configure_flow_controller)
        self.assertIsNone(config.validate)

    def test_with_flag_overrides(self):
        config = FlowLibConfig()
        cli = FlowLibCLI(config)

        nifi_endpoint_override = 'https://whatever.com:8020'
        zookeeper_connection_override = 'fake-zookeeper.com:1111'
        component_dir_override = 'some_other_component_dir'
        documentation_dir_override = 'some_docs'

        args = cli.parser.parse_args([
            '--nifi-endpoint', nifi_endpoint_override,
            '--zookeeper-connection', zookeeper_connection_override,
            '--component-dir', component_dir_override,
            '--generate-docs', documentation_dir_override
        ])
        config.with_flag_overrides(args)
        self.assertEqual(config.nifi_endpoint, nifi_endpoint_override)
        self.assertEqual(config.zookeeper_connection, zookeeper_connection_override)
        self.assertEqual(config.component_dir, component_dir_override)
        self.assertEqual(config.generate_docs, documentation_dir_override)

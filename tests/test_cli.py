# -*- coding: utf-8 -*-
from argparse import ArgumentError, SUPPRESS
import unittest

from flowlib.cli import FlowLibCLI

from . import utils

class TestConf(unittest.TestCase):

    def test_defaults(self):
        cli = FlowLibCLI()
        self.assertIsNotNone(cli.args)
        self.assertIsNotNone(cli.config)

    def test_parser(self):
        cli = FlowLibCLI()

        # hack to suppress argparse stderr output
        cli.parser._print_message = lambda a,b: None

        nifi_endpoint = 'http://abc:8081'
        self.assertEqual(cli.parser.parse_args(['--nifi-endpoint', nifi_endpoint]).nifi_endpoint, nifi_endpoint)

        zookeeper_connection = 'zookeeper:2182'
        self.assertEqual(cli.parser.parse_args(['--zookeeper-connection', zookeeper_connection]).zookeeper_connection, zookeeper_connection)

        zookeeper_root_node = '/other'
        self.assertEqual(cli.parser.parse_args(['--zookeeper-root-node', zookeeper_root_node]).zookeeper_root_node, zookeeper_root_node)

        zookeeper_valid_acl = 'creator'
        zookeeper_invalid_acl = 'invalid'
        self.assertEqual(cli.parser.parse_args(['--zookeeper-acl', zookeeper_valid_acl]).zookeeper_acl, zookeeper_valid_acl)
        self.assertRaises(SystemExit, cli.parser.parse_args, ['--zookeeper-acl', zookeeper_invalid_acl])

        component_dir = 'abc'
        self.assertEqual(cli.parser.parse_args(['--component-dir', component_dir]).component_dir, component_dir)

        force = True
        self.assertEqual(cli.parser.parse_args(['--force']).force, force)

        validate = True
        self.assertEqual(cli.parser.parse_args(['--validate']).validate, validate)

        generate_docs = 'doc_dir'
        self.assertEqual(cli.parser.parse_args(['--generate-docs', generate_docs]).generate_docs, generate_docs)

        scaffold = 'test'
        self.assertEqual(cli.parser.parse_args(['--scaffold', scaffold]).scaffold, scaffold)

        # flow_yaml = 'dataflow.yaml'
        # r = "^.*No such file or directory:\s'{}'".format(flow_yaml)
        # self.assertRaisesRegex((SystemExit), r, cli.parser.parse_args, ['--flow-yaml', flow_yaml])

        export = 'flow-name'
        self.assertEqual(cli.parser.parse_args(['--export', export]).export, export)

        cfc = True
        self.assertEqual(cli.parser.parse_args(['--configure-flow-controller']).configure_flow_controller, cfc)

        valid_component_types = ['processor', 'controller', 'reporting-task']
        invalid_component_type = 'not-real'
        for component_type in valid_component_types:
            plural = component_type + 's'
            self.assertEqual(cli.parser.parse_args(['--list', plural]).list, plural)
        self.assertRaises(SystemExit, cli.parser.parse_args, ['--list', invalid_component_type])

        package_id = 'org.apache.nifi.TestProcessor'
        for component_type in valid_component_types:
            ns = cli.parser.parse_args(['--describe', component_type, package_id])
            self.assertEqual(ns.describe.component_type, component_type)
            self.assertEqual(ns.describe.package_id, package_id)
        # wrong number of args
        self.assertRaises(SystemExit, cli.parser.parse_args, ['--list', valid_component_types[0]])
        # invalid component_type
        self.assertRaises(SystemExit, cli.parser.parse_args, ['--list', invalid_component_type, package_id])

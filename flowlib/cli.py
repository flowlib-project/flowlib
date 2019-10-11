# -*- coding: utf-8 -*-
import argparse
from argparse import Namespace
import collections
import sys
import yaml

import flowlib
from flowlib.model.config import FlowLibConfig


class ValidateDescribe(argparse.Action):
    def __call__(self, parser, args, values, option_string=None):
        choices = ('processor', 'controller', 'reporting-task')
        component_type, package_id = values
        if component_type not in choices:
            parser.print_usage()
            print("{}: error: argument --describe: invalid choice: '{}' (choose from {})".format(parser.prog, choice,
                ', '.join("'{}'".format(c) for c in choices)))
            sys.exit(1)

        Describe = collections.namedtuple('Describe', 'component_type package_id')
        setattr(args, self.dest, Describe(component_type, package_id))


class FlowLibCLI:
    def __init__(self, file_config=None):
        """
        Parse provided CLI flags with optional FlowLibConfig defaults
        """
        self.parser = argparse.ArgumentParser(prog="flowlib",
            description="A python library and cli for deploying NiFi flows from YAML")

        self.parser.add_argument('--version',
            action = 'version',
            version = '%(prog)s {}'.format(flowlib.__version__)
        )

        self.parser.add_argument('--nifi-endpoint',
            type = str,
            help = 'A NiFi server endpoint'
        )

        self.parser.add_argument('--component-dir',
            type = str,
            help = 'A directory containing re-useable flowlib components'
        )

        self.parser.add_argument('--force',
            action = 'store_true',
            help = 'Force flowlib to overwrite an existing NiFi canvas'
        )

        # TODO: --flow-yaml should be required when validate is True
        self.parser.add_argument('--validate',
            action = 'store_true',
            help = 'Attempt to initialize the Flow from a flow.yaml by loading all of its components'
        )

        self.mx_group = self.parser.add_mutually_exclusive_group()
        self.mx_group.add_argument('--scaffold',
            type = str,
            help = 'Directory path to initialize with a new project scaffold'
        )
        self.mx_group.add_argument('--flow-yaml',
            type = argparse.FileType('r'),
            help = 'YAML file defining a NiFi flow to deploy'
        )
        self.mx_group.add_argument('--export',
            type = argparse.FileType('x'),
            help = 'Export the currently deployed NiFi flow as JSON. Prints to stdout if no filepath is specified'
        )
        self.mx_group.add_argument('--configure-flow-controller',
            action = 'store_true',
            help = 'Deploy reporting tasks and set global configs for the flow controller specified by .flowlib.yml to a running NiFi instance'
        )
        self.mx_group.add_argument('--list',
            type = str,
            choices = ['processors', 'controllers', 'reporting-tasks'],
            help = 'List the available package ids for the specified component type'
        )
        self.mx_group.add_argument('--describe',
            type = str,
            action = ValidateDescribe,
            metavar=('{processors,controllers,reporting-tasks}', 'PACKAGE_ID'),
            nargs = 2,
            help = 'Print the configurable properties for the specified component'
        )

        if not file_config:
            file_config = FlowLibConfig()
        self.args = self.parser.parse_args()
        self.config = file_config.with_flag_overrides(self.args)

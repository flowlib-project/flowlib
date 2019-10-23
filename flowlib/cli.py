# -*- coding: utf-8 -*-
import argparse
from argparse import Namespace
import collections
import sys
import yaml

import flowlib
from flowlib.model.config import FlowLibConfig


class ValidateDescribe(argparse.Action):
    """
    Validate --describe arguments
    """
    def __call__(self, parser, args, values, option_string=None):
        choices = ('processor', 'controller', 'reporting-task')
        component_type, package_id = values
        if component_type not in choices:
            parser.error("argument --describe: invalid choice: '{}' (choose from {})".format(component_type,
                ', '.join("'{}'".format(c) for c in choices)))
        Describe = collections.namedtuple('Describe', 'component_type package_id')
        setattr(args, self.dest, Describe(component_type, package_id))


class ValidateValidate(argparse.Action):
    """
    Validate --validate flag
    """
    def __call__(self, parser, args, values, option_string=None):
        if not args.flow_yaml:
            parser.error("argument --validate: --flow-yaml is required when --validate is true")
        setattr(args, self.dest, True)


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
            help = 'A NiFi server endpoint (proto://host:port)'
        )

        self.parser.add_argument('--zookeeper-connection',
            type = str,
            help = 'A Zookeeper client connection string (host:port)'
        )

        self.parser.add_argument('--zookeeper-root-node',
            type = str,
            help = 'The root node in zookeeper to use when storing state'
        )

        self.parser.add_argument('--zookeeper-acl',
            choices = ['open', 'creator'],
            help = 'The ACL to set for newly created zookeeper nodes if migrating state'
        )

        self.parser.add_argument('--component-dir',
            type = str,
            help = 'A directory containing re-useable flowlib components'
        )

        self.parser.add_argument('--force',
            action = 'store_true',
            help = 'Force flowlib to overwrite an existing flow (or flow controller when used with --configure-flow-controller)'
        )

        self.parser.add_argument('--validate',
            action = ValidateValidate,
            nargs=0,
            help = 'Attempt to initialize the Flow from a flow.yaml by loading all of its components'
        )

        self.mx_group = self.parser.add_mutually_exclusive_group()
        self.mx_group.add_argument('--scaffold',
            type = str,
            help = 'Directory path to initialize with a new project scaffold'
        )
        self.mx_group.add_argument('--generate-docs',
            type = str,
            help = 'Directory path to initialize with flowlib helper documentation'
        )
        self.mx_group.add_argument('--flow-yaml',
            type = str,
            help = 'YAML file defining a NiFi flow to deploy'
        )
        self.mx_group.add_argument('--export',
            type = str,
            help = 'Export the specified NiFi flow deployment and its components as JSON. Prints to stdout'
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
            metavar=('{processor,controller,reporting-task}', 'PACKAGE_ID'),
            nargs = 2,
            help = 'Print the configurable properties for the specified component'
        )

        if not file_config:
            file_config = FlowLibConfig()
        self.args = self.parser.parse_args()
        self.config = file_config.with_flag_overrides(self.args)

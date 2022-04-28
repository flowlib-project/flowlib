# -*- coding: utf-8 -*-
import argparse
from argparse import Namespace
import collections
import sys

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


class ValidateValidate(argparse._StoreTrueAction):
    """
    Validate --validate flag
    """
    def __call__(self, parser, args, values, option_string=None):
        setattr(args, self.dest, True)
        if not args.flow_yaml:
            parser.error("argument --validate: --flow-yaml is required when --validate is true")


class ValidateTransferTemplates(argparse.Action):
    def __call__(self, parser, args, values, option_string=None):
        setattr(args, self.dest, values)
        if not args.dest_nifi_endpoint:
            parser.error("argument --transfer-templates: --dest-nifi-endpoint is required")



class FlowLibCLI:
    def __init__(self, args=None, file_config=None):
        """
        Parse provided CLI flags with optional FlowLibConfig defaults
        """
        self.parser = argparse.ArgumentParser(prog="flowlib",
                                              description="A python library and cli for deploying NiFi flows from YAML")

        self.parser.add_argument('--version',
                                 action='version',
                                 version='%(prog)s {}'.format(flowlib.__version__)
                                 )

        self.parser.add_argument('--nifi-endpoint',
                                 type=str,
                                 help='A NiFi server endpoint (proto://host:port)'
                                 )

        self.parser.add_argument('--registry-endpoint',
                                 type=str,
                                 help='A NiFi registry server endpoint (proto://host:port)')

        self.parser.add_argument('--output-format',
                                 type=str,
                                 default="yaml",
                                 help='Output format (yaml/json)'
                                 )

        self.parser.add_argument('--zookeeper-connection',
                                 type=str,
                                 help='A Zookeeper client connection string (host:port)'
                                 )

        self.parser.add_argument('--zookeeper-root-node',
                                 type=str,
                                 help='The root node in zookeeper to use when storing state'
                                 )

        self.parser.add_argument('--zookeeper-acl',
                                 choices=['open', 'creator'],
                                 help='The ACL to set for newly created zookeeper nodes if migrating state'
                                 )

        self.parser.add_argument('--component-dir',
                                 type=str,
                                 help='A directory containing re-useable flowlib components'
                                 )

        self.parser.add_argument('--force',
                                 action='store_true',
                                 help='Force flowlib to overwrite an existing flow (or flow controller when used with --configure-flow-controller)'
                                 )

        self.parser.add_argument('--validate',
                                 action=ValidateValidate,
                                 help='Attempt to initialize the Flow from a flow.yaml by loading all of its components'
                                 )

        self.parser.add_argument('--container',
                                 type=str,
                                 help='The name of the docker container to run to execute NiFi Toolkit commands')

        self.parser.add_argument('--dest-registry-endpoint',
                                 type=str,
                                 help='The NiFi Registry endpoint (proto://host:port) to transfer a flow from the --registry-endpoint')

        self.parser.add_argument('--dest-nifi-endpoint',
                                 type=str,
                                 help='The NiFi Instance endpoint (proto://host:port) to transfer a template from the --nifi-endpoint')

        self.mx_group = self.parser.add_mutually_exclusive_group()

        self.mx_group.add_argument('--scaffold',
                                   type=str,
                                   help='Directory path to initialize with a new project scaffold'
                                   )
        self.mx_group.add_argument('--generate-docs',
                                   type=str,
                                   help='Directory path to initialize with flowlib helper documentation'
                                   )
        self.mx_group.add_argument('--flow-yaml',
                                   type=str,
                                   help='YAML file defining a NiFi flow to deploy'
                                   )
        self.mx_group.add_argument('--deployment-json',
                                   type=str,
                                   help='JSON file defining a NiFi flow to deploy, created by the --export option'
                                   )
        self.mx_group.add_argument('--export',
                                   type=str,
                                   help='Export the specified NiFi flow deployment and its components as JSON. Prints to stdout'
                                   )
        self.mx_group.add_argument('--registry-import',
                                   type=str,
                                   nargs=3,
                                   help='Import the specified NiFi registry output into a new flow within an existing bucket: <FILE> <BUCKET_NAME> <NEW_DESIRED_FLOWNAME>'
                                   )
        self.mx_group.add_argument('--registry-export',
                                   type=str,
                                   nargs=1,
                                   help='Export the specified NiFi flow and its components from the Nifi Registry by passing <all> or <bucket name>, will match names that start with this value'
                                   )
        self.mx_group.add_argument('--configure-flow-controller',
                                   action='store_true',
                                   help='Deploy reporting tasks and set global configs for the flow controller specified by .flowlib.yml to a running NiFi instance'
                                   )
        self.mx_group.add_argument('--list',
                                   type=str,
                                   choices=['processors', 'controllers', 'reporting-tasks'],
                                   help='List the available package ids for the specified component type'
                                   )
        self.mx_group.add_argument('--describe',
                                   type=str,
                                   action=ValidateDescribe,
                                   metavar=('{processor,controller,reporting-task}', 'PACKAGE_ID'),
                                   nargs=2,
                                   help='Print the configurable properties for the specified component'
                                   )
        self.mx_group.add_argument('--list-flows',
                                   type=str,
                                   nargs='?',
                                   const='all',
                                   help='Lists flows for all buckets in the registry or for a bucket name specified')

        self.mx_group.add_argument('--transfer-flows',
                                   type=str,
                                   nargs='?',
                                   const="{}",
                                   help="Deploy the provided flows or all flows in a bucket to another bucket within the same registry"
                                        "Note: The format is \"{\"source_bucket_name:dest_bucket_name\": [list of flow names or empty]}"
                                        "and it is assumed that the flow names are the same between buckets and registries")

        self.mx_group.add_argument('--change-versions',
                                   type=str,
                                   nargs='*',
                                   help="Change the version of the specified process groups to either the latest or specified version")

        self.mx_group.add_argument('--toggle-controller-services',
                                   type=str,
                                   nargs='*',
                                   help="Disable or enable the controller services for the specified process groups")

        self.mx_group.add_argument('--list-templates',
                                   action="store_true",
                                   help="Lists templates that are available")

        self.mx_group.add_argument('--create-templates',
                                   type=str,
                                   nargs='*',
                                   help="Create templates for each process group specified")

        self.mx_group.add_argument('--transfer-templates',
                                   type=str,
                                   nargs="*",
                                   action=ValidateTransferTemplates,
                                   help="Transfer tempaltes from one NiFi instance to another. WARNING: will overwrite templates with the same name")

        self.mx_group.add_argument('--deploy-templates',
                                   type=str,
                                   nargs='*',
                                   help="Instantiate templates in a specified process group")

        if not file_config:
            file_config = FlowLibConfig()
        self.args = self.parser.parse_args(args=args) if args else self.parser.parse_args()
        self.config = file_config.with_flag_overrides(self.args)

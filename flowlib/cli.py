# -*- coding: utf-8 -*-
import argparse
import sys

import flowlib

import logging

class FlowLibConfig:
    def __init__(self, **kwargs):
        self.flow_yaml = kwargs.get('flow_yaml')
        self.export_yaml = kwargs.get('export_yaml')
        self.component_dir = kwargs.get('component_dir')
        self.nifi_host = kwargs.get('nifi_host')
        self.nifi_port = kwargs.get('nifi_port')

    def __repr__(self):
        return str(self.__dict__)


class FlowLibCLI:
    def __init__(self):
        self.parser = argparse.ArgumentParser(prog="B23 FlowLib", description="A python library and cli for deploying NiFi flows from YAML")
        # TODO: Add --validate arg to check that the given flow can be loaded successfully
        # TODO: Add --dry-run arg
        self.parser.add_argument('--version',
            action='version',
            version='%(prog)s {} {}'.format(flowlib.__version__, flowlib.__git_version__)
        )
        self.parser.add_argument('--nifi-host',
            type = str,
            default = 'localhost',
            help = 'A NiFi server host'
        )
        self.parser.add_argument('--nifi-port',
            type = str,
            default = '8080',
            help = 'HTTP port for the NiFi API'
        )
        self.parser.add_argument('--component-dir',
            type = str,
            help = 'A directory containing re-useable flowlib components'
        )
        self.mx_group = self.parser.add_mutually_exclusive_group(required=True)
        self.mx_group.add_argument('--flow-yaml',
            type=argparse.FileType('r'),
            help='YAML file defining a NiFi flow to deploy'
        )
        self.mx_group.add_argument('--export-yaml',
            type=argparse.FileType('x'),
            help='Export the currently deployed NiFi flow as YAML. Prints to stdout if no filepath is specified'
        )
        self.config = FlowLibConfig(**vars(self.parser.parse_args()))

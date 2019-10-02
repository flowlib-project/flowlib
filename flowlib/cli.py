# -*- coding: utf-8 -*-
import argparse
import sys
import yaml

import flowlib


class FlowLibConfig:

    DEFAULT_CFG = '.flowlib.yml'
    DEFAULTS = {
        'component_dir': 'components',
        'nifi_endpoint': 'http://localhost:8080/nifi-api',
        'export': False,
        'force': False,
        'validate': False
    }

    def __init__(self, **kwargs):
        """
        :type flow_yaml: str
        :type scaffold: str
        :type force: bool
        :type export: bool
        :type validate: bool
        :type component_dir: str
        :type nifi_endpoint: str
        :type reporting_task_controllers: list(dict)
        :type reporting_tasks: list(dict)
        """
        # cli flags
        self.flow_yaml = kwargs.get('flow_yaml')
        self.scaffold = kwargs.get('scaffold')
        self.force = kwargs.get('force', FlowLibConfig.DEFAULTS['force'])
        self.export = kwargs.get('export', FlowLibConfig.DEFAULTS['export'])
        self.validate = kwargs.get('validate', FlowLibConfig.DEFAULTS['validate'])

        # cli flag overrides
        self.component_dir = kwargs.get('component_dir', FlowLibConfig.DEFAULTS['component_dir'])
        self.nifi_endpoint = kwargs.get('nifi_endpoint', FlowLibConfig.DEFAULTS['nifi_endpoint'])

        # file only configs
        self.reporting_task_controllers = kwargs.get('reporting_task_controllers', list())
        self.reporting_tasks = kwargs.get('reporting_tasks', list())

    @staticmethod
    def from_file(stream):
        """
        Construct a FlowLibConfig from a yaml config file
        :param stream: A python file like object
        """
        d = yaml.safe_load(stream) or dict()
        return FlowLibConfig(**d)

    @staticmethod
    def new_with_flag_overrides(file_config, flags):
        """
        Construct merge a config read from a yaml file with the provided cli flags
        :type file_config: FlowLibConfig
        :type flags: FlowLibConfig
        """
        if not file_config:
            file_config = FlowLibConfig(dict())

        config = vars(file_config)
        flags = vars(flags)

        # remove any unset keys
        for k in list(flags.keys()):
            if not flags[k]:
                del flags[k]

        config.update(flags)
        return FlowLibConfig(**config)


    def __repr__(self):
        return str(self.__dict__)


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

        self.parser.add_argument('--scaffold',
            type = str,
            help = 'Directory path to initialize with a new project scaffold'
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
        self.mx_group.add_argument('--flow-yaml',
            type = argparse.FileType('r'),
            help = 'YAML file defining a NiFi flow to deploy'
        )
        self.mx_group.add_argument('--export',
            type = argparse.FileType('x'),
            help = 'Export the currently deployed NiFi flow as JSON. Prints to stdout if no filepath is specified'
        )

        self.config = FlowLibConfig.new_with_flag_overrides(file_config, self.parser.parse_args())

# -*- coding: utf-8 -*-
import argparse
import sys
import yaml

import flowlib


class FlowLibConfig:

    DEFAULT_CFG = '.flowlib.yml'
    DEFAULTS = {
        'component_dir': 'components',
        'nifi_endpoint': 'http://localhost:8080/nifi-api'
    }

    def __init__(self, **kwargs):
        """
        :type flow_yaml: str
        :type scaffold: str
        :type force: bool
        :type export: bool
        :type validate: bool
        :type deploy_reporting_tasks: bool
        :type component_dir: str
        :type nifi_endpoint: str
        :type reporting_task_controllers: list(dict)
        :type reporting_tasks: list(dict)
        """
        # cli only flags
        self.flow_yaml = None
        self.scaffold = None
        self.force = None
        self.export = None
        self.deploy_reporting_tasks = None
        self.validate = None

        # file configs with flag overrides
        self.component_dir = kwargs.get('component_dir', FlowLibConfig.DEFAULTS['component_dir'])
        self.nifi_endpoint = kwargs.get('nifi_endpoint', FlowLibConfig.DEFAULTS['nifi_endpoint'])

        # file only configs
        self.reporting_task_controllers = kwargs.get('reporting_task_controllers', list())
        self.reporting_tasks = kwargs.get('reporting_tasks', list())

    def with_flag_overrides(self, flags):
        """
        Construct merge a config read from a yaml file with the provided cli flags
        :type flags: FlowLibConfig
        """
        flags = vars(flags)

        # remove any unset keys
        for k in list(flags.keys()):
            if not flags[k]:
                del flags[k]

        for k,v in flags.items():
            setattr(self, k, v)

        return self

    def __repr__(self):
        return str(self.__dict__)

    @staticmethod
    def new_from_file(stream):
        """
        Construct a FlowLibConfig from a yaml config file
        :param stream: A python file like object
        """
        d = yaml.safe_load(stream) or dict()
        return FlowLibConfig(**d)


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
        self.mx_group.add_argument('--deploy-reporting-tasks',
            action = 'store_true',
            help = 'Deploy reporting tasks specified in .flowlib.yml to a running NiFi instance'
        )

        if not file_config:
            file_config = FlowLibConfig()
        self.config = file_config.with_flag_overrides(self.parser.parse_args())

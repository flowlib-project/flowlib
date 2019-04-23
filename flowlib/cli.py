# -*- coding: utf-8 -*-
import argparse

class FlowLibConfig:
    def __init__(self, **kwargs):
        self.flow_yaml = kwargs.get('flow_yaml')
        self.nifi_address = kwargs.get('nifi_address')
        self.nifi_port = kwargs.get('nifi_port')

    def __repr__(self):
        return str(self.__dict__)


class FlowLibCLI:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="Deploy a NiFi flow from YAML")
        # TODO: Add --validate arg to check that the given flow can be loaded successfully
        self.parser.add_argument('--flow-yaml',
            nargs='?',
            type=argparse.FileType('r'),
            default='./flow.yaml',
            help='YAML file defining a NiFi flow')
        self.parser.add_argument('--nifi-address',
            type = str,
            default = 'localhost',
            help = 'Address of the NiFi API'
        )
        self.parser.add_argument('--nifi-port',
            type = str,
            default = '8080',
            help = 'HTTP port for the NiFi API'
        )
        self.config = FlowLibConfig(**vars(self.parser.parse_args()))

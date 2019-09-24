# -*- coding: utf-8 -*-

import yaml

from flowlib.model import FlowLibException
from flowlib.model.component import FlowComponent

# https://github.com/yaml/pyyaml/issues/103
class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True

class FlowDeployment:
    def __init__(self, name, raw_flow, flowlib_version):
        """
        :param name: The name of the flow being deployed
        :type name: str
        :param raw_flow: The raw yaml text of the flow.yaml
        :type raw_flow: io.TextIOWrapper
        :param flowlib_version: The version of the flowlib library used to perform the deployment
        :type flowlib_version: str
        """
        self.name = name
        self.raw_flow = raw_flow
        self.flowlib_version = flowlib_version
        self.root_group_id = None
        self.root_processors = dict()
        self._components = list()

    @property
    def checksum(self):
        return "not implemented"

    @property
    def components(self):
        return self._components

    def add(self, component):
        """
        :param component:
        :type component: DeployedComponent
        """
        c = list(filter(lambda x: x.name == component.name, self.components))
        if len(c) > 0:
            raise FlowLibException("A component named {} already exists".format(component.name))
        else:
            self.components.append(component)

    def get_component(self, name):
        """
        :param name: The name of the component
        :type name: str
        :returns: DeployedComponent
        """
        c = list(filter(lambda x: x.name == name, self.components))
        if len(c) <= 0:
            raise FlowLibException("Component named {} was not found".format(name))
        else:
            return c[0]

    def as_dict(self):
        self.raw_flow.seek(0)
        return {
            'name': self.name,
            'flowlib_version': self.flowlib_version,
            'raw_flow': yaml.safe_load(self.raw_flow),
            'root_group_id': self.root_group_id,
            'root_processors': self.root_processors,
            'components': list(map(lambda x: x.as_dict(), self.components))
        }

    def save(self, path='deployment.yaml'):
        f = open(path, 'w')
        yaml.dump_all([self.as_dict()], f, Dumper=NoAliasDumper)
        f.close()

    @staticmethod
    def from_yaml():
        pass

    @staticmethod
    def from_dict():
        pass

    def __repr__(self):
        return str(vars(self))


class DeployedComponent:
    def __init__(self, name, raw_component, instances=dict()):
        """
        :param name: A unique name for the component
        :type name: str
        :param raw_component: The yaml src of this loaded component
        :type raw_component: io.TextIOWrapper
        :param instances: The deployed instances of this component
        :type instances: dict({element_path: {"group_id": pg_id, "processor_id": proc_id}})
        """
        self.name = name
        self.raw_component = raw_component
        self.instances = instances

    def as_dict(self):
        self.raw_component.seek(0)
        return {
            'name': self.name,
            'raw_component': yaml.safe_load(self.raw_component),
            'instances': self.instances
        }

    def __repr__(self):
        return str(vars(self))

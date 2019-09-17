# -*- coding: utf-8 -*-

import yaml

from flowlib.model import FlowLibException
from flowlib.model.component import FlowComponent

class FlowDeployment:
    def __init__(self, name, raw, flowlib_version):
        """
        :param name: The name of the flow being deployed
        :type name: str
        :param raw: The raw yaml text of the flow.yaml
        :type raw: io.TextIOWrapper
        :param flowlib_version: The version of the flowlib library used to perform the deployment
        :type flowlib_version: str
        """
        self.name = name
        self.raw = raw
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
        self.raw.seek(0)
        return {
            'name': self.name,
            'flowlib_version': self.flowlib_version,
            'raw': self.raw.read(),
            'root_group_id': self.root_group_id,
            'root_processors': self.root_processors,
            'components': list(map(lambda x: x.as_dict(), self.components))
        }

    def save(self, path='deployment.yaml'):
        f = open(path, 'w')
        yaml.dump(self.as_dict(), f)
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
    def __init__(self, name, flow_component, instances=dict()):
        """
        :param name: A unique name for the component
        :type name: str
        :param flow_component: The yaml src of this loaded component
        :type flow_component: flowlib.model.component.FlowComponent
        :param instances: The deployed instances of this component
        :type instances: dict({pg_id: {proc_name: proc_id}})
        """
        self.name = name
        self.flow_component = flow_component
        self.instances = instances

    def as_dict(self):
        return {
            'name': self.name,
            'flow_component': self.flow_component.as_dict(),
            'instances': self.instances
        }

    def __repr__(self):
        return str(vars(self))

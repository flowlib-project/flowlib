# -*- coding: utf-8 -*-
import yaml
import json

from flowlib.model import FlowLibException
from flowlib.model.component import FlowComponent


class FlowDeployment:
    def __init__(self, name, raw_flow, flowlib_version, root_group_id=None, root_processors=dict()):
        """
        :param name: The name of the flow being deployed
        :type name: str
        :param raw_flow: The raw yaml text of the flow.yaml
        :type raw_flow: io.TextIOWrapper or dict
        :param flowlib_version: The version of the flowlib library used to perform the deployment
        :type flowlib_version: str
        :param root_group_id: The NiFi uuid of the flow's process group
        :type root_group_id: str
        :param root_processors: Any processors that are defined at the root of the flow
          (e.g. not contained in a component)
        :type root_processors: dict
        """
        self.name = name
        self.raw_flow = raw_flow
        self.flowlib_version = flowlib_version
        self.root_group_id = root_group_id
        self.root_processors = root_processors
        self._components = list()

    @property
    def components(self):
        return self._components

    def add_component(self, component):
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
        d = dict()
        d['name'] = self.name
        d['flowlib_version'] = self.flowlib_version
        if isinstance(self.raw_flow, dict):
            d['raw_flow'] = self.raw_flow
        else:
            self.raw_flow.seek(0)
            d['raw_flow'] = yaml.safe_load(self.raw_flow)
        d['root_group_id'] = self.root_group_id
        d['root_processors'] = self.root_processors
        d['components'] = list(map(lambda x: x.as_dict(), self.components))
        return d

    def save(self, buf):
        """
        :param buf: An output buffer
        :type buf: io.StringIO
        """
        buf.write(json.dumps(self.as_dict(), indent=2))

    @staticmethod
    def from_dict(d):
        components = d.pop('components')
        deployment = FlowDeployment(**d)
        for c in components:
            deployment.add_component(DeployedComponent(**c))
        return deployment

    def __repr__(self):
        return str(vars(self))


class DeployedComponent:
    def __init__(self, name, raw_component, stateful_processors=None):
        """
        :param name: A unique name for the component
        :type name: str
        :param raw_component: The yaml src of this loaded component
        :type raw_component: io.TextIOWrapper or dict
        :type stateful_processors: dict({element_path: {"group_id": pg_id, "processor_id": proc_id}})
        """
        self.name = name
        self.raw_component = raw_component
        self.stateful_processors = stateful_processors or dict()

    def as_dict(self):
        d = dict()
        d['name'] = self.name
        if isinstance(self.raw_component, dict):
            d['raw_component'] = self.raw_component
        else:
            self.raw_component.seek(0)
            d['raw_component'] = yaml.safe_load(self.raw_component)

        d['stateful_processors'] = self.stateful_processors
        return d

    def __repr__(self):
        return str(vars(self))

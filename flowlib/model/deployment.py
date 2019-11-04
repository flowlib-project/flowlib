# -*- coding: utf-8 -*-
import yaml
import json

from flowlib.exceptions import FlowLibException
from flowlib.model.flow import Flow
from flowlib.model.component import FlowComponent

class FlowDeployment:
    def __init__(self, flow, root_group_id=None, stateful_processors=None):
        """
        :param flow: The raw dictionary value of the Flow converted from yaml
        :type flow: dict
        :param root_group_id: The NiFi uuid of the flow's process group
        :type root_group_id: str
        :param stateful_processors: Any stateful processors that are defined at the root of the flow
          (e.g. not contained in a component)
        :type stateful_processors: dict({name: {"processor_id": proc_id}})
        """
        self.flow = flow
        self.components = list()
        self.root_group_id = root_group_id
        self.stateful_processors = stateful_processors or dict()

    def add_component(self, dc):
        """
        :param dc: The component that was loaded
        :type dc: DeployedComponent
        """
        c = list(filter(lambda x: x.component['name'] == dc.component['name'], self.components))
        if len(c) > 0:
            raise FlowLibException("A component named {} already exists".format(dc.component['name']))
        else:
            self.components.append(dc)

    def get_component(self, name):
        """
        :param name: The name of the component
        :type name: str
        :returns: The first DeployedComponent found or None
        """
        c = list(filter(lambda x: x.component['name'] == name, self.components))
        if len(c) <= 0:
            return None
        else:
            return c[0]

    def as_dict(self):
        return {
            'flow': self.flow,
            'components': [c.as_dict() for c in self.components],
            'root_group_id': self.root_group_id,
            'stateful_processors': self.stateful_processors
        }

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
    def __init__(self, component, stateful_processors=None):
        """
        :param component: The raw dictionary value of the Component converted from yaml
        :type component: dict
        :param stateful_processors: A dict of the stateful processors that were created in NiFi during the deployment
        :type stateful_processors: dict({element_path: {"group_id": pg_id, "processor_id": proc_id}})
        """
        self.component = component
        self.stateful_processors = stateful_processors or dict()

    def as_dict(self):
        return {
            'component': self.component,
            'stateful_processors': self.stateful_processors
        }

    def __repr__(self):
        return str(vars(self))

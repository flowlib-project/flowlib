# -*- coding: utf-8 -*-
import os
import yaml
import logging
import pprint

from nipyapi.nifi.models.processor_config_dto import ProcessorConfigDTO

class FlowLibException(Exception):
    pass


class Flow:
    PG_DELIMETER = '/'

    def __init__(self, name, version, controllers, canvas, flow_root_dir):
        """
        The root Flow class should be initialized from a flow.yaml with a canvas field
        This is what will be deployed to the root ProcessGroup of the target nifi instance
        :param name: The name of the Flow
        :type name: str
        :param version: The version of the Flow
        :type version: str
        :param controllers: The root controllers for the root canvas
        :type controllers: list(Controller)
        :param canvas: The root elements of the flow
        :type canvas: list(FlowElement)
        :param flow_root_dir: The path to the directory containing flow.yaml
        :type flow_root_dir: str
        :param loaded_components: A map of components (component_ref) loaded while initializing the flow, these are re-useable components
        :type loaded_components: dict(str:FlowComponent)
        :elements: A map of elements defining the flow logic, may be deeply nested if the FlowElement is a ProcessGroup itself.
          Initialized by calling flow.init()
        :type elements: dict(str:FlowElement)
        """
        self.name = name
        self.version = version
        self.controllers = controllers
        self.canvas = canvas
        self.flow_root_dir = flow_root_dir ## todo: Create a --flow-lib-dir flag for loading components
        self.loaded_components = dict()
        self.elements = dict()

    def __repr__(self):
        return pprint.pformat(self.__dict__)

    @classmethod
    def load_from_file(cls, f):
        """
        :param f: A fileobj which defines a root level DataFlow
        :type f: io.TextIOWrapper
        :raises: FlowLibException
        """
        raw = yaml.safe_load(f)
        name = raw.get('name')
        version = str(raw.get('version'))
        controllers = raw.get('controllers')
        canvas = raw.get('canvas')

        flow = cls(name, version, controllers, canvas, os.path.dirname(f.name))
        logging.info("Initializing root Flow: {}".format(flow.name))
        for elem_dict in flow.canvas:
            elem_dict['parent_path'] = flow.name
            el = FlowElement.load(elem_dict, flow)
            if flow.elements.get(el.name):
                raise FlowLibException("Root FlowElement is already defined: {}".format(el.name))
            else:
                flow.elements[el.name] = el

        return flow

    # TODO: Initialize a Flow.elements from a running nifi instance
    # @classmethod
    # def load_from_nifi(cls, url):
    #     nipyapi.config.nifi_config.host = url

    def get_parent_element(self, element):
        """
        A helper method for looking up parent elements from a breadcrumb path
        :param element: The element to retrieve the parent of
        :type element: FlowElement
        """
        target = self
        names = element.parent_path.split(Flow.PG_DELIMETER)
        for n in names[1:]:
            elements = target.elements
            target = elements.get(n)
        return target


class FlowComponent:
    def __init__(self, component_name, source_file, defaults=None, required_vars=None):
        """
        A reuseable component of a flow. Referenced by a ProcessGroup which is an instantiation of a FlowComponent
        """
        self.component_name = component_name
        self.source_file = source_file
        self.defaults = defaults
        self.required_vars = required_vars

    def __repr__(self):
        return pprint.pformat(self.__dict__)


class FlowElement:
    """
    This is either a ProcessGroup, Processor, InputPort, or OutputPort
    Do not call __init__ directly, use FlowElement.load()
    """
    def __init__(self, name, parent_path, _type, connections):
        self._id = None
        self._parent_id = None
        self.name = name
        self.parent_path = parent_path
        self._type = _type
        self.connections

    def __repr__(self):
        return pprint.pformat(self.__dict__)

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, _id):
        if self._id:
            raise FlowLibException("Attempted to change readonly attribute after initialization")
        self._id = _id

    @property
    def parent_id(self):
        return self._parent_id

    @parent_id.setter
    def parent_id(self, _id):
        if self._parent_id:
            raise FlowLibException("Attempted to change readonly attribute after initialization")
        self._parent_id = _id

    @property
    def type(self):
        return self._type

    @staticmethod
    def load(elem_dict, flow):
        if not isinstance(elem_dict, dict) or not elem_dict.get('type'):
            raise FlowLibException("FlowElement.load() requires a dict with a 'type' field, one of ['processor', 'process_group', 'input_port', 'output_port']")

        name = elem_dict.get('name')
        if not name or len(name) < 1:
            raise FlowLibException("Invalid element with parent path: {}. Element names may not be empty".format(elem_dict.get('parent_path')))
        if Flow.PG_DELIMETER in name:
            raise FlowLibException("Invalid element: '{}'. Element names may not contain '{}' characters".format(self.name, Flow.PG_DELIMETER))

        elem_dict['_type'] = elem_dict.pop('type')
        if elem_dict.get('_type') == 'process_group':
            return ProcessGroup(**elem_dict).load(flow)
        elif elem_dict.get('_type') == 'processor':
            return Processor(**elem_dict)
        elif elem_dict.get('_type') == 'input_port':
            return InputPort(**elem_dict)
        elif elem_dict.get('_type') == 'output_port':
            return OutputPort(**elem_dict)
        else:
            raise FlowLibException("Element 'type' field must be one of ['processor', 'process_group', 'input_port', 'output_port']")


class ProcessGroup(FlowElement):
    def __init__(self, name, parent_path, _type, component_ref, vars=None, connections=None):
        """
        :elements: A map of elements defining the flow logic, may be deeply nested if the FlowElement is a ProcessGroup itself.
          Initialized by calling FlowElement.load()
        :type elements: dict(str:FlowElement)
        """
        self._id = None
        self._parent_id = None
        self.name = name
        self.parent_path = parent_path
        self._type = _type
        self.component_ref = component_ref
        self.vars = vars
        self.connections = [Connection(**c) for c in connections] if connections else None
        self.elements = dict()

    def load(self, flow):
        logging.info("Loading ProcessGroup: {}".format(self.name))
        file_ref = os.path.join(flow.flow_root_dir, self.component_ref)
        with open(file_ref) as f:
            raw = yaml.safe_load(f)

        try:
            process_group = raw.pop('process_group')
        except KeyError as e:
            raise FlowLibException("FlowLib component does not contain a process_group field: {}".format(loaded_component.source_file))

        raw['source_file'] = file_ref
        loaded_component = FlowComponent(**raw)
        if not self.component_ref in flow.loaded_components:
            flow.loaded_components[self.component_ref] = loaded_component

        # Validate required variables are present
        if loaded_component.required_vars:
            for v in loaded_component.required_vars:
                if not v in self.vars:
                    raise FlowLibException("Missing Required Var. {} is undefined but is required by {}".format(v, loaded_component.file_ref))

        found_input = False
        found_output = False
        # Call FlowElement.load() on each element in the process_group
        for elem_dict in process_group:
            elem_dict['parent_path'] = "{}/{}".format(self.parent_path, self.name)
            el = FlowElement.load(elem_dict, flow)

            if isinstance(el, ProcessGroup):
                if el.component_ref == self.component_ref:
                    raise FlowLibException("Recursive component reference found in {}. A component cannot reference itself.".format(self.component_ref))

            if self.elements.get(el.name):
                raise FlowLibException("Found Duplicate Elements. FlowElement {} is already defined in: {}".format(el.name, ref))
            else:
                self.elements[el.name] = el

        return self


class Processor(FlowElement):
    def __init__(self, name, parent_path, _type, config, connections=None):
        self._id = None
        self._parent_id = None
        self.name = name
        self.parent_path = parent_path
        self._type = _type
        self.config = ProcessorConfig(config.pop('package_id'), **config)
        self.connections = [Connection(**c) for c in connections] if connections else None


class ProcessorConfig(ProcessorConfigDTO):
    def __init__(self, package_id, **kwargs):
        super().__init__(**kwargs)
        self.package_id = package_id

    def __repr__(self):
        return pprint.pformat(self.__dict__)


class InputPort(FlowElement):
    def __init__(self, name, parent_path, _type, connections=None):
        self._id = None
        self._parent_id = None
        self.name = name
        self.parent_path = parent_path
        self._type = _type
        self.connections = [Connection(**c) for c in connections] if connections else None


class OutputPort(FlowElement):
    def __init__(self, name, parent_path, _type, connections=None):
        self._id = None
        self._parent_id = None
        self.name = name
        self.parent_path = parent_path
        self._type = _type
        self.connections = [Connection(**c) for c in connections] if connections else None


class Connection:
    def __init__(self, name, from_port=None, to_port=None, relationships=None):
        self.name = name
        self.from_port = from_port
        self.to_port = to_port
        self.relationships = relationships

    def __repr__(self):
        return pprint.pformat(self.__dict__)


# class Controller:
#     def __init__(self, name, package_id, properties):
#         self.name = name
#         self.package_id = package_id
#         self.properties = properties

#     def __repr__(self):
#         return pprint.pformat(self.__dict__)

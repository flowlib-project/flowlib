import os
import yaml
import logging
import pprint

from nipyapi.nifi.models.processor_config_dto import ProcessorConfigDTO

class FlowLibException(Exception):
    pass


class Flow:
    PG_DELIMETER = '/'

    def __init__(self, flow_name, controllers, canvas, flow_root_dir):
        """
        The root Flow class should be initialized from a flow.yaml with a canvas field
        This is what will be deployed to the root ProcessGroup of the target nifi instance
        :param flow_name: The name of the Flow
        :type flow_name: str
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
        self.flow_name = flow_name
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
        """
        raw = yaml.safe_load(f)
        name = raw.get('flow_name')
        controllers = raw.get('controllers')
        canvas = raw.get('canvas')
        return cls(name, controllers, canvas, os.path.dirname(f.name))

    def init(self):
        """
        :raises: FlowLibException
        """
        logging.info("Initializing root Flow: {}".format(self.flow_name))
        for elem_dict in self.canvas:
            elem_dict['parent_path'] = self.flow_name
            el = FlowElement.load(elem_dict, self)
            if self.elements.get(el.name):
                raise FlowLibException("Root FlowElement is already defined: {}".format(el.name))
            else:
                self.elements[el.name] = el

        return self


class FlowComponent:
    def __init__(self, component_name, source_ref, accepts_inputs=True, accepts_outputs=True, defaults=None, required_vars=None):
        """
        A reuseable component of a flow. Referenced by a ProcessGroup which is an instantiation of a FlowComponent
        """
        self.component_name = component_name
        self.source_ref = source_ref
        self.accepts_inputs = accepts_inputs
        self.accepts_outputs = accepts_outputs
        self.defaults = defaults
        self.required_vars = required_vars

    def __repr__(self):
        return pprint.pformat(self.__dict__)


class FlowElement:
    """
    This is either a ProcessGroup, Processor, InputPort, or OutputPort
    Do not call __init__ directly, use FlowElement.load()
    """
    def __init__(self, name, parent_path, element_type):
        self.name = name
        self.parent_path = parent_path
        self.element_type = element_type

    def __repr__(self):
        return pprint.pformat(self.__dict__)

    @staticmethod
    def load(elem_dict, flow):
        if not isinstance(elem_dict, dict) or not elem_dict.get('element_type'):
            raise FlowLibException("FlowElement.load() requires a dict with a element_type field")

        name = elem_dict.get('name')
        if not name or len(name) < 1:
            raise FlowLibException("Invalid element with parent path: {}. Element names may not be empty".format(elem_dict.get('parent_path')))
        if Flow.PG_DELIMETER in name:
            raise FlowLibException("Invalid element: '{}'. Element names may not contain '{}' characters".format(self.name, Flow.PG_DELIMETER))

        if elem_dict.get('element_type') == 'ProcessGroup':
            return ProcessGroup(**elem_dict).load(flow)
        elif elem_dict.get('element_type') == 'Processor':
            return Processor(**elem_dict)
        elif elem_dict.get('element_type') == 'InputPort':
            return InputPort(**elem_dict)
        elif elem_dict.get('element_type') == 'OutputPort':
            return OutputPort(**elem_dict)
        else:
            raise FlowLibException("Only ProcessGroups, Processors, InputPorts, or OutputPorts are allowed")


class ProcessGroup(FlowElement):
    def __init__(self, name, parent_path, element_type, component_ref, vars=None, downstream=None):
        """
        :elements: A map of elements defining the flow logic, may be deeply nested if the FlowElement is a ProcessGroup itself.
          Initialized by calling FlowElement.load()
        :type elements: dict(str:FlowElement)
        """
        self.name = name
        self.parent_path = parent_path
        self.element_type = element_type
        self.component_ref = component_ref
        self.vars = vars
        self.downstream = [DownstreamConnection(**d) for d in downstream] if downstream else None
        self.elements = dict()

    def load(self, flow):
        logging.info("Loading ProcessGroup: {}".format(self.name))
        ref = os.path.join(flow.flow_root_dir, self.component_ref)
        with open(ref) as f:
            raw = yaml.safe_load(f)

        try:
            process_group = raw.pop('process_group')
        except KeyError as e:
            raise FlowLibException("FlowLib component does not contain a process_group field: {}".format(loaded_component.source_ref))

        # TODO: Check that a component does not reference itself recursively
        raw['source_ref'] = ref
        loaded_component = FlowComponent(**raw)
        if not loaded_component.source_ref in flow.loaded_components:
            flow.loaded_components[loaded_component.source_ref] = loaded_component

        # Validate required variables are present
        if loaded_component.required_vars:
            for v in loaded_component.required_vars:
                if not v in self.vars:
                    raise FlowLibException("Missing Required Var. {} is undefined but is required by {}".format(v, loaded_component.source_ref))

        for elem_dict in process_group:
            elem_dict['parent_path'] = "{}/{}".format(self.parent_path, self.name)
            el = FlowElement.load(elem_dict, flow)

            if self.elements.get(el.name):
                raise FlowLibException("Found Duplicate Elements. FlowElement {} is already defined in: {}".format(el.name, ref))
            else:
                self.elements[el.name] = el

        return self


class Processor(FlowElement):
    def __init__(self, name, parent_path, element_type, config, downstream=None):
        self.name = name
        self.parent_path = parent_path
        self.element_type = element_type
        self.config = ProcessorConfig(config.pop('package_id'), **config)
        self.downstream = [DownstreamConnection(**d) for d in downstream] if downstream else None


class ProcessorConfig(ProcessorConfigDTO):
    def __init__(self, package_id, **kwargs):
        super().__init__(**kwargs)
        self.package_id = package_id

    def __repr__(self):
        return pprint.pformat(self.__dict__)


class InputPort(FlowElement):
    def __init__(self, name, parent_path, element_type, downstream=None):
        self.name = name
        self.parent_path = parent_path
        self.element_type = element_type
        self.downstream = [DownstreamConnection(**d) for d in downstream] if downstream else None


class OutputPort(FlowElement):
    pass


class DownstreamConnection:
    def __init__(self, name, relationships):
        self.name = name
        self.relationships = relationships

    def __repr__(self):
        return pprint.pformat(self.__dict__)


class Controller:
    def __init__(self, name, package_id, properties):
        self.name = name
        self.package_id = package_id
        self.properties = properties

    def __repr__(self):
        return pprint.pformat(self.__dict__)

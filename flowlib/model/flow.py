# -*- coding: utf-8 -*-
from abc import ABC

from flowlib.logger import log
from flowlib.exceptions import FlowLibException, FlowValidationException

from nipyapi.nifi.models.processor_config_dto import ProcessorConfigDTO
from nipyapi.nifi.models.controller_service_dto import ControllerServiceDTO
from nipyapi.nifi.models.reporting_task_dto import ReportingTaskDTO
from nipyapi.nifi.models.remote_process_group_dto import RemoteProcessGroupDTO


class Flow:

    PG_NAME_DELIMETER = '/'

    def __init__(self, raw, name=None, canvas=None, flowlib_version=None, version=None, controller_services=None, comments=None, global_vars=None, components=None):
        """
        :param raw: The raw dictionary value of the Flow converted from yaml
        :type raw: dict
        :param name: The name of the Flow
        :type name: str
        :param canvas: The root elements of the flow
        :type canvas: list(dict)
        :param flowlib_version: The version of the flowlib module
        :type flowlib_version: str
        :param version: The version of the Flow
        :type version: str
        :param controller_services: The controller_services to create for the Flow
        :type controller_services: list(dict)
        :param comments: Flow comments
        :type comments: str
        :param global_vars: Global variables for jinja var injection in NiFi component properties
        :type global_vars: dict(str:Any)
        :param _loaded_components: A map of components (component_path) loaded while initializing the flow, these are re-useable components
        :type _loaded_components: dict(str:FlowComponent)
        :attr _elements: A map of elements defining the flow logic, may be deeply nested if the FlowElement is a ProcessGroup itself.
          Initialized by calling flow.initialize()
        :type _elements: dict(str:FlowElement)
        :attr _controllers: Whether this flow has been been initialized (elements and components loaded)
        :type _controllers: list(ControllerService)
        :attr _is_initialized: Whether this flow has been been initialized (elements and components loaded)
        :type _is_initialized: bool
        :attr _is_valid: Whether this flow has been been validated (elements and connections)
        :type _is_valid: bool
        """
        self.raw = raw
        self.name = name
        self.canvas = canvas
        self.flowlib_version = flowlib_version
        self.version = version
        self.comments = comments
        self.controller_services = controller_services or list()
        self.global_vars = global_vars or dict()
        self._is_initialized = False
        self._is_valid = False
        self._controllers = None
        self._loaded_components = dict()
        self._elements = dict()
        self._id = None

    @property
    def components(self):
        return self._loaded_components

    @components.setter
    def components(self, components):
        if self._loaded_components:
            raise FlowLibException("Attempted to change readonly attribute after initialization")
        self._loaded_components = components

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, _id):
        if self._id:
            raise FlowLibException("Attempted to change readonly attribute after initialization")
        self._id = _id


    def initialize(self, component_dir=None, with_components=None):
        if self._is_initialized == False:
            from flowlib.parser import init_flow
            init_flow(self, component_dir=component_dir, with_components=with_components)
            self._is_initialized = True
        else:
            log.warn("Flow has already been initialized. Will not re-initialize")


    def validate(self):
        if not self._is_initialized:
            raise FlowValidationException("Cannot validate an uninitialized flow. Call flow.initialize() first")

        if self._is_valid == False:
            from flowlib.validator import check_connections
            check_connections(self, self._elements)
            self._is_valid = True
        else:
            log.warn("Flow has already been validated. Will not re-validate")


    def find_component_by_path(self, path):
        """
        A helper method for looking up a component by its relative path in component_dir
        :param path: The relative path of the component in component_dir
        :type name: str
        """
        if self.components:
            filtered = list(filter(lambda x: x.source_file == path, self.components.values()))
            if len(filtered) > 1:
                raise FlowLibException("Found multiple loaded components with source_file {}".format(path))
            if len(filtered) == 1:
                return filtered[0]
        return None

    def find_controller_by_name(self, name):
        """
        A helper method for looking up a controller by name
        :param name: The name of the controller
        :type name: str
        """
        if self._controllers:
            filtered = list(filter(lambda c: c.name == name, self._controllers))
            if len(filtered) > 1:
                raise FlowLibException("Found multiple controllers named {}".format(name))
            if len(filtered) == 1:
                return filtered[0]
        return None

    def get_parent_element(self, element):
        """
        A helper method for looking up parent elements from a breadcrumb path
        :param element: The element to retrieve the parent of
        :type element: FlowElement
        """
        if isinstance(element, FlowElement):
            target = self
            names = element.parent_path.split(Flow.PG_NAME_DELIMETER)
            for n in names[1:]:
                target = target._elements.get(n)
            return target
        elif isinstance(element, Flow):
            return None
        else:
            raise FlowLibException("Flow.get_parent_element() requires an element which is a subclass of FlowElement")


    def __repr__(self):
        return str(vars(self))

class FlowElement(ABC):
    """
    An abstract parent class for things that might appear on the flow's canvas
    This is either a ProcessGroup, Processor, InputPort, or OutputPort
    :param _id: The NiFi uuid of the element
    :type _id: str
    :param _parent_id: The NiFi uuid of the process group which contains this element
    :type _parent_id: str
    :param _parent_path: The path of the parent process group on the canvas (e.g flow-name/group-name)
    :type _parent_path: str
    :param _src_component_name: The name of the component which contains this Element
    :type _src_component_name: str
    :param _type: one of ['processor', 'process_group', 'input_port', 'output_port']
    :type _type: str
    :param name: A unique name for the Element
    :type name: str
    :param connections: A list of Connections defining this Elements connections to other Elements
    :type connections: list(Connection)
    """
    def __init__(self, **kwargs):
        self._id = kwargs.get('_id')
        self._parent_id = kwargs.get('_parent_id')
        self._parent_path = kwargs.get('_parent_path')
        self._src_component_name = kwargs.get('_src_component_name')
        self._type = kwargs.get('_type')
        self.name = kwargs.get('name')
        self.connections = [Connection(**c) for c in kwargs.get('connections')] if kwargs.get('connections') else []

    @staticmethod
    def from_dict(elem_dict):
        if not isinstance(elem_dict, dict) or not elem_dict.get('type'):
            raise FlowLibException("FlowElement.from_dict() requires a dict with a 'type' field, one of ['processor', 'process_group', 'input_port', 'output_port']")

        name = elem_dict.get('name')
        if not name or len(name) < 1:
            raise FlowLibException("Element names may not be empty. Found invalid element with parent path: {}".format(elem_dict.get('parent_path')))
        if Flow.PG_NAME_DELIMETER in name:
            raise FlowLibException("Invalid element: '{}'. Element names may not contain '{}' characters".format(name, Flow.PG_NAME_DELIMETER))

        elem_dict['_type'] = elem_dict.pop('type')
        if elem_dict['_type'] == 'process_group':
            if elem_dict.get('vars'):
                elem_dict['_vars'] = elem_dict.pop('vars')
            return ProcessGroup(**elem_dict)
        elif elem_dict['_type'] == 'remote_process_group':
            return RemoteProcessGroup(**elem_dict)
        elif elem_dict['_type'] == 'processor':
            return Processor(**elem_dict)
        elif elem_dict['_type'] == 'input_port':
            return InputPort(**elem_dict)
        elif elem_dict['_type'] == 'output_port':
            return OutputPort(**elem_dict)
        else:
            raise FlowLibException("Element 'type' field must be one of ['processor', 'process_group', 'remote_process_group', 'input_port', 'output_port']")

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
    def parent_path(self):
        return self._parent_path

    @parent_path.setter
    def parent_path(self, path):
        if self._parent_path:
            raise FlowLibException("Attempted to change readonly attribute after initialization")
        self._parent_path = path

    @property
    def type(self):
        return self._type

    def __repr__(self):
        return str(vars(self))


class RemoteProcessGroup(FlowElement):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config = RemoteProcessGroupConfig(**kwargs['config'])


class RemoteProcessGroupConfig(RemoteProcessGroupDTO):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ProcessGroup(FlowElement):
    def __init__(self, **kwargs):
        """
        Represents the instantiation of a flowlib Component
        :param component_path: The relative file path of the source component in component_dir
        :type component_path: str
        :param controllers: Maps a required_controller to the controller implementation to use
        :type controllers: dict(str:str)
        :param vars: The variables to inject into the component instance
        :type vars: dict(str:Any)
        :attr _elements: A map of elements defining the flow logic, may be deeply nested if the FlowElement is a ProcessGroup itself.
          Initialized by calling FlowElement.load()
        :type _elements: dict(str:FlowElement)
        """
        super().__init__(**kwargs)
        self.component_path = kwargs.get('component_path')
        self.controllers = kwargs.get('controllers', dict())
        self.vars = kwargs.get('_vars', dict())
        self._elements = dict()


class Processor(FlowElement):
    def __init__(self, **kwargs):
        """
        Represents a processor element within a process group
        :param config: The configuration of the processor to instantiate in NiFi
        :type config: ProcessorConfig
        """
        super().__init__(**kwargs)
        if not kwargs.get('config', {}).get('package_id'):
            raise FlowLibException("Invalid processor definition. config.package_id is a required field")
        if not 'properties' in kwargs.get('config', {}):
            kwargs['config']['properties'] = dict()
        self.config = ProcessorConfig(kwargs['config'].pop('package_id'), **kwargs['config'])


class ProcessorConfig(ProcessorConfigDTO):
    def __init__(self, package_id, **kwargs):
        super().__init__(**kwargs)
        self.package_id = package_id

    def __repr__(self):
        return str(vars(self))


class InputPort(FlowElement):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class OutputPort(FlowElement):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Connection:
    def __init__(self, name, from_port=None, to_port=None, relationships=None, back_pressure_object_threshold=None, back_pressure_data_size_threshold=None, flow_file_expiration=None, load_balance_strategy=None, prioritizers=None):
        self.name = name
        self.from_port = from_port
        self.to_port = to_port
        self.relationships = relationships
        self.back_pressure_object_threshold = back_pressure_object_threshold
        self.back_pressure_data_size_threshold = back_pressure_data_size_threshold
        self.flow_file_expiration = flow_file_expiration
        self.load_balance_strategy = load_balance_strategy
        self.prioritizers = prioritizers

    def __repr__(self):
        return str(vars(self))


class ControllerService:
    def __init__(self, name, config):
        self._id = None
        self._parent_id = None
        self.name = name

        if not 'properties' in config:
            config['properties'] = dict()
        self.config = ControllerServiceConfig(config.pop('package_id'), **config)

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

    def __repr__(self):
        return str(vars(self))


class ControllerServiceConfig(ControllerServiceDTO):
    def __init__(self, package_id, **kwargs):
        super().__init__(**kwargs)
        self.package_id = package_id

    def __repr__(self):
        return str(vars(self))


class ReportingTask:
    def __init__(self, name, config):
        self._id = None
        self.name = name

        if not 'properties' in config:
            config['properties'] = dict()
        self.config = ReportingTaskConfig(config.pop('package_id'), **config)

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, _id):
        if self._id:
            raise FlowLibException("Attempted to change readonly attribute after initialization")
        self._id = _id

    def __repr__(self):
        return str(vars(self))


class ReportingTaskConfig(ReportingTaskDTO):
    def __init__(self, package_id, **kwargs):
        super().__init__(**kwargs)
        self.package_id = package_id

    def __repr__(self):
        return str(vars(self))

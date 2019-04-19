import copy
import logging
import re
import sys
import yaml

import nipyapi
from nipyapi import canvas
from nipyapi.nifi import models
from nipyapi.nifi import apis

from model import (FlowLibException, Flow, FlowComponent, FlowElement,
    ProcessGroup, Processor, InputPort, OutputPort)

# Some constants for canvas dimensions
TOP_LEVEL_PG_LOCATION = (300, 100)
VAR_WRAPPER = "$({})"

# TODO: Add a --dry-run command flag so that we can validate flows completely before
#   attempting to deploy to a running NiFi instance

def validate_flow(config):
    try:
        flow = Flow.load_from_file(config.flow_yaml).init()
        replace_flow_element_vars_recursive(flow.elements, flow.loaded_components)
        # validate_connections_recursive(flow.elements, flow.loaded_components)
    except FlowLibException as e:
        logging.error(e)
        sys.exit(1)


def deploy_flow_yaml(config):
    """
    :param config: A FlowLibConfig
    :type config: FlowGenConfig
    """
    logging.info("Deploying NiFi flow from YAML with config:")
    logging.info(config)

    nifi_url = "http://{}:{}/nifi-api".format(config.nifi_address, config.nifi_port)
    nipyapi.config.nifi_config.host = nifi_url
    root_id = nipyapi.canvas.get_root_pg_id()

    try:
        flow = Flow.load_from_file(config.flow_yaml).init()
        logging.info("Deploying {} to NiFi root canvas ID: {}".format(flow.flow_name, root_id))

        # TODO: Check deployed flow to see if a flow already exists or require --force, if not
        # then check if root process group is the same as the one being deployed,
        # should we set the version in the pg name or comments?
        root = nipyapi.canvas.get_process_group(root_id, identifier_type='id')
        root.component.name = flow.flow_name

        # TODO: Stop all source processors and wait for queues to drain completely.
        # Then stop all remaining processors and remove all connections

        # TODO: It is probably more reliable to delete all processors and connections and re-deploy
        # to a blank canvas. This will involve reading the state and setting the state directly in zookeeper
        # for the newly deployed processors

        # Set root pg name
        nipyapi.nifi.apis.ProcessGroupsApi().update_process_group(root_id, root)

        # create_controllers(flow)
        replace_flow_element_vars_recursive(flow.elements, flow.loaded_components)
        create_canvas_elements_recursive(flow.elements, root)
        create_connections_recursive(flow, flow.elements, flow.loaded_components)

    except FlowLibException as e:
        logging.error(e)
        sys.exit(1)


def _replace_vars(process_group, source_component):
    """
    Replace vars for all Processor elements inside a given ProcessGroup

    Note: We already valdated that required vars were present during flow.init()
      so don't worry about it here

    :param process_group: The processorGroup processors that need vars evaluated
    :type process_group: model.ProcessGroup
    :param component: The source component that the processGroup was created from
    :type component: model.FlowComponent
    """
    # Create a dict of vars to replace
    replacements = copy.deepcopy(source_component.defaults) or dict()
    if process_group.vars:
        for key,val in process_group.vars.items():
            replacements[key] = val

    # Format each var name with the expected VAR_WRAPPER
    # so that we can do a lookup when we find a pattern match
    wrapped_vars = dict()
    for k,v in replacements.items():
        wrapped_vars[VAR_WRAPPER.format(k)] = v

    esc_keys = [re.escape(key) for key in wrapped_vars.keys()]
    pattern = re.compile(r'(' + '|'.join(esc_keys) + r')')

    # Apply var replacements for each value of processor.config.properties
    for el in process_group.elements.values():
        if isinstance(el, Processor):
            for k,v in el.config.properties.items():
                el.config.properties[k] = pattern.sub(lambda x: wrapped_vars[x.group()], v)


def replace_flow_element_vars_recursive(elements, loaded_components):
    """
    Recusively apply the variable evaluation to each element in the flow
    :param elements: The elements to deploy
    :type elements: list(model.FlowElement)
    :param loaded_components: The components that were imported during flow.init()
    :type loaded_components: map(str:model.FlowComponent)
    """
    for el in elements.values():
        if isinstance(el, ProcessGroup):
            source_component = loaded_components[el.component_ref]
            _replace_vars(el, source_component)
            replace_flow_element_vars_recursive(el.elements, loaded_components)


def create_canvas_elements_recursive(elements, parent_pg):
    """
    Recursively creates the actual NiFi elements (process_groups, processors, inputs, outputs) on the canvas
    :param elements: The elements to deploy
    :type elements: list(model.FlowElement)
    :param parent_pg: The process group in which to create the processors
    :type parent_pg: nipyapi.nifi.models.process_group_entity.ProcessGroupEntity
    """
    for el in elements.values():
        if isinstance(el, ProcessGroup):
            pg = create_process_group(el, parent_pg)
            create_canvas_elements_recursive(el.elements, pg)
        elif isinstance(el, Processor):
            create_processor(el, parent_pg)
        elif isinstance(el, InputPort):
            create_input_port(el, parent_pg)
        elif isinstance(el, OutputPort):
            create_output_port(el, parent_pg)
        else:
            raise FlowLibException("Unsupported Element Type: {}".format(el.element_type))


def create_connections_recursive(flow, elements, loaded_components, source_component=None, parent_element=None):
    """
    Recursively creates the connections between elements defined in the Flow
    :param elements: a list of FlowElements to connect together
    :type elements: list(FlowElement)
    :param loaded_components: The components that were imported during flow.init()
    :type loaded_components: map(str:model.FlowComponent)
    :param parent_element: The parent elements of the current ProcessGroup or None if this is the root flow
    :type parent_element: model.ProcessGroup or None
    """
    for el in elements.values():
        if isinstance(el, ProcessGroup):
            source_component = loaded_components[el.component_ref]
            create_connections_recursive(flow, el.elements, loaded_components, source_component, el)
        elif el.element_type in ['Processor', 'InputPort', 'OutputPort']:
            create_downstream_connections(flow, el, elements, source_component, parent_element)
        else:
            raise FlowLibException("Unsupported Element Type: {}".format(el.element_type))


def create_process_group(element, parent_pg):
    """
    Create a Process Group on the NiFi canvas
    :param element: The Process Group to deploy
    :type element: model.ProcessGroup
    :param parent_pg: The process group in which to create the new process group
    :type parent_pg: nipyapi.nifi.models.process_group_entity.ProcessGroupEntity
    """
    # TODO: If we assert that the canvas is clean then we do not need to check if the
    # canvas elements already exist when creating processors, pgs, input/output ports
    name = "{}/{}".format(element.name, parent_pg.id)
    logging.info("Create or update ProcessGroup: {}".format(name))
    pg = nipyapi.canvas.get_process_group(name)
    if pg:
        logging.error("Found existing ProcessGroup: {}".format(name))
        raise FlowLibException("Re-deploying a flow is not yet supported")
    else:
        logging.debug("Creating ProcessGroup: {} with parent: {}".format(name, element.parent_path))
        pg = nipyapi.canvas.create_process_group(parent_pg, name, TOP_LEVEL_PG_LOCATION)

    element.id = pg.id
    element.parent_id = parent_pg.id
    return pg


def create_processor(element, parent_pg):
    """
    Create a Processor on the NiFi canvas
    :param element: The Processor to deploy
    :type element: model.Processor
    :param parent_pg: The process group in which to create the new processor
    :type parent_pg: nipyapi.nifi.models.process_group_entity.ProcessGroupEntity
    """
    name = "{}/{}".format(element.name, parent_pg.id)
    logging.info("Create or update Processor: {}".format(name))
    p = nipyapi.canvas.get_processor(name)
    if p:
        logging.error("Found existing Processor: {}".format(name))
        raise FlowLibException("Re-deploying a flow is not yet supported")
    else:
        logging.debug("Creating Processor: {} with parent: {}".format(name, element.parent_path))
        tpe = models.DocumentedTypeDTO(type=element.config.package_id)
        p = canvas.create_processor(parent_pg, tpe, TOP_LEVEL_PG_LOCATION, name, element.config)

    element.id = p.id
    element.parent_id = parent_pg.id
    return p


def create_input_port(element, parent_pg):
    """
    Create an Input Port on the NiFi canvas
    :param element: The InputPort to deploy
    :type element: model.InputPort
    :param parent_pg: The process group in which to create the new processor
    :type parent_pg: nipyapi.nifi.models.process_group_entity.ProcessGroupEntity
    """
    name = "{}/{}".format(element.name, parent_pg.id)
    logging.info("Create or update InputPort: {}".format(name))
    filtered_ips = [ip for ip in nipyapi.canvas.list_all_input_ports() if name in ip.component.name]
    ip = None
    if len(filtered_ips) > 0:
        ip = filtered_ips[0]
    if ip:
        logging.error("Found existing InputPort: {}".format(name))
        raise FlowLibException("Re-deploying a flow is not yet supported")
    else:
        logging.debug("Creating InputPort: {} with parent: {}".format(name, element.parent_path))
        ip = canvas.create_port(parent_pg.id, 'INPUT_PORT', name, 'STOPPED')

    element.id = ip.id
    element.parent_id = parent_pg.id
    return ip


def create_output_port(element, parent_pg):
    """
    Create an Output Port on the NiFi canvas
    :param element: The Output Port to deploy
    :type element: model.OutputPort
    :param parent_pg: The process group in which to create the new processor
    :type parent_pg: nipyapi.nifi.models.process_group_entity.ProcessGroupEntity
    """
    name = "{}/{}".format(element.name, parent_pg.id)
    logging.info("Create or update OutputPort: {}".format(name))
    filtered_ops = [op for op in nipyapi.canvas.list_all_output_ports() if name in op.component.name]
    op = None
    if len(filtered_ops) > 0:
        op = filtered_ops[0]
    if op:
        logging.error("Found existing OutputPort: {}".format(name))
        raise FlowLibException("Re-deploying a flow is not yet supported")
    else:
        logging.debug("Creating OutputPort: {} with parent: {}".format(name, element.parent_path))
        op = canvas.create_port(parent_pg.id, 'OUTPUT_PORT', name, 'STOPPED')

    element.id = op.id
    element.parent_id = parent_pg.id
    return op


def create_downstream_connections(flow, element, all_elements, source_component, parent=None):
    """
    Create the downstream connections for the element on the NiFi canvas
    :param element: The source FlowElement to connect to its downstreams
    :type element: FlowElement
    :param source_component: The source component of the current element
    :type source_component: FlowComponent
    :param parent: The parent element if it exists
    :type parent: FlowElement
    """
    logging.info('Creating downstream connections for element: {}/{}'.format(element.parent_path, element.name))
    # Validate no inputs or outputs on the root canvas
    if not source_component and (isinstance(element, InputPort) or isinstance(element, OutputPort)):
        raise FlowLibException("Input and Output ports may only be contained inside a component (ProcessGroup)")
    # Validate that a parent element was provided if connecting an outputPort to a downstream InputPort of another PG
    if isinstance(element, OutputPort) and not parent:
        raise FlowLibException("The parent element is required in order to create an OutputPort")

    # Get the source element NiFi entity by id
    #   - For ProcessGroups, we need to get the id of the OutputPort element id for the source ProcessGroup.
    #   - For OutputPorts, the downstream relationships are defined in the parent ProcessGroup and
    #     all_elements is the dict of elements contained in the parent
    downstream = element.downstream
    if isinstance(element, ProcessGroup):
        # we already validated output ports during init, so just grab the first one
        source_op = [e for e in element.elements.values() if isinstance(e, OutputPort)][0]
        source = get_nifi_entity_by_id('output_port', source_op.id)
    elif isinstance(element, InputPort):
        source = get_nifi_entity_by_id('input_port', element.id)
    elif isinstance(element, Processor):
        source = get_nifi_entity_by_id('processor', element.id)
    elif isinstance(element, OutputPort):
        downstream = parent.downstream
        pg_parent = flow.get_parent_element(parent) # we need to go one more level up in depth on the canvas to get the target elements
        all_elements = pg_parent.elements
        source = get_nifi_entity_by_id('output_port', element.id)

    if downstream:
        for d in downstream:
            dest_element = all_elements.get(d.name)
            if not dest_element:
                raise FlowLibException("The downstream connection element for {} is not defined in {}".format(element.name, source_component.source_file))

            # Get the destincation element NiFi entity by id
            # for ProcessGroups, we need to get the id of the InputPort element id for the
            # destincation ProcessGroup
            if isinstance(dest_element, ProcessGroup):
                # we already validated input ports during init, so just grab the first one
                dest_element = [e for e in dest_element.elements.values() if isinstance(e, InputPort)][0]
                dest = get_nifi_entity_by_id('input_port', dest_element.id)
            elif isinstance(dest_element, OutputPort):
                dest = get_nifi_entity_by_id('output_port', dest_element.id)
            elif isinstance(dest_element, Processor):
                dest = get_nifi_entity_by_id('processor', dest_element.id)
            elif isinstance(dest_element, InputPort):
                raise FlowLibException("The downstream connection element for {} cannot be an InputPort: {}".format(element.name, source_component.source_file))

            logging.debug("Creating connection between source {} and dest {} for relationships {}".format(source.component.name, dest.component.name, d.relationships))
            canvas.create_connection(source, dest, d.relationships)


def get_nifi_entity_by_id(kind, identifier):
    """
    :param kind: One of input_port, output_port, processor, process_group
    :param identifier: The NiFi API identifier uuid of the entity
    """
    logging.debug('Getting Nifi {} Entity with id: {}'.format(kind, identifier))
    if kind == 'input_port':
        e = nipyapi.nifi.InputPortsApi().get_input_port(identifier)
    elif kind == 'output_port':
        e = nipyapi.nifi.OutputPortsApi().get_output_port(identifier)
    elif kind == 'processor':
        e = nipyapi.nifi.ProcessorsApi().get_processor(identifier)
    elif kind == 'process_group':
        e = nipyapi.nifi.ProcessGroupsApi().get_process_group(identifier)
    else:
        raise FlowLibException("{} is not a valid NiFi api type")
    return e


# def check_or_create_controllers(parent_pg, controller, name, properties):
#     """
#     :param parent_pg:
#     :param controller:
#     :param name:
#     :return:
#     """
#     controller_type = models.documented_type_dto.DocumentedTypeDTO(type=controller)
#     controller = canvas.create_controller(parent_pg, controller_type, name)
#     update = models.controller_service_dto.ControllerServiceDTO(properties=properties)
#     canvas.update_controller(controller, update)
#     return controller


# def get_canvas_reverse_location(index, total):
#     x_location = 300
#     # for y, assume each processor is 200
#     y_offset = total - index
#     y_location = 200 * y_offset
#     return (x_location, y_location)


# def get_canvas_location(sequence_number):
#     x_location = 300
#     y_location = 50 + (200 * sequence_number)
#     return (x_location, y_location)

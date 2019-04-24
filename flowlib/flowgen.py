# -*- coding: utf-8 -*-
import copy
import logging
import re
import sys
import yaml

import nipyapi
from nipyapi import canvas
from nipyapi.nifi import models
from nipyapi.nifi import apis

import flowlib
from flowlib.model import (FlowLibException, Flow, FlowComponent, FlowElement,
    ProcessGroup, Processor, InputPort, OutputPort)

# TODO: Rename this module to something else ??
# TODO: Separate this module from the actual NiFi API interaction

# Some constants for canvas dimensions
TOP_LEVEL_PG_LOCATION = (300, 100)
VAR_WRAPPER = "$({})"

# TODO: include git revision if possible
DEPLOYMENT_VERSION_INFO = """B23 FlowLib
flowlib version: {}
git release: {}

flow.yaml version: {}
"""

def validate_flow(config):
    try:
        flow = Flow.load_from_file(config.flow_yaml)
        replace_flow_element_vars_recursive(flow.elements, flow.loaded_components) # move to flow.load_from_file()
        flow.validate()
    except FlowLibException as e:
        logging.error(e)
        sys.exit(1)


def deploy_flow_yaml(config):
    """
    :type config: FlowLibConfig
    """
    logging.info("Deploying NiFi flow from YAML with config:")
    logging.info(config)

    nifi_url = "http://{}:{}/nifi-api".format(config.nifi_address, config.nifi_port)
    nipyapi.config.nifi_config.host = nifi_url
    root_id = nipyapi.canvas.get_root_pg_id()

    try:
        flow = Flow.load_from_file(config.flow_yaml)
        replace_flow_element_vars_recursive(flow.elements, flow.loaded_components)
        # flow.validate()

        logging.info("Deploying {} to NiFi root canvas ID: {}".format(flow.name, root_id))
        root = nipyapi.canvas.get_process_group(root_id, identifier_type='id')

        # TODO: Check here if there is a flow already deployed
        # deployed_flow = Flow.load_from_nifi(nifi_url)
        # flow.compare(deployed_flow)

        # Update root process group metadata with new flow version info
        root.component.name = flow.name
        root.component.comments = DEPLOYMENT_VERSION_INFO.format(flowlib.__version__, flowlib.__git_version__,  flow.version)

        # TODO: Stop all source processors and wait for queues to drain completely.
        # Then stop all remaining processors and remove all connections ?

        # TODO: It is probably more reliable to delete all processors and connections and re-deploy
        # to a blank canvas. This will involve reading the state and setting the state directly in zookeeper
        # for the newly deployed processors ?

        # Set root pg name
        nipyapi.nifi.apis.ProcessGroupsApi().update_process_group(root_id, root)

        # create_controllers(flow)
        create_canvas_elements_recursive(flow.elements, root)
        create_connections_recursive(flow, flow.elements)

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
            raise FlowLibException("Unsupported Element Type: {}".format(el.type))


def create_connections_recursive(flow, elements):
    """
    Recursively creates the connections between elements defined in the Flow
    :param flow: The Flow to create connections for
    :type flow: Flow
    :param elements: a list of FlowElements to connect together
    :type elements: list(FlowElement)
    """
    for el in elements.values():
        if isinstance(el, ProcessGroup):
            create_connections_recursive(flow, el.elements)
        elif el.type in ['processor', 'input_port', 'output_port']:
            create_connections(flow, el)
        else:
            raise FlowLibException("Unsupported Element Type: {}".format(el.type))


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


def create_connections(flow, source_element):
    """
    Create the downstream connections for the element on the NiFi canvas
    :param flow: The Flow to create connections for
    :type flow: Flow
    :param source_element: The source FlowElement to connect to its downstreams
    :type source_element: FlowElement
    """
    logging.info("Creating downstream connections for element: {}/{}".format(source_element.parent_path, source_element.name))
    parent = flow.get_parent_element(source_element)
    # Validate no inputs or outputs on the root canvas
    if not parent and (isinstance(source_element, InputPort) or isinstance(source_element, OutputPort)):
        raise FlowLibException("Input and Output ports are not allowed in the root process group")

    connections = source_element.connections
    if isinstance(source_element, OutputPort):
        if parent.connections:
            connections = [c for c in parent.connections if c.from_port == source_element.name]
        else:
            connections = None

    if connections:
        for c in connections:
            # Find the NiFi Entity ID of the source element
            if isinstance(source_element, Processor) or isinstance(source_element, InputPort):
                elements = parent.elements
                source = get_nifi_entity_by_id(source_element.type, source_element.id)
            elif isinstance(source_element, OutputPort):
                # if source is an output port then we need to to search the next parent's elements for the downstream element
                elements = flow.get_parent_element(parent).elements
                source = get_nifi_entity_by_id(source_element.type, source_element.id)
            else:
                raise FlowLibException("""
                    Something went wrong, failed while recursively connecting flow elements on the canvas.
                    Cannot create downstream connections for elements of type {}""".format(type(source_element)))

            dest_element = elements.get(c.name)
            if not dest_element:
                raise FlowLibException("The destination element {} is not defined, must be one of: {}".format(c.name, elements.keys()))

            # Find the NiFi Entity ID of the dest element
            if isinstance(dest_element, Processor) or isinstance(dest_element, OutputPort):
                dest = get_nifi_entity_by_id(dest_element.type, dest_element.id)
            elif isinstance(dest_element, ProcessGroup):
                d = [v for k,v in dest_element.elements.items() if isinstance(v, InputPort) and k == c.to_port][0]
                dest = get_nifi_entity_by_id(d.type, d.id)
            else:
                raise FlowLibException("""Connections cannot be defined for downstream elements of type 'input_port'.
                  InputPorts can only be referenced from outside of the current component""")

            logging.debug("Creating connection between source {} and dest {} for relationships {}".format(source.component.name, dest.component.name, c.relationships))
            canvas.create_connection(source, dest, c.relationships)
    else:
        logging.debug("Terminal node, no downstream connections found for element {}".format(source_element.name))


def get_nifi_entity_by_id(kind, identifier):
    """
    :param kind: One of input_port, output_port, processor, process_group
    :param identifier: The NiFi API identifier uuid of the entity
    """
    logging.debug("Getting Nifi {} Entity with id: {}".format(kind, identifier))
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

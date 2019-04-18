import copy
import logging
import re
import sys
import yaml


import nipyapi
from nipyapi import canvas
from nipyapi.nifi import models
from nipyapi.nifi import apis

from model import Flow, FlowLibException

# Some constants for canvas dimensions
TOP_LEVEL_PG_LOCATION = (300, 100)
VAR_WRAPPER = "$({})"

def validate_flow_yaml(config):
    try:
        flow = Flow.load_from_file(config.flow_yaml).init()
        replace_flow_element_vars_recursive(flow.elements, flow.loaded_components)
        # TODO: Validate downstream connections
        # validate_flow_connections(flow)
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

        # TODO: create_or_update_controllers(flow)
        replace_flow_element_vars_recursive(flow.elements, flow.loaded_components)
        create_canvas_elements_recursive(flow.elements, root)
        # TODO: create_or_update_connections(flow)
    except FlowLibException as e:
        logging.error(e)


def _replace_vars(process_group, source_component):
    """
    :param process_group: The processorGroup processors that need vars evaluated
    :type process_group: model.ProcessGroup
    :param component: The source component that the processGroup was created from
    :type component: model.FlowComponent
    """
    # We already valdated that required vars were present during flow.init()
    # so don't worry about it here

    # Create a dict of vars to replace
    replacements = copy.deepcopy(source_component.defaults) or dict()
    if process_group.vars:
        for key,val in process_group.vars.items():
            replacements[key] = val


    # format each var name with the expected VAR_WRAPPER
    # so that we can do a lookup when we find a pattern match
    wrapped_vars = dict()
    for k,v in replacements.items():
        wrapped_vars[VAR_WRAPPER.format(k)] = v

    esc_keys = [re.escape(key) for key in wrapped_vars.keys()]
    pattern = re.compile(r'(' + '|'.join(esc_keys) + r')')

    # apply var replacements for each value of processor.config.properties
    for el in process_group.elements.values():
        if el.element_type == 'Processor':
            for k,v in el.config.properties.items():
                el.config.properties[k] = pattern.sub(lambda x: wrapped_vars[x.group()], v)


def replace_flow_element_vars_recursive(elements, loaded_components):
    """
    Recusively apply the variable templating to each element in the flow
    :param elements: The elements to deploy
    :type elements: list(model.FlowElement)
    :param loaded_components: The components that were imported during flow.init()
    :type loaded_components: map(str:model.FlowComponent)
    """
    for el in elements.values():
        if el.element_type == 'ProcessGroup':
            source_component = loaded_components[el.component_ref]
            _replace_vars(el, source_component)
            replace_flow_element_vars_recursive(el.elements, loaded_components)


def create_canvas_elements_recursive(elements, parent_pg):
    """
    Recursively creates the actual NiFi elements (groups, processors, inputs, outputs) on the canvas
    :param elements: The elements to deploy
    :type elements: list(model.FlowElement)
    :param parent_pg: The process group in which to create the processors
    :type parent_pg: nipyapi.nifi.models.process_group_entity.ProcessGroupEntity
    """
    for el in elements.values():
        if el.element_type == 'ProcessGroup':
            pg = create_or_update_process_group(el, parent_pg)
            create_canvas_elements_recursive(el.elements, pg)
        elif el.element_type == 'Processor':
            create_or_update_processor(el, parent_pg)
        elif el.element_type == 'InputPort':
            create_or_update_input_port(el, parent_pg)
        elif el.element_type == 'OutputPort':
            create_or_update_output_port(el, parent_pg)
        else:
            raise FlowLibException("Unsupported Element Type: {}".format(el.element_type))


def create_or_update_process_group(element, parent_pg):
    """
    :param element: The process group to deploy
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

    return pg


def create_or_update_processor(element, parent_pg):
    """
    :param element: The processor to deploy
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

    return p


def create_or_update_input_port(element, parent_pg):
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

    return ip


def create_or_update_output_port(element, parent_pg):
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

    return op


# def get_connection_info(connection):
#     """
#     :param connection:
#     :return:
#     """
#     ap = apis.connections_api.ConnectionsApi()
#     connection = ap.get_connection(connection.id)
#     return connection


# def update_connection(source_pe, downstream_pe, connection, connection_params):
#     """
#     :param connection_params:
#     :param source_pe:
#     :param downstream_pe:
#     :param connection:
#     :return:
#     """

#     destination_component = models.connectable_dto.ConnectableDTO(
#         type='PROCESSOR',
#         group_id=downstream_pe.component.parent_group_id,
#         id=downstream_pe.id
#     )
#     source_component = models.connectable_dto.ConnectableDTO(
#         type='PROCESSOR',
#         group_id=source_pe.component.parent_group_id,
#         id=source_pe.id
#     )
#     component_connection = models.connection_dto.ConnectionDTO(
#         **connection_params,
#         id=connection.id,
#         source=source_component,
#         destination=destination_component
#     )

#     existing_revision = get_connection_info(connection).revision.version
#     logging.info("existing revision is {}".format(existing_revision))

#     revision = models.revision_dto.RevisionDTO(
#         version=existing_revision
#     )
#     connection_body_config = models.connection_entity.ConnectionEntity(
#         id=connection.id,
#         source_type='PROCESSOR',
#         destination_type='PROCESSOR',
#         component=component_connection,
#         revision=revision
#     )
#     ap = apis.connections_api.ConnectionsApi()
#     update = ap.update_connection(connection.id, connection_body_config)

#     return update


# def check_or_create_connection(source_pe, processor):
#     # inefficeint way to check, but this is only known approach now
#     all_connections = canvas.list_all_connections('root', True)
#     logging.info("identified {} existing connections".format(len(all_connections)))
#     logging.info("source processor entity id is {}".format(source_pe.id))

#     # start iterating through the proposed new connections
#     for connection in processor['connections']:
#         logging.info("connection is {}".format(connection))
#         downstream_pe = canvas.get_processor(connection['downstream_name'], identifier_type='name')
#         logging.info("downstream processor id is {}".format(downstream_pe.id))
#         logging.info("relationship is {}".format(connection['relationship']))

#         # if there at least one connection on the canvas, otherwise just create it
#         if all_connections:

#             # initialize that we are going to look and see if connection exists already
#             found_connection = False

#             for existing_connection in all_connections:
#                 # Check for a match between proposed and existing - idempotency
#                 if (source_pe.id == existing_connection.source_id) and (downstream_pe.id == existing_connection.destination_id):
#                     found_connection = True
#                     logging.info("connection between {} and {} already exists. Ignoring".format(source_pe.id, downstream_pe.id))
#                     update = update_connection(source_pe, downstream_pe, existing_connection, connection['config'])
#                     break

#                 else:
#                     logging.info("Connection did not exist between {} and {}".format(source_pe.id, downstream_pe.id))

#             # if all existing connections were checked and still did not find a match, then create one
#             if not found_connection:
#                 logging.info("creating connection between {} and {}".format(source_pe.id, downstream_pe.id))
#                 connection = canvas.create_connection(source_pe, downstream_pe,
#                                                           relationships=connection['relationship'])

#         # No connections existed originally, so just start creating them
#         else:

#             new_connection = canvas.create_connection(source_pe, downstream_pe, relationships=connection['relationship'])
#             logging.info("connection {} created".format(new_connection.id))
#             update = update_connection(source_pe, downstream_pe, new_connection, connection['config'])
#     return connection


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

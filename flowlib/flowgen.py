import nipyapi
from nipyapi import canvas
from nipyapi.nifi import models
from nipyapi.nifi import apis

import yaml
import logging

# Some constants for canvas dimensions
TOP_LEVEL_PG_LOCATION = (300, 100)


def deploy_from_yaml(config):
    logging.info("Deploying NiFi flow from YAML with config:")
    logging.info(config)

    nifi_url = 'http://{}:{}/nifi-api'.format(config.nifi_address, config.nifi_port)
    nipyapi.config.nifi_config.host = nifi_url
    root_id = nipyapi.canvas.get_root_pg_id()
    root_pge = models.process_group_entity.ProcessGroupEntity(id=root_id)
    logging.info("Deploying flow to NiFi root canvas ID: {}".format(root_id))

    # TODO: parse this to a real graph data structure
    # we need to be able to go from yaml -> nifi as well as nifi -> yaml, should be 1:1
    # Additionally, it should be composeable so that we can re-use process groups via references
    # and input/output ports
    flow = yaml.safe_load(config.flow_yaml)

    pge_name = flow['processor_group_name']
    logging.info("Found top level process group: {}".format(pge_name))

    # Create flow-specific processor group (under root processor group entity)
    pge = check_or_create_pg(root_pge, pge_name, get_canvas_location(0))

    # Create or Update Controllers
    # total_controllers = len(flow['controllers'])
    # logging.info('Found {} total controllers'.format(total_controllers))
    # TODO: create controllers from yaml
    # for index, controller in enumerate(flow['controllers']):
    #     controller = b23.check_or_create_controllers(pge,
    #                                                  controller['type'],
    #                                                  controller['name'],
    #                                                  controller['properties']
    #                                                  )
    #     logging.info('created controller {}'.format(controller))

    total_processors = len(flow['processors'])
    logging.info("Found {} total processors".format(total_processors))

    pce_list = list()
    for index, processor in enumerate(flow['processors']):
        # get the processor entity object if new or exists, then add to list
        processor_entity = check_or_create_proc(pge, processor, index, total_processors)
        pce_list.append(processor_entity)
        logging.info('Added processor to canvas: {}'.format(processor_entity.component.name))

    connection_list = list()
    for index, processor in enumerate(flow['processors']):
        connection = check_or_create_connection(pce_list[index], processor)
        connection_list.append(connection)


## TODO: Use create_or_update pattern instead of check or create ##

def check_or_create_pg(top_pge, name, location):
    """
    Checks to see if process group exists. If not, create one.
    :param top_pge:
    :param name:
    :param location:
    :return:
    """
    pge = canvas.get_process_group(name, identifier_type='name')
    if pge:
        logging.info("process group {} with id {} already exists.  Ignoring create request".format(name, pge.id))
    else:
        pge = canvas.create_process_group(top_pge, name, TOP_LEVEL_PG_LOCATION)  # unable to configure PG
        logging.info("new process group {} created".format(pge.component.name))
    return pge


def check_or_create_proc(top_pge, processor, index, total):
    p_name = processor['name']
    proc = canvas.get_processor(p_name, identifier_type='name')
    if proc:
        logging.info("processor {} {} already exists.  Ignoring create request".format(proc.id, p_name))
    else:
        logging.info("creating new processor {}".format(p_name))
        logging.info('processor type is {}'.format(processor['type']))
        logging.info('processor properties are {}'.format(processor['properties']))
        p_type = models.DocumentedTypeDTO(type=processor['type'])
        p_location = get_canvas_location(index)
        initial_proc = canvas.create_processor(top_pge, p_type, p_location, p_name)
        logging.info('processor created with id of {}'.format(initial_proc.id))

        # Update the processor
        p_config = models.processor_config_dto \
            .ProcessorConfigDTO(
                properties=processor['properties'],
                auto_terminated_relationships=processor['auto_terminate'],
                concurrently_schedulable_task_count=processor['concurrently_schedulable_task_count'],
                scheduling_period=processor['scheduling_period'],
                scheduling_strategy=processor['scheduling_strategy'],
                comments=processor['comments']
        )
        proc = canvas.update_processor(initial_proc, p_config)

    return proc


def get_connection_info(connection):
    """
    :param connection:
    :return:
    """
    ap = apis.connections_api.ConnectionsApi()
    connection = ap.get_connection(connection.id)
    return connection


def update_connection(source_pe, downstream_pe, connection, connection_params):
    """
    :param connection_params:
    :param source_pe:
    :param downstream_pe:
    :param connection:
    :return:
    """

    destination_component = models.connectable_dto.ConnectableDTO(
        type='PROCESSOR',
        group_id=downstream_pe.component.parent_group_id,
        id=downstream_pe.id
    )
    source_component = models.connectable_dto.ConnectableDTO(
        type='PROCESSOR',
        group_id=source_pe.component.parent_group_id,
        id=source_pe.id
    )
    component_connection = models.connection_dto.ConnectionDTO(
        **connection_params,
        id=connection.id,
        source=source_component,
        destination=destination_component
    )

    existing_revision = get_connection_info(connection).revision.version
    logging.info('existing revision is {}'.format(existing_revision))

    revision = models.revision_dto.RevisionDTO(
        version=existing_revision
    )
    connection_body_config = models.connection_entity.ConnectionEntity(
        id=connection.id,
        source_type='PROCESSOR',
        destination_type='PROCESSOR',
        component=component_connection,
        revision=revision
    )
    ap = apis.connections_api.ConnectionsApi()
    update = ap.update_connection(connection.id, connection_body_config)

    return update


def check_or_create_connection(source_pe, processor):
    # inefficeint way to check, but this is only known approach now
    all_connections = canvas.list_all_connections('root', True)
    logging.info('identified {} existing connections'.format(len(all_connections)))
    logging.info('source processor entity id is {}'.format(source_pe.id))

    # start iterating through the proposed new connections
    for connection in processor['connections']:
        logging.info('connection is {}'.format(connection))
        downstream_pe = canvas.get_processor(connection['downstream_name'], identifier_type='name')
        logging.info('downstream processor id is {}'.format(downstream_pe.id))
        logging.info('relationship is {}'.format(connection['relationship']))

        # if there at least one connection on the canvas, otherwise just create it
        if all_connections:

            # initialize that we are going to look and see if connection exists already
            found_connection = False

            for existing_connection in all_connections:
                # Check for a match between proposed and existing - idempotency
                if (source_pe.id == existing_connection.source_id) and (downstream_pe.id == existing_connection.destination_id):
                    found_connection = True
                    logging.info(
                        'connection between {} and {} already exists. Ignoring'.format(source_pe.id, downstream_pe.id))
                    update = update_connection(source_pe, downstream_pe, existing_connection, connection['config'])
                    break

                else:
                    logging.info('Connection did not exist between {} and {}'.format(source_pe.id, downstream_pe.id))

            # if all existing connections were checked and still did not find a match, then create one
            if not found_connection:
                logging.info('creating connection between {} and {}'.format(source_pe.id, downstream_pe.id))
                connection = canvas.create_connection(source_pe, downstream_pe,
                                                          relationships=connection['relationship'])

        # No connections existed originally, so just start creating them
        else:

            new_connection = canvas.create_connection(source_pe, downstream_pe, relationships=connection['relationship'])
            logging.info('connection {} created'.format(new_connection.id))
            update = update_connection(source_pe, downstream_pe, new_connection, connection['config'])
    return connection


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


def get_canvas_location(sequence_number):
    x_location = 300
    y_location = 50 + (200 * sequence_number)
    return (x_location, y_location)

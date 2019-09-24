# -*- coding: utf-8 -*-
import io
import os
import yaml
import time
import re
from urllib3.exceptions import MaxRetryError

import nipyapi

from flowlib.logger import log
from flowlib.model import FlowLibException
from flowlib.model.deployment import FlowDeployment, DeployedComponent
from flowlib.model.flow import InputPort, OutputPort, ProcessGroup, Processor
import flowlib.layout
import flowlib.parser


def wait_for_nifi_api(nifi_endpoint, retries=24, delay=5):
    log.info("Waiting for NiFi api to be ready at {}...".format(nifi_endpoint))
    nipyapi.config.nifi_config.host = nifi_endpoint
    i = 0
    while i < retries:
        try:
            nipyapi.nifi.FlowApi().get_process_group_status('root')
            return
        except MaxRetryError as e:
            i += 1
            time.sleep(delay)
    raise FlowLibException("Timeout reached while waiting for NiFi Rest API to be ready")


def init_from_nifi(flow, nifi_endpoint):
    """
    Initialize a Flow from from a running NiFi instance
    :param flow: An unitialized Flow instance
    :type flow: flowlib.model.Flow
    :param nifi_endpoint: A NiFi api endpoint
    :type nifi_endpoint: str
    """
    wait_for_nifi_api(nifi_endpoint)
    root_id = nipyapi.canvas.get_root_pg_id()
    root = nipyapi.canvas.get_process_group(root_id, identifier_type='id')

    deployment = FlowDeployment.from_dict(yaml.safe_load(root.component.comments))
    flowlib.parser.init_from_deployment(flow, deployment)


def deploy_flow(flow, nifi_endpoint, deployment_state=None, force=False):
    """
    Deploy a Flow to NiFi via the Rest api
    :param flow: A Flow instance
    :type flow: flowlib.model.flow.Flow
    """
    wait_for_nifi_api(nifi_endpoint)

    # Create a new FlowDeployment and add all the loaded_components to it
    deployment = FlowDeployment(flow.name, flow.raw, flowlib.__version__)
    for component in flow.loaded_components.values():
        deployment.add(DeployedComponent(component.name, component.raw))

    canvas_root_id = nipyapi.canvas.get_root_pg_id()
    canvas_root_pg = nipyapi.canvas.get_process_group(canvas_root_id, identifier_type='id')
    log.info("Deploying {} to NiFi".format(flow.name))

    # TODO: temporarily rename this and don't delete it until after the flow is re-deployed successfully, GH #33
    flow_pg = nipyapi.canvas.get_process_group(flow.name, identifier_type='name')
    if flow_pg and force:
        if isinstance(flow_pg, list):
            raise FlowLibException("Found multiple ProcessGroups named {}".format(flow.name))
        else:
            _force_cleanup_flow(flow_pg.id)

    flow_pg_element = ProcessGroup(flow.name, None, "process_group", None)
    flow_pg = _create_process_group(flow_pg_element, canvas_root_pg, flowlib.layout.TOP_LEVEL_PG_LOCATION, deployment, is_flow_root=True)

    # reset fps
    flow.raw.seek(0)
    for c in flow.loaded_components.values():
        if c.raw:
            c.raw.seek(0)

    _create_controllers(flow, flow_pg)

    # We must wait until the controllers exist in NiFi before applying jinja templating
    # because the controller() helper needs to lookup controller IDs for injecting into the processor's properties
    flowlib.parser.replace_flow_element_vars_recursive(flow, flow.elements, flow.loaded_components)

    _create_canvas_elements_recursive(flow.elements, flow_pg, deployment)
    _create_connections_recursive(flow, flow.elements)
    _set_controllers_enabled(flow, enabled=True)

    # Find all deployed flows and re-organize the top level PGs
    pgs = nipyapi.nifi.ProcessGroupsApi().get_process_groups(canvas_root_id).process_groups
    log.info("Found {} deployed flows, updating top level canvas layout.".format(len(pgs)))
    pgs = sorted(pgs, key=lambda e: e.component.name)
    positions = flowlib.layout.generate_top_level_pg_positions(pgs)
    for pg in pgs:
        pg.component.position = positions.get(pg.component.name, flowlib.layout.DEFAULT_POSITION)
        log.info("Setting position for {} to {}".format(pg.component.name, pg.position))
        nipyapi.nifi.apis.ProcessGroupsApi().update_process_group(pg.id, pg)

    # Get the updated flow PG
    flow_pg = nipyapi.canvas.get_process_group(flow.name, identifier_type='name')

    # Write deployment yaml to buffer
    s = io.StringIO()
    deployment.save(s)

    # Save to local file
    deployment_out = os.path.join(os.path.dirname(flow.flow_src), '.deployment.json')
    with open(deployment_out, 'w') as f:
        s.seek(0)
        f.write(s.read())

    # Save in NiFi instance PG comments
    s.seek(0)
    flow_pg.component.comments = s.read()
    nipyapi.nifi.apis.ProcessGroupsApi().update_process_group(flow_pg.id, flow_pg)


def _get_nifi_entity_by_id(kind, identifier):
    """
    :param kind: One of input_port, output_port, processor, process_group
    :param identifier: The NiFi API identifier uuid of the entity
    """
    log.debug("Getting Nifi {} Entity with id: {}".format(kind, identifier))
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


def _create_controllers(flow, flow_pg):
    """
    Create the controller services for the flow
    :param flow: A Flow instance
    :type flow: flowlib.model.Flow
    :param flow_pg: The process group of the root flow being deployed
    :type flow_pg: nipyapi.nifi.models.process_group_entity.ProcessGroupEntity
    """
    all_controller_types = list(map(lambda x: x.type, nipyapi.canvas.list_all_controller_types()))
    for c in flow.controllers:
        if c.config.package_id not in all_controller_types:
            raise FlowLibException("{} is not a valid NiFi Controller Service type".format(c.config.package_id))

        controller_type = nipyapi.nifi.models.DocumentedTypeDTO(type=c.config.package_id)
        controller = nipyapi.canvas.create_controller(flow_pg, controller_type, name=c.name)
        controller = nipyapi.canvas.get_controller(controller.id, identifier_type='id')
        nipyapi.canvas.update_controller(controller, c.config)
        c.id = controller.id
        c.parent_id = flow_pg.id


def _set_controllers_enabled(flow, enabled=True):
    """
    Start/Enable or Stop/Disable all controller services for a flow
    :param flow: A Flow instance
    :type flow: flowlib.model.Flow
    """
    for c in flow.controllers:
        controller = nipyapi.canvas.get_controller(c.id, identifier_type='id')
        nipyapi.canvas.schedule_controller(controller, enabled)


def _create_canvas_elements_recursive(elements, parent_pg, deployment):
    """
    Recursively creates the actual NiFi elements (process_groups, processors, inputs, outputs) on the canvas
    :param elements: The elements to deploy
    :type elements: list(model.FlowElement)
    :param parent_pg: The process group in which to create the processors
    :type parent_pg: nipyapi.nifi.models.process_group_entity.ProcessGroupEntity
    :param deployment: The current deployment
    :type deployment: flowlib.model.deployment.FlowDeployment
    """

    # Generate a dictionary of {name: (x,y)} positions for each element
    positions = flowlib.layout.generate_layout(elements)

    for el in elements.values():
        position = positions[el.name]
        if isinstance(el, ProcessGroup):
            pg = _create_process_group(el, parent_pg, position, deployment)
            _create_canvas_elements_recursive(el.elements, pg, deployment)
        elif isinstance(el, Processor):
            _create_processor(el, parent_pg, position, deployment)
        elif isinstance(el, InputPort):
            _create_input_port(el, parent_pg, position)
        elif isinstance(el, OutputPort):
            _create_output_port(el, parent_pg, position)
        else:
            raise FlowLibException("Unsupported Element Type: {}".format(el.type))


def _create_connections_recursive(flow, elements):
    """
    Recursively creates the connections between elements defined in the Flow
    :param flow: The Flow to create connections for
    :type flow: Flow
    :param elements: a list of FlowElements to connect together
    :type elements: list(FlowElement)
    """
    for el in elements.values():
        if isinstance(el, ProcessGroup):
            _create_connections_recursive(flow, el.elements)
        elif el.type in ['processor', 'input_port', 'output_port']:
            _create_connections(flow, el)
        else:
            raise FlowLibException("Unsupported Element Type: {}".format(el.type))


def _create_process_group(element, parent_pg, position, deployment, is_flow_root=False):
    """
    Create a Process Group on the NiFi canvas
    :param element: The Process Group to deploy
    :type element: model.ProcessGroup
    :param parent_pg: The process group in which to create the new process group
    :type parent_pg: nipyapi.nifi.models.process_group_entity.ProcessGroupEntity
    :param is_flow_root: Whether the PG being created is the root of a flow being deployed
    :type is_flow_root: bool
    :param deployment: The current flow deployment
    :type deployment: flowlib.model.deployment.FlowDeployment
    """
    name = "{}/{}".format(element.name, parent_pg.id)
    if is_flow_root:
        name = element.name

    log.info("Creating ProcessGroup: {}".format(name))
    pg = nipyapi.canvas.get_process_group(name)
    if pg:
        log.error("Found existing ProcessGroup: {}".format(name))
        raise FlowLibException("Re-deploying a flow is not yet supported")
    else:
        log.debug("Creating ProcessGroup: {} with parent: {}".format(name, element.parent_path))
        pg = nipyapi.canvas.create_process_group(parent_pg, name, position)

        if is_flow_root:
            deployment.root_group_id = pg.id

    element.id = pg.id
    element.parent_id = parent_pg.id
    return pg


def _create_processor(element, parent_pg, position, deployment):
    """
    Create a Processor on the NiFi canvas
    :param element: The Processor to deploy
    :type element: model.Processor
    :param parent_pg: The process group in which to create the new processor
    :type parent_pg: nipyapi.nifi.models.process_group_entity.ProcessGroupEntity
    :param deployment: The current flow deployment
    :type deployment: flowlib.model.deployment.FlowDeployment
    """
    name = "{}/{}".format(element.name, parent_pg.id)
    log.info("Creating Processor: {}".format(name))
    p = nipyapi.canvas.get_processor(name)
    if p:
        log.error("Found existing Processor: {}".format(name))
        raise FlowLibException("Re-deploying a flow is not yet supported")
    else:
        log.debug("Creating Processor: {} with parent: {}".format(name, element.parent_path))
        _type = nipyapi.nifi.models.DocumentedTypeDTO(type=element.config.package_id)
        p = nipyapi.canvas.create_processor(parent_pg, _type, position, name, element.config)

        # If the processor is stateful, add it to the instances
        if _type.type in flowlib.STATEFUL_PROCESSORS:
            if element.src_component_name == 'root':
                deployment.root_processors[element.name] = p.id
            else:
                deployed_component = deployment.get_component(element.src_component_name)
                deployed_component.instances[element.parent_path + "/" + element.name] = {
                    "group_id": parent_pg.id,
                    "processor_id": p.id
                }

    element.id = p.id
    element.parent_id = parent_pg.id
    return p


def _create_input_port(element, parent_pg, position):
    """
    Create an Input Port on the NiFi canvas
    :param element: The InputPort to deploy
    :type element: flowlib.model.InputPort
    :param parent_pg: The process group in which to create the new processor
    :type parent_pg: nipyapi.nifi.models.process_group_entity.ProcessGroupEntity
    """
    name = "{}/{}".format(element.name, parent_pg.id)
    log.info("Creating InputPort: {}".format(name))
    filtered_ips = [ip for ip in nipyapi.canvas.list_all_input_ports() if name in ip.component.name]
    ip = None
    if len(filtered_ips) > 0:
        ip = filtered_ips[0]
    if ip:
        log.error("Found existing InputPort: {}".format(name))
        raise FlowLibException("Re-deploying a flow is not yet supported")
    else:
        log.debug("Creating InputPort: {} with parent: {}".format(name, element.parent_path))
        ip = nipyapi.canvas.create_port(parent_pg.id, 'INPUT_PORT', name, 'STOPPED', position=position)

    element.id = ip.id
    element.parent_id = parent_pg.id
    return ip


def _create_output_port(element, parent_pg, position):
    """
    Create an Output Port on the NiFi canvas
    :param element: The Output Port to deploy
    :type element: model.OutputPort
    :param parent_pg: The process group in which to create the new processor
    :type parent_pg: nipyapi.nifi.models.process_group_entity.ProcessGroupEntity
    """
    name = "{}/{}".format(element.name, parent_pg.id)
    log.info("Creating OutputPort: {}".format(name))
    filtered_ops = [op for op in nipyapi.canvas.list_all_output_ports() if name in op.component.name]
    op = None
    if len(filtered_ops) > 0:
        op = filtered_ops[0]
    if op:
        log.error("Found existing OutputPort: {}".format(name))
        raise FlowLibException("Re-deploying a flow is not yet supported")
    else:
        log.debug("Creating OutputPort: {} with parent: {}".format(name, element.parent_path))
        op = nipyapi.canvas.create_port(parent_pg.id, 'OUTPUT_PORT', name, 'STOPPED', position=position)

    element.id = op.id
    element.parent_id = parent_pg.id
    return op


def _create_connections(flow, source_element):
    """
    Create the downstream connections for the element on the NiFi canvas
    :param flow: The Flow to create connections for
    :type flow: Flow
    :param source_element: The source FlowElement to connect to its downstreams
    :type source_element: FlowElement
    """
    log.info("Creating downstream connections for element: {}/{}".format(source_element.parent_path, source_element.name))
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
                source = _get_nifi_entity_by_id(source_element.type, source_element.id)
            elif isinstance(source_element, OutputPort):
                # if source is an output port then we need to to search the next parent's elements for the downstream element
                elements = flow.get_parent_element(parent).elements
                source = _get_nifi_entity_by_id(source_element.type, source_element.id)
            else:
                raise FlowLibException("""
                    Something went wrong, failed while recursively connecting flow elements on the canvas.
                    Cannot create downstream connections for elements of type {}""".format(type(source_element)))

            dest_element = elements.get(c.name)
            if not dest_element:
                raise FlowLibException("The destination element {} is not defined, must be one of: {}".format(c.name, elements.keys()))

            # Find the NiFi Entity ID of the dest element
            if isinstance(dest_element, Processor) or isinstance(dest_element, OutputPort):
                dest = _get_nifi_entity_by_id(dest_element.type, dest_element.id)
            elif isinstance(dest_element, ProcessGroup):
                d = [v for k,v in dest_element.elements.items() if isinstance(v, InputPort) and k == c.to_port][0]
                dest = _get_nifi_entity_by_id(d.type, d.id)
            else:
                raise FlowLibException("""Connections cannot be defined for downstream elements of type 'input_port'.
                  InputPorts can only be referenced from outside of the current component""")

            log.debug("Creating connection between source {} and dest {} for relationships {}".format(source.component.name, dest.component.name, c.relationships))
            nipyapi.canvas.create_connection(source, dest, c.relationships)
    else:
        log.debug("Terminal node, no downstream connections found for element {}".format(source_element.name))


def _force_cleanup_flow(flow_pg_id):
    """
    Delete a deployed Flow from the NiFi canvas so that flows can be re-deployed
    :param flow_pg_id: The id of the Flow's ProcessGroup
    :type flow_pg_id: str
    """
    log.info("Deleting flow connections...")
    connections = nipyapi.canvas.list_all_connections(pg_id=flow_pg_id, descendants=True)
    for c in connections:
        nipyapi.canvas.delete_connection(c, purge=True)

    log.info("Deleting flow controller services...")
    controllers = nipyapi.canvas.list_all_by_kind('controllers', pg_id=flow_pg_id, descendants=False)
    if controllers and not isinstance(controllers, list):
        controllers = [controllers]
    for c in controllers:
        nipyapi.canvas.delete_controller(c, force=True)

    log.info("Deleting flow process group...")
    flow_pg = _get_nifi_entity_by_id('process_group', flow_pg_id)
    nipyapi.canvas.delete_process_group(flow_pg, force=True)

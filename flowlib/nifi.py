# -*- coding: utf-8 -*-
import time
import re
from jinja2 import Template
from urllib3.exceptions import MaxRetryError

import nipyapi

from flowlib.logger import log
from flowlib.model import FlowLibException, InputPort, OutputPort, ProcessGroup, Processor
import flowlib.parser
import flowlib.layout

FLOW_DEPLOYMENT_INFO = """
### DO NOT CHANGE ANYTHING BELOW THIS LINE ###
This NiFi Flow was generated and deployed by B23 FlowLib
version: {{ flowlib_version }}

### flow.yaml ###

{{ flow_raw }}

### components ###
{% for c in flow_components %}
# {{ c.ref }} #

{{ c.raw }}
{% endfor %}
"""

MATCH_LIB_VERSION = r'B23 FlowLib\sversion:\s(.*)'
MATCH_FLOW_YAML = r'### flow.yaml ###\s(.*)\s# components #'
MATCH_COMPONENTS = r'### components ###\s(.*)'


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
    flow.name = root.component.name
    _init_flow_meta_info(flow, root.component.comments)
    # _init_flow_elements_recursive(flow, root)
    # _init_flow_connections_recursive(flow, root)


def deploy_reporting_tasks(nifi_endpoint, reporting_task_controllers, reporting_tasks, force=False):
    """
    Deploy ReportingTasks and required controller services to NiFi via the Rest api
    :param nifi_endpoint: The NiFi api endpoint
    :type nifi_endpoint: str
    :param reporting_task_controllers: The controller services to deploy
    :type reporting_task_controllers: list(flowlib.model.Controller)
    :param reporting_tasks: The reporting tasks to depoy
    :type reporting_tasks: list(flowlib.model.ReportingTask)
    """
    wait_for_nifi_api(nifi_endpoint)
    if force:
        _force_cleanup_reporting_tasks()

    # apply templating and create the reporting task controllers
    reporting_task_controllers = flowlib.parser.init_reporting_task_controllers(reporting_task_controllers)
    _create_reporting_task_controllers(reporting_task_controllers)

    # enable the new controller services
    controllers = nipyapi.nifi.apis.FlowApi().get_controller_services_from_controller().controller_services
    _set_controllers_enabled(controllers, enabled=True)

    # apply templating and create the reporting tasks
    reporting_tasks = flowlib.parser.init_reporting_tasks(reporting_task_controllers, reporting_tasks)
    _create_reporting_tasks(reporting_tasks)
    _set_reporting_tasks_enabled(reporting_tasks, enabled=True)


def deploy_flow(flow, nifi_endpoint, force=False):
    """
    Deploy a Flow to NiFi via the Rest api
    :param flow: A Flow instance
    :type flow: flowlib.model.Flow
    """
    wait_for_nifi_api(nifi_endpoint)
    canvas_root_id = nipyapi.canvas.get_root_pg_id()
    canvas_root_pg = nipyapi.canvas.get_process_group(canvas_root_id, identifier_type='id')
    log.info("Deploying {} to NiFi".format(flow.name))

    flow_pg = nipyapi.canvas.get_process_group(flow.name, identifier_type='name')
    if flow_pg and force:
        if isinstance(flow_pg, list):
            raise FlowLibException("Found multiple ProcessGroups named {}".format(flow.name))
        else:
            _force_cleanup_flow(flow_pg.id)

    flow_pg_element = ProcessGroup(flow.name, None, "process_group", None)
    flow_pg = _create_process_group(flow_pg_element, canvas_root_pg, flowlib.layout.TOP_LEVEL_PG_LOCATION, is_flow_root=True)

    # TODO: Filter loaded_components that are actually used in this flow

    # reset fps
    flow.raw.seek(0)
    for c in flow.loaded_components.values():
        if c.raw:
            c.raw.seek(0)

    # Update flow process group metadata with version info
    context = {
        'flowlib_version': flow.flowlib_version,
        'flow_raw': flow.raw.read(),
        'flow_components': [{'ref': k, 'raw': v.raw.read()} for k,v in flow.loaded_components.items()]
    }
    t = Template(FLOW_DEPLOYMENT_INFO)
    flow_pg.component.comments = t.render(context)
    nipyapi.nifi.apis.ProcessGroupsApi().update_process_group(flow_pg.id, flow_pg)

    _create_controllers(flow, flow_pg)

    # We must wait until the controllers exist in NiFi before applying jinja templating
    # because the controller() helper needs to lookup controller IDs for injecting into the processor's properties
      # flowlib.parser.set_global_helpers(flow.controllers)
    flowlib.parser.replace_flow_element_vars_recursive(flow, flow.elements, flow.loaded_components)

    _create_canvas_elements_recursive(flow.elements, flow_pg)
    _create_connections_recursive(flow, flow.elements)
    _set_controllers_enabled(flow.controllers, enabled=True)

    # find all deployed flows and re-organize the top level PGs
    pgs = nipyapi.nifi.ProcessGroupsApi().get_process_groups(canvas_root_id).process_groups
    log.info("Found {} deployed flows, updating top level canvas layout.".format(len(pgs)))
    pgs = sorted(pgs, key=lambda e: e.component.name)
    positions = flowlib.layout.generate_top_level_pg_positions(pgs)
    for pg in pgs:
        pg.component.position = positions.get(pg.component.name, flowlib.layout.DEFAULT_POSITION)
        log.info("Setting position for {} to {}".format(pg.component.name, pg.position))
        nipyapi.nifi.apis.ProcessGroupsApi().update_process_group(pg.id, pg)


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


def _create_reporting_task_controllers(controllers):
    """
    Create the reporting task controller services for the NiFi instance
    :param controllers: A list of ReportingTaskControllers to create
    :type controllers: list(Controllers)
    """
    all_controller_types = list(map(lambda x: x.type, nipyapi.canvas.list_all_controller_types()))
    for c in controllers:
        if c.config.package_id not in all_controller_types:
            raise FlowLibException("{} is not a valid NiFi Controller Service type".format(c.config.package_id))

        controller = nipyapi.nifi.apis.ControllerApi().create_controller_service(
            body=nipyapi.nifi.ControllerServiceEntity(
                revision={'version': 0},
                component=nipyapi.nifi.ControllerServiceDTO(
                    type=c.config.package_id,
                    name=c.name,
                    properties=c.config.properties
                )
            )
        )
        c.id = controller.id


def _create_reporting_tasks(tasks):
    """
    Create the ReportingTasks for the NiFi instance
    :param tasks: A list of ReportingTasks to create
    :type tasks: list(ReportingTask)
    """
    for t in tasks:
        task = nipyapi.nifi.apis.ControllerApi().create_reporting_task(
            body=nipyapi.nifi.ReportingTaskEntity(
                revision={'version': 0},
                component=nipyapi.nifi.ReportingTaskDTO(
                    type=t.config.package_id,
                    name=t.name,
                    properties=t.config.properties
                )
            )
        )
        t.id = task.id


def _set_controllers_enabled(controllers, enabled=True):
    """
    Start/Enable or Stop/Disable all controller services for a flow
    :param flow: A list of controllers to enable/disable
    :type flow: list(Controller)
    """
    for c in controllers:
        controller = nipyapi.canvas.get_controller(c.id, identifier_type='id')
        nipyapi.canvas.schedule_controller(controller, enabled)


def _set_reporting_tasks_enabled(tasks, enabled=True):
    """
    Start/Enable or Stop/Disable all reporting tasks
    :param flow: A list of reporting tasks to enable/disable
    :type flow: list(ReportingTask)
    """
    state = 'RUNNING' if enabled else 'STOPPED'
    for t in tasks:
        task = nipyapi.nifi.apis.ReportingTasksApi().get_reporting_task(t.id)
        nipyapi.nifi.apis.ReportingTasksApi().update_run_status(t.id,
            body=nipyapi.nifi.ReportingTaskRunStatusEntity(
                revision=task.revision,
                state=state
            )
        )


def _create_canvas_elements_recursive(elements, parent_pg):
    """
    Recursively creates the actual NiFi elements (process_groups, processors, inputs, outputs) on the canvas
    :param elements: The elements to deploy
    :type elements: list(model.FlowElement)
    :param parent_pg: The process group in which to create the processors
    :type parent_pg: nipyapi.nifi.models.process_group_entity.ProcessGroupEntity
    """

    # Generate a dictionary of {name: (x,y)} positions for each element
    positions = flowlib.layout.generate_layout(elements)

    for el in elements.values():
        position = positions[el.name]
        if isinstance(el, ProcessGroup):
            pg = _create_process_group(el, parent_pg, position)
            _create_canvas_elements_recursive(el.elements, pg)
        elif isinstance(el, Processor):
            _create_processor(el, parent_pg, position)
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


def _create_process_group(element, parent_pg, position, is_flow_root=False):
    """
    Create a Process Group on the NiFi canvas
    :param element: The Process Group to deploy
    :type element: model.ProcessGroup
    :param parent_pg: The process group in which to create the new process group
    :type parent_pg: nipyapi.nifi.models.process_group_entity.ProcessGroupEntity
    """
    name = "{}/{}".format(element.name, parent_pg.id)
    if is_flow_root:
        name = element.name

    log.info("Create or update ProcessGroup: {}".format(name))
    pg = nipyapi.canvas.get_process_group(name)
    if pg:
        log.error("Found existing ProcessGroup: {}".format(name))
        raise FlowLibException("Re-deploying a flow is not yet supported")
    else:
        log.debug("Creating ProcessGroup: {} with parent: {}".format(name, element.parent_path))
        pg = nipyapi.canvas.create_process_group(parent_pg, name, position)

    element.id = pg.id
    element.parent_id = parent_pg.id
    return pg


def _create_processor(element, parent_pg, position):
    """
    Create a Processor on the NiFi canvas
    :param element: The Processor to deploy
    :type element: model.Processor
    :param parent_pg: The process group in which to create the new processor
    :type parent_pg: nipyapi.nifi.models.process_group_entity.ProcessGroupEntity
    """
    name = "{}/{}".format(element.name, parent_pg.id)
    log.info("Create or update Processor: {}".format(name))
    p = nipyapi.canvas.get_processor(name)
    if p:
        log.error("Found existing Processor: {}".format(name))
        raise FlowLibException("Re-deploying a flow is not yet supported")
    else:
        log.debug("Creating Processor: {} with parent: {}".format(name, element.parent_path))
        tpe = nipyapi.nifi.models.DocumentedTypeDTO(type=element.config.package_id)
        p = nipyapi.canvas.create_processor(parent_pg, tpe, position, name, element.config)

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
    log.info("Create or update InputPort: {}".format(name))
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
    log.info("Create or update OutputPort: {}".format(name))
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


def _init_flow_meta_info(flow, desc):
    lib_version_pattern = re.compile(MATCH_LIB_VERSION)
    lib_version = lib_version_pattern.findall(desc)
    if lib_version:
        flow.lib_version = lib_version[0]


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


def _force_cleanup_reporting_tasks():
    """
    Delete all the ReportingTasks and ReportingTaskController services on the NiFi instance
    so that they can be re-deployed
    """
    log.info("Deleting reporting tasks...")
    # disable existing reporting tasks
    reporting_tasks = nipyapi.nifi.apis.flow_api.FlowApi().get_reporting_tasks().reporting_tasks
    _set_reporting_tasks_enabled(reporting_tasks, enabled=False)

    # fetch reporting tasks again to get the most recent revision
    reporting_tasks = nipyapi.nifi.apis.flow_api.FlowApi().get_reporting_tasks().reporting_tasks
    for task in reporting_tasks:
        nipyapi.nifi.ReportingTasksApi().remove_reporting_task(
            id=task.id,
            version=task.revision.version,
            client_id=task.revision.client_id
        )

    log.info("Deleting reporting task controllers...")
    # disable existing controllers
    controllers = nipyapi.nifi.apis.FlowApi().get_controller_services_from_controller().controller_services
    _set_controllers_enabled(controllers, enabled=False)

    # fetch controllers again to get the most recent revision
    controllers = nipyapi.nifi.apis.FlowApi().get_controller_services_from_controller().controller_services
    for controller in controllers:
        nipyapi.nifi.apis.ControllerServicesApi().remove_controller_service(
            id=controller.id,
            version=controller.revision.version,
            client_id=controller.revision.client_id
        )

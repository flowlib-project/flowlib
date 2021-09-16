# -*- coding: utf-8 -*-
import io
import os
import json
import yaml
import time
import re
import uuid

import nipyapi
import urllib3

import flowlib.layout
import flowlib.parser
from flowlib.logger import log
from flowlib.nifi.state import ZookeeperClient
from flowlib.exceptions import FlowLibException, FlowNotFoundException
from flowlib.model.deployment import FlowDeployment, DeployedComponent
from flowlib.model.flow import InputPort, OutputPort, RemoteProcessGroup, ProcessGroup, Processor


def get_nifi_rest_api_info():
    return nipyapi.nifi.apis.FlowApi().get_about_info()


def wait_for_nifi_api(nifi_endpoint, retries=12, delay=5):
    log.debug("Waiting for NiFi api to be ready at {}...".format(nifi_endpoint))

    i = 0
    while i < retries:
        if nipyapi.utils.is_endpoint_up("{}/nifi".format(nifi_endpoint)):
            nipyapi.config.nifi_config.host = "{}/nifi-api".format(nifi_endpoint)
            return
        i += 1
        time.sleep(delay)
    raise FlowLibException("Timeout reached while waiting for NiFi Rest API to be ready")


def get_previous_deployment(nifi_endpoint, flow_name):
    """
    Get the currently deployed flow and its components
      (including processor state) from a running NiFi instance
    :param nifi_endpoint: A NiFi api endpoint
    :type nifi_endpoint: str
    :param flow_name: The name of the flow PG to get
    :type flow_name: str
    :returns: flowlib.model.deployment.FlowDeployment
    """
    wait_for_nifi_api(nifi_endpoint)
    flow_pg = _find_flow_by_name(flow_name)

    queued = nipyapi.nifi.apis.FlowApi().get_process_group_status(flow_pg.id).process_group_status.aggregate_snapshot.flow_files_queued
    if queued > 0:
        log.warn("There are active flowfiles queued for this flow. Exporting or redeploying a flow with items enqueued may lead to dropped flowfiles")

    # load the deployment from the root PG comments
    try:
        deployment = FlowDeployment.from_dict(json.loads(flow_pg.component.comments))
    except Exception as e:
        log.error(e)
        raise FlowLibException("Failed to serialize the previously deployed Flow")

    # set state for flow canvas level stateful processors
    for k,v in deployment.stateful_processors.items():
        proc_id = v['processor_id']
        state = nipyapi.nifi.apis.ProcessorsApi().get_state(proc_id).component_state.cluster_state
        if state and state.total_entry_count > 0:
            deployment.stateful_processors[k]['state'] = { entry.key:entry.value for entry in state.state }
        else:
            log.info("Processor was specified as persisting state but no cluster state was found for {}, will not export state".format(proc_id))

    # set state for component level stateful processors
    for c in deployment.components:
        for k,v in c.stateful_processors.items():
            proc_id = v['processor_id']
            state = nipyapi.nifi.apis.ProcessorsApi().get_state(proc_id).component_state.cluster_state
            if state and state.total_entry_count > 0:
                c.stateful_processors[k]['state'] = { entry.key:entry.value for entry in state.state }
            else:
                log.info("Processor was specified as persisting state but no cluster state was found for {}, will not export state".format(proc_id))

    return deployment


def configure_flow_controller(nifi_endpoint, reporting_task_controllers, reporting_tasks,
    max_timer_driven_threads=None, max_event_driven_threads=None, force=False):
    """
    Deploy ReportingTasks and required controller services to NiFi via the Rest api
    :param nifi_endpoint: The NiFi api endpoint
    :type nifi_endpoint: str
    :param reporting_task_controllers: The controller services to deploy
    :type reporting_task_controllers: list(flowlib.model.Controller)
    :param reporting_tasks: The reporting tasks to depoy
    :type reporting_tasks: list(flowlib.model.ReportingTask)
    :param max_timer_driven_threads: The max number of concurrent timer driven processors that can be scheduled
    :type max_timer_driven_threads: int
    :param max_event_driven_threads: The max number of concurrent event driven processors that can be scheduled
    :type max_event_driven_threads: int
    """
    wait_for_nifi_api(nifi_endpoint)
    if force:
        _force_cleanup_reporting_tasks()

    # set max concurrent scheduling threads
    controller_config = nipyapi.nifi.apis.controller_api.ControllerApi().get_controller_config()
    if max_timer_driven_threads:
        controller_config.component.max_timer_driven_thread_count = max_timer_driven_threads
    if max_event_driven_threads:
        controller_config.component.max_event_driven_thread_count = max_event_driven_threads
    nipyapi.nifi.apis.controller_api.ControllerApi().update_controller_config(controller_config)

    # apply templating and create the reporting task controllers
    reporting_task_controllers = flowlib.parser.init_controllers(reporting_task_controllers)
    _create_reporting_task_controllers(reporting_task_controllers)

    # enable the new controller services
    controllers = nipyapi.nifi.apis.FlowApi().get_controller_services_from_controller().controller_services
    _set_controllers_enabled(controllers, enabled=True)

    # apply templating and create the reporting tasks
    reporting_tasks = flowlib.parser.init_reporting_tasks(reporting_task_controllers, reporting_tasks)
    _create_reporting_tasks(reporting_tasks)
    _set_reporting_tasks_enabled(reporting_tasks, enabled=True)


def nifi_export(config):
    endpoint = f'{config.nifi_endpoint}/nifi-api'
    nipyapi.utils.set_endpoint(endpoint)

    _pg = nipyapi.canvas.recurse_flow(pg_id=nipyapi.canvas.get_root_pg_id()).process_group_flow.to_dict()

    _pgs = [x for x in _pg["flow"]["process_groups"] if x["component"]["id"] == config.nifi_export][0]

    _pgsq = nipyapi.nifi.apis.process_groups_api.ProcessGroupsApi().get_process_group(_pgs["id"])

    _rf = nipyapi.canvas.recurse_flow(pg_id=config.nifi_export)

    nipyapi.utils.fs_write(nipyapi.utils.dump(_pgsq, mode=config.output_syntax), f"./processor-group.{config.output_syntax}")
    nipyapi.utils.fs_write(nipyapi.utils.dump(_rf.process_group_flow, mode=config.output_syntax), f"./skeleton-flow.{config.output_syntax}")


def nifi_import(config):
    endpoint = f'{config.nifi_endpoint}/nifi-api'
    nipyapi.utils.set_endpoint(endpoint)

    pgi = nipyapi.nifi.apis.process_groups_api.ProcessGroupsApi()

    _pg = nipyapi.utils.load(nipyapi.utils.fs_read(f"./processor-group.{config.output_syntax}"))

    _flow_content = nipyapi.utils.load(nipyapi.utils.fs_read(f"./skeleton-flow.{config.output_syntax}"))

    _pg["component"]["parentGroupId"] = nipyapi.canvas.get_root_pg_id()
    _pg["revision"]["version"] = 0
    del _pg["component"]["id"]

    splitEndpoint = _pg["uri"].split(":")
    endpoint2 = "/".join(splitEndpoint[2].split("/")[1:-1])
    endpoint1 = f'{splitEndpoint[0]}:{"/".join(splitEndpoint[1:-1])}:{config.nifi_endpoint.split(":")[2]}'
    newUri = f'{endpoint1}/{endpoint2}/{nipyapi.canvas.get_root_pg_id()}'
    _pg["uri"] = newUri

    try:
        _find_flow_by_name(_pg["status"]["aggregateSnapshot"]["name"])
    except FlowNotFoundException as e:
        pgi.create_process_group(id=nipyapi.canvas.get_root_pg_id(), body=_pg).to_dict()

def registry_import(ids, endpoint=None):
    nipyapi.config.registry_config.host = f'{endpoint}/nifi-registry-api'

    nipyapi.versioning.import_flow_version(
        bucket_id=ids[0],
        flow_id=ids[1],
        file_path="./registry-output.json"
    )

def registry_export(registry_options, endpoint=None):
    """
    Export a flow from a Nifi Registry via the Rest api
    :param buckets: Initialized Registry Bucket Query
    :param flow: Initialized Registry flow query
    """

    if endpoint is None:
        _flow_bucket_info = nipyapi.registry.apis.bucket_flows_api.BucketFlowsApi()
    else:
        nipyapi.config.registry_config.host = f'{endpoint}/nifi-registry-api'
        _flow_bucket_info = nipyapi.registry.apis.bucket_flows_api.BucketFlowsApi()

    _flow_data_info = _flow_bucket_info.get_flow(bucket_id=registry_options[0],
                                                 flow_id=registry_options[1])

    flow_content = json.loads(
        nipyapi.versioning.export_flow_version(mode="json", bucket_id=_flow_data_info.bucket_identifier,
                                               flow_id=_flow_data_info.identifier,
                                               version=None))
    del flow_content["bucket"]
    return flow_content


def deploy_flow(flow, config, deployment=None, force=False):
    """
    Deploy a Flow to NiFi via the Rest api
    :param flow: An initialized Flow instance
    :type flow: flowlib.model.flow.Flow
    :param config: A valid FlowLibConfig object
    :type config: FlowLibConfig
    :param deployment: If a deployment is specified, then we will use the state from
      the one provided instead of attempting to export the currently deployed flow first.
      This means that if there is state to be migrated, it must be included in the provided
      deployment because it will not be read from the currently deployed flow.
    :type deployment: FlowDeployment
    :param force: Whether to overwrite a previously deployed data flow
    :type force: bool
    """
    if not flow._is_initialized:
        raise FlowLibException("Flow has not yet been initialized. Call flow.initialize() first")
    if not flow._is_valid:
        raise FlowLibException("Flow has not yet been validated. Call flow.validate() first")

    wait_for_nifi_api(config.nifi_endpoint)
    previous_deployment = deployment
    try:
        # if a deployment was not provided, then check to see if the flow is already deployed
        # if it was provided and the flow already exists, then it will be overwritten if force is True
        if not previous_deployment:
            previous_deployment = get_previous_deployment(config.nifi_endpoint, flow.name)
    except FlowNotFoundException:
        pass

    # create a new FlowDeployment
    deployment = FlowDeployment(flow.raw)
    for component in flow._loaded_components.values():
        deployment.add_component(DeployedComponent(component.raw))

    canvas_root_id = nipyapi.canvas.get_root_pg_id()
    canvas_root_pg = nipyapi.canvas.get_process_group(canvas_root_id, identifier_type='id')
    log.info("Deploying {} to NiFi".format(flow.name))

    previous_flow_pg = None
    if previous_deployment:
        try:
            previous_flow_pg = _find_flow_by_name(flow.name)
        except FlowNotFoundException:
            pass
        if previous_flow_pg:
            log.info("Found ProcessGroup of previously deployed flow: {}".format(previous_flow_pg.id))
        if previous_flow_pg and deployment:
            log.info("An explicit FlowDeployment was provided for this deployment so any existing state will be overwritten if the --force flag is true")

    flow_pg = None
    try:
        if previous_flow_pg and not force:
             raise FlowLibException("A flow with that name already exists, use the --force option to overwrite it")

        # create a PG for the new flow
        flow_pg_element = ProcessGroup(name="(deploying) {}".format(flow.name), _type="process_group", _parent_path=flow.name)
        flow_pg = _create_process_group(flow_pg_element, canvas_root_pg, flowlib.layout.TOP_LEVEL_PG_LOCATION, deployment, is_flow_root=True)
        flow.id = flow_pg.id

        _create_controllers(flow, flow_pg)
        # we have to wait until the controllers exist in NiFi before applying jinja templating
        # because the controller() jinja helper needs to lookup controller IDs for injecting into the processor's properties
        flowlib.parser.replace_flow_element_vars_recursive(flow, flow._elements, flow.components)

        _create_canvas_elements_recursive(flow._elements, flow_pg, config, deployment, previous_deployment)
        #
        _create_connections_recursive(flow, flow._elements)
        _set_controllers_enabled(flow._controllers, enabled=True)

        if previous_flow_pg and force:
            _remove_flow(previous_flow_pg.id, force=force)

    except:
        # rename new flow to failed and re-raise the exception
        if flow_pg:
            _rename_process_group("(failed) {}".format(flow.name), flow_pg.id)
        raise

    # we finished creating the new flow without errors so replace the old one
    _rename_process_group(flow.name, flow_pg.id)

    # find all deployed flows and re-organize the top level PGs
    pgs = nipyapi.nifi.ProcessGroupsApi().get_process_groups(canvas_root_id).process_groups
    log.info("Found {} deployed flows, updating top level canvas layout.".format(len(pgs)))
    pgs = sorted(pgs, key=lambda e: e.component.name)
    positions = flowlib.layout.generate_top_level_pg_positions(pgs)
    for pg in pgs:
        pg.component.position = positions.get(pg.component.name, flowlib.layout.DEFAULT_POSITION)
        log.info("Setting position for {} to {}".format(pg.component.name, pg.position))
        nipyapi.nifi.apis.ProcessGroupsApi().update_process_group(pg.id, pg)

    # re-fetch the deployed flow PG
    flow_pg = nipyapi.canvas.get_process_group(flow_pg.id, identifier_type='id')

    # write deployment to buffer
    s = io.StringIO()
    deployment.save(s)

    # save in NiFi instance PG comments
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
    elif kind == 'remote_process_group':
        e = nipyapi.nifi.RemoteProcessGroupsApi().get_remote_process_group(identifier)
    else:
        raise FlowLibException("{} is not a valid NiFi api type")
    return e


def _rename_process_group(name, pg_id):
    """
    Rename an existing process group
    :param name: The new name for the ProcessGroup
    :type name: str
    :param pg_id: The NiFi uuid of the process group
    :type pg_id: str
    """
    flow_pg = nipyapi.canvas.get_process_group(pg_id, identifier_type='id')
    if not flow_pg:
        raise FlowLibException("Failed to rename process group. No process group found with id {}".format(pg_id))
    flow_pg.component.name = name
    nipyapi.nifi.apis.ProcessGroupsApi().update_process_group(flow_pg.id, flow_pg)


def _create_controllers(flow, flow_pg):
    """
    Create the controller services for the flow
    :param flow: A Flow instance
    :type flow: flowlib.model.flow.Flow
    :param flow_pg: The process group of the root flow being deployed
    :type flow_pg: nipyapi.nifi.models.process_group_entity.ProcessGroupEntity
    """
    all_controller_types = list(map(lambda x: x.type, nipyapi.canvas.list_all_controller_types()))
    for c in flow._controllers:
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


def _create_canvas_elements_recursive(elements, parent_pg, config, current_deployment, previous_deployment=None):
    """
    Recursively creates the actual NiFi elements (process_groups, processors, inputs, outputs) on the canvas
    :param elements: The elements to deploy
    :type elements: list(model.FlowElement)
    :param parent_pg: The process group in which to create the processors
    :type parent_pg: nipyapi.nifi.models.process_group_entity.ProcessGroupEntity
    :param config: A valid FlowLibConfig object
    :type config: FlowLibConfig
    :param current_deployment: The current flow deployment
    :type current_deployment: flowlib.model.deployment.FlowDeployment
    :param previous_deployment: The previous flow deployment
    :type previous_deployment: flowlib.model.deployment.FlowDeployment or None
    """

    # Generate a dictionary of {name: (x,y)} positions for each element
    positions = flowlib.layout.generate_layout(elements)

    for el in elements.values():
        position = positions[el.name]
        if isinstance(el, ProcessGroup):
            pg = _create_process_group(el, parent_pg, position, current_deployment)
            _create_canvas_elements_recursive(el._elements, pg, config, current_deployment, previous_deployment)
        elif isinstance(el, Processor):
            _create_processor(el, parent_pg, position, config, current_deployment, previous_deployment)
        elif isinstance(el, RemoteProcessGroup):
            _create_remote_process_group(el, parent_pg, position)
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
            _create_connections_recursive(flow, el._elements)
        elif el.type in ['input_port', 'output_port', 'remote_process_group', 'processor']:
            _create_element_connections(flow, el)
        else:
            raise FlowLibException("Unsupported Element Type: {}".format(el.type))


def _create_remote_process_group(element, parent_pg, position):
    """
    Create a Remote Process Group on the NiFi canvas
    :param element: The Remote Process Group to deploy
    :type element: flowlib.model.flow.RemoteProcessGroup
    :param parent_pg: The process group in which to create the new remote process group
    :type parent_pg: nipyapi.nifi.models.process_group_entity.ProcessGroupEntity
    """
    element.config.name = element.name
    rpg = nipyapi.nifi.apis.ProcessGroupsApi().create_remote_process_group(
        id=parent_pg.id,
        body=nipyapi.nifi.RemoteProcessGroupEntity(
            revision={'version': 0},
            component=element.config
        )
    )
    element.id = rpg.id
    element.parent_id = parent_pg.id


def _create_process_group(element, parent_pg, position, current_deployment, is_flow_root=False):
    """
    Create a Process Group on the NiFi canvas
    :param element: The Process Group to deploy
    :type element: model.ProcessGroup
    :param parent_pg: The process group in which to create the new process group
    :type parent_pg: nipyapi.nifi.models.process_group_entity.ProcessGroupEntity
    :param is_flow_root: Whether the PG being created is the root of a flow being deployed
    :type is_flow_root: bool
    :param current_deployment: The current flow deployment
    :type current_deployment: flowlib.model.deployment.FlowDeployment
    :param previous_deployment: The previous flow deployment
    :type previous_deployment: flowlib.model.deployment.FlowDeployment or None
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
            current_deployment.root_group_id = pg.id

    element.id = pg.id
    element.parent_id = parent_pg.id
    return pg


def _create_processor(element, parent_pg, position, config, current_deployment, previous_deployment=None):
    """
    Create a Processor on the NiFi canvas
    :param element: The Processor to deploy
    :type element: model.Processor
    :param parent_pg: The process group in which to create the new processor
    :type parent_pg: nipyapi.nifi.models.process_group_entity.ProcessGroupEntity
    :param config: A valid FlowLibConfig object
    :type config: FlowLibConfig
    :param current_deployment: The current flow deployment
    :type current_deployment: flowlib.model.deployment.FlowDeployment
    :param previous_deployment: The previous flow deployment
    :type previous_deployment: flowlib.model.deployment.FlowDeployment or None
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

        # If the processor is marked as stateful, add it to the deployment's stateful_processors
        # and migrate the NiFi state if a previous_deployment is provided
        if p.component.persists_state:
            state = None
            if element.src_component_name == 'root':
                current_deployment.stateful_processors[element.name] = {'processor_id': p.id}
                if previous_deployment:
                    state = previous_deployment.stateful_processors.get(element.name, {}).get('state')
            else:
                component_path = element.parent_path + "/" + element.name
                deployed_component = current_deployment.get_component(element.src_component_name)
                deployed_component.stateful_processors[component_path] = {
                    "group_id": parent_pg.id,
                    "processor_id": p.id
                }
                if previous_deployment:
                    previous_component = previous_deployment.get_component(element.src_component_name)
                    if previous_component:
                        state = previous_component.stateful_processors.get(component_path, {}).get('state')

            if state:
                log.info("Migrating processor state: {}".format(element.name))
                client = ZookeeperClient(config.zookeeper_connection, config.zookeeper_root_node, config.zookeeper_acl)
                client.set_processor_state(p.id, state)
            else:
                log.info("Processor {} is marked as stateful but no previous state was found, nothing to migrate...".format(element.name))

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


def _create_element_connections(flow, source_element):
    """
    Create the downstream connections for the element on the NiFi canvas
    :param flow: The Flow to create connections in
    :type flow: Flow
    :param source_element: The source FlowElement to connect to its downstreams
    :type source_element: FlowElement
    """
    log.info("Creating downstream connections for element: {}/{}".format(source_element.parent_path, source_element.name))
    parent = flow.get_parent_element(source_element)

    # If source is an output_port then the downstream connections are the parent's connections
    if isinstance(source_element, OutputPort):
        # We're only interested in connections from the current output port
        if parent.connections:
            connections = [c for c in parent.connections if c.from_port == source_element.name]
        else:
            connections = None
    else:
        connections = source_element.connections

    if connections:
        for c in connections:
            if isinstance(source_element, (InputPort, Processor, RemoteProcessGroup)):
                elements = parent._elements
            elif isinstance(source_element, OutputPort):
                # if source is an output port then we need to to search the
                # parent's elements for the destination element
                elements = flow.get_parent_element(parent)._elements
            else:
                raise FlowLibException("""
                    Something went wrong, failed while recursively connecting flow elements on the canvas.
                    Cannot create downstream connections for elements of type {}""".format(type(source_element)))

            source = _get_nifi_entity_by_id(source_element.type, source_element.id)
            source_id = source.component.id
            source_group_id = source.component.parent_group_id

            dest_element = elements.get(c.name)
            if not dest_element:
                raise FlowLibException("The destination element {} is not defined, must be one of: {}".format(c.name, elements.keys()))

            if isinstance(dest_element, (OutputPort, Processor, RemoteProcessGroup)):
                dest = _get_nifi_entity_by_id(dest_element.type, dest_element.id)
            elif isinstance(dest_element, ProcessGroup):
                d = [v for k,v in dest_element._elements.items() if isinstance(v, InputPort) and k == c.to_port][0]
                dest = _get_nifi_entity_by_id(d.type, d.id)
            else:
                raise FlowLibException("""Connections cannot be defined for downstream elements of type 'input_port'.
                  InputPorts can only be referenced from outside of the current component""")

            dest_id = dest.component.id
            dest_group_id = dest.component.parent_group_id

            # if source or dest are a RPG then we need the IDs of the target input or output
            # ports from the remote instance
            if isinstance(source, nipyapi.nifi.RemoteProcessGroupEntity):
                source_type = 'REMOTE_OUTPUT_PORT'
                target = [op for op in source.component.contents.output_ports if op.name == c.from_port]
                if len(target) != 1:
                    raise FlowLibException("Output port {} not found. Found: {}".format(c.from_port, [op.name for op in dest.component.contents.output_ports]))
                source_id = target[0].id
                source_group_id = target[0].group_id
            else:
                source_type = nipyapi.utils.infer_object_label_from_class(source)

            if isinstance(dest, nipyapi.nifi.RemoteProcessGroupEntity):
                dest_type = 'REMOTE_INPUT_PORT'
                target = [ip for ip in dest.component.contents.input_ports if ip.name == c.to_port]
                if len(target) != 1:
                    raise FlowLibException("Input port {} not found. Found: {}".format(c.to_port, [ip.name for ip in dest.component.contents.input_ports]))
                dest_id = target[0].id
                dest_group_id = target[0].group_id
            else:
                dest_type = nipyapi.utils.infer_object_label_from_class(dest)

            # if the source of the connection is an output port then the group_id for the connection is the id of
            # the parent group of the group which contains the output port
            if isinstance(source_element, OutputPort):
                group_id = flow.get_parent_element(parent).id
            else:
                group_id = source_element.parent_id

            log.debug("Creating connection between source {} and dest {} for relationships {}".format(source.component.name, dest.component.name, c.relationships))

            nipyapi.nifi.ProcessGroupsApi().create_connection(
                id=group_id,
                body=nipyapi.nifi.ConnectionEntity(
                    revision=nipyapi.nifi.RevisionDTO(version=0),
                    source_type=source_type,
                    destination_type=dest_type,
                    component=nipyapi.nifi.ConnectionDTO(
                        source=nipyapi.nifi.ConnectableDTO(
                            id=source_id,
                            group_id=source_group_id,
                            type=source_type
                        ),
                        back_pressure_data_size_threshold=c.back_pressure_data_size_threshold,
                        back_pressure_object_threshold=c.back_pressure_object_threshold,
                        load_balance_strategy=c.load_balance_strategy,
                        flow_file_expiration=c.flow_file_expiration,
                        load_balance_compression=c.load_balance_compression,
                        prioritizers=c.prioritizers,
                        name=c.name,
                        destination=nipyapi.nifi.ConnectableDTO(
                            id=dest_id,
                            group_id=dest_group_id,
                            type=dest_type
                        ),
                        selected_relationships=c.relationships
                    )
                )
            )
    else:
        log.debug("Terminal node, no downstream connections found for element {}".format(source_element.name))


def _remove_flow(flow_pg_id, force=False):
    """
    Delete a deployed Flow from the NiFi canvas so that flows can be re-deployed
    :param flow_pg_id: The id of the Flow's ProcessGroup
    :type flow_pg_id: str
    """
    # TODO: Warn on running processors or queued flowfiles ??

    log.info("Stopping processors...")
    nipyapi.canvas.schedule_process_group(flow_pg_id, False)

    log.info("Deleting flow connections...")
    connections = nipyapi.canvas.list_all_connections(pg_id=flow_pg_id, descendants=True)
    for c in connections:
        nipyapi.canvas.delete_connection(c, purge=force)

    log.info("Deleting flow controller services...")
    controllers = nipyapi.canvas.list_all_by_kind('controllers', pg_id=flow_pg_id, descendants=False)
    if controllers and not isinstance(controllers, list):
        controllers = [controllers]
    for c in controllers:
        nipyapi.canvas.delete_controller(c, force=force)

    log.info("Deleting flow process group...")
    flow_pg = _get_nifi_entity_by_id('process_group', flow_pg_id)
    nipyapi.canvas.delete_process_group(flow_pg, force=force)


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


def _find_flow_by_name(name):
    """
    Returns the ProcessGroupEntity of the flow
    :raises: FlowLibException if multiple flows with that name are found
    :raises: FlowNotFoundException if no flow is found with that name
    """
    flow_pg = nipyapi.canvas.get_process_group(name, identifier_type='name')
    if isinstance(flow_pg, list):
        pgs = [pg for pg in flow_pg if pg.component.name == name]
        if len(pgs) > 1:
            raise FlowLibException("Found multiple Flow ProcessGroups named {}".format(name))
        elif len(pgs) == 0:
            raise FlowNotFoundException("No flow ProcessGroup named {} is deployed".format(name))
        else:
            flow_pg = pgs[0]

    if not flow_pg or flow_pg.component.name != name:
        raise FlowNotFoundException("No flow named {} is deployed".format(name))

    return flow_pg

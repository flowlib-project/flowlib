# -*- coding: utf-8 -*-
import os
import yaml

import jinja2
import nipyapi.nifi
import nipyapi.canvas
from tabulate import tabulate

from flowlib.layout import TOP_LEVEL_PG_LOCATION
from flowlib.model import FlowLibException
from flowlib.model.flow import Processor, ControllerService, ReportingTask
from flowlib.logger import log
import flowlib.nifi.rest


def generate_docs(config, dest, force=False):
    """
    Use the configured NiFi api endpoint to generate html docs containing example YAML definitions for the available
      processors, controller service, and reporting tasks
    :type config: FlowLibConfig
    :param dest: The destination directory to create the flowlib documentation
    :type dest: str
    """
    if os.path.exists(dest):
        log.warn("Destination directory {} already exists. Will not update static descriptors...".format(dest))

    flowlib.nifi.rest.wait_for_nifi_api(config.nifi_endpoint)

    reporting_task_doc_dir = os.path.join(dest, 'reporting-tasks')
    controllers_doc_dir = os.path.join(dest, 'controllers')
    processors_doc_dir = os.path.join(dest, 'processors')

    # list the available component types using the NiFi api
    reporting_tasks = _get_available_component_package_ids('reporting-tasks')
    controller_services = _get_available_component_package_ids('controllers')
    processors = _get_available_component_package_ids('processors')

    # get the component document descriptors from the NiFi api
    root_id = nipyapi.canvas.get_root_pg_id()
    root_pg = nipyapi.canvas.get_process_group(root_id, identifier_type='id')

    mode='x' # skip files that already exist
    if force: # otherwise set mode to 'w' and overwrite all descriptors
        mode='w'

    _gen_reporting_task_doc_descriptors(reporting_task_doc_dir, reporting_tasks, mode)
    _gen_controller_service_doc_descriptors(controllers_doc_dir, controller_services, root_pg, mode)
    _gen_processor_doc_descriptors(processors_doc_dir, processors, root_pg, mode)
    _gen_doc_html(dest)


def _get_available_component_package_ids(component_type):
    """
    List the available component package ids from an existing NiFi instance
    :type component_type: str
    """
    if component_type == 'processors':
        results = nipyapi.nifi.apis.flow_api.FlowApi().get_processor_types().processor_types
    elif component_type == 'controllers':
        results = nipyapi.nifi.apis.flow_api.FlowApi().get_controller_service_types().controller_service_types
    elif component_type == 'reporting-tasks':
        results = nipyapi.nifi.apis.flow_api.FlowApi().get_reporting_task_types().reporting_task_types
    else:
        raise FlowLibException("Invalid component_type")

    return [t.type for t in results]


def _gen_reporting_task_doc_descriptors(doc_dir, reporting_tasks, mode='x'):
    os.makedirs(doc_dir, exist_ok=True)
    for rt in reporting_tasks:
        try:
            # write props to doc file
            with open('{}.{}'.format(os.path.join(doc_dir, rt), 'yaml'), mode) as f:
                # create temp reporting task
                task = nipyapi.nifi.ControllerApi().create_reporting_task(
                    body=nipyapi.nifi.ReportingTaskEntity(
                        revision={'version': 0},
                        component=nipyapi.nifi.ReportingTaskDTO(
                            type=rt,
                            name='doc-temp'
                        )
                    )
                )
                # delete the temp reporting task
                nipyapi.nifi.ReportingTasksApi().remove_reporting_task(
                    id=task.id,
                    version=task.revision.version,
                    client_id=task.revision.client_id
                )
                f.write(yaml.safe_dump({ k:v.to_dict() for k,v in task.component.descriptors.items() }))
        except FileExistsError:
            log.warn("Reporting task descriptors already exist for {}, skipping...".format(rt))


def _gen_controller_service_doc_descriptors(doc_dir, controller_services, root_pg, mode='x'):
    os.makedirs(doc_dir, exist_ok=True)
    for cs in controller_services:
        try:
            # write props to doc file
            with open('{}.{}'.format(os.path.join(doc_dir, cs), 'yaml'), mode) as f:
                # create temp controller service in root pg
                controller_type = nipyapi.nifi.models.DocumentedTypeDTO(type=cs)
                controller = nipyapi.canvas.create_controller(root_pg, controller_type, name='doc-temp')
                # delete the temp controller service
                nipyapi.canvas.delete_controller(controller, force=True)
                f.write(yaml.safe_dump({ k:v.to_dict() for k,v in controller.component.descriptors.items() }))
        except FileExistsError:
            log.warn("Controller service descriptors already exist for {}, skipping...".format(cs))


def _gen_processor_doc_descriptors(doc_dir, processors, root_pg, mode='x'):
    os.makedirs(doc_dir, exist_ok=True)
    for p in processors:
        try:
            # write props to doc file
            with open('{}.{}'.format(os.path.join(doc_dir, p), 'yaml'), mode) as f:
                # create temp processor in root pg
                processor_type = nipyapi.nifi.models.DocumentedTypeDTO(type=p)
                processor = nipyapi.canvas.create_processor(root_pg, processor_type, TOP_LEVEL_PG_LOCATION, name='doc-temp')
                # delete the temp processor
                nipyapi.canvas.delete_processor(processor, force=True)
                f.write(yaml.safe_dump({ k:v.to_dict() for k,v in processor.component.config.descriptors.items() }))
        except FileExistsError:
            log.warn("Processor descriptors already exist for {}, skipping...".format(p))


def _gen_doc_html(doc_dir):
    log.info("Generating html helper docs at {}".format(doc_dir))
    context = {
        'flowlib_info': {
            'version': flowlib.__version__,
            'nifi_version': flowlib.nifi.rest.get_nifi_rest_api_info().about
        },
        'reporting_tasks': [],
        'controller_services': [],
        'processors': []
    }
    reporting_task_doc_dir = os.path.join(doc_dir, 'reporting-tasks')
    controllers_doc_dir = os.path.join(doc_dir, 'controllers')
    processors_doc_dir = os.path.join(doc_dir, 'processors')

    # create jinja templates
    env = jinja2.Environment()
    with open(os.path.abspath(os.path.join(os.path.dirname(__file__), '../templates/index.html')), 'r') as f:
        index_html_template = env.from_string(f.read())
    with open(os.path.abspath(os.path.join(os.path.dirname(__file__), '../templates/descriptors.html')), 'r') as f:
        descriptors_html_template = env.from_string(f.read())
    with open(os.path.abspath(os.path.join(os.path.dirname(__file__), '../templates/example.html')), 'r') as f:
        example_html_template = env.from_string(f.read())

    # generate reporting task docs
    for rt in [ f for f in os.listdir(reporting_task_doc_dir) if f.endswith('.yaml') ]:
        with open(os.path.join(reporting_task_doc_dir, rt)) as f:
            rt = rt[:-5] # trim .yaml extension
            descriptors = yaml.safe_load(f)
            example = _create_example_yaml_from_descriptors('reporting_task', rt, descriptors)
            context['reporting_tasks'].append(rt)

        with open(os.path.join(reporting_task_doc_dir, rt + '.descriptors.html'), 'w') as f:
            f.write(descriptors_html_template.render(key=rt, descriptors=descriptors,
                flowlib_info=context['flowlib_info']))
        with open(os.path.join(reporting_task_doc_dir, rt + '.example.html'), 'w') as f:
            f.write(example_html_template.render(key=rt, example=example,
                flowlib_info=context['flowlib_info']))

    # generate controller service docs
    for cs in [ f for f in os.listdir(controllers_doc_dir) if f.endswith('.yaml') ]:
        with open(os.path.join(controllers_doc_dir, cs)) as f:
            cs = cs[:-5] # trim .yaml extension
            descriptors = yaml.safe_load(f)
            example = _create_example_yaml_from_descriptors('controller_service', cs, descriptors)
            context['controller_services'].append(cs)

        with open(os.path.join(controllers_doc_dir, cs + '.descriptors.html'), 'w') as f:
            f.write(descriptors_html_template.render(key=cs, descriptors=descriptors,
                flowlib_info=context['flowlib_info']))
        with open(os.path.join(controllers_doc_dir, cs + '.example.html'), 'w') as f:
            f.write(example_html_template.render(key=cs, example=example,
                flowlib_info=context['flowlib_info']))

    # generate processor docs
    for p in [ f for f in os.listdir(processors_doc_dir) if f.endswith('.yaml') ]:
        with open(os.path.join(processors_doc_dir, p)) as f:
            p = p[:-5] # trim .yaml extension
            descriptors = yaml.safe_load(f)
            example = _create_example_yaml_from_descriptors('processor', p, descriptors)
            context['processors'].append(p)

        with open(os.path.join(processors_doc_dir, p + '.descriptors.html'), 'w') as f:
            f.write(descriptors_html_template.render(key=p, descriptors=descriptors,
                flowlib_info=context['flowlib_info']))
        with open(os.path.join(processors_doc_dir, p + '.example.html'), 'w') as f:
            f.write(example_html_template.render(key=p, example=example,
                flowlib_info=context['flowlib_info']))

    with open(os.path.join(doc_dir, 'index.html'), 'w') as f:
        f.write(index_html_template.render(**context))


def _create_example_yaml_from_descriptors(component_type, package_id, descriptors):
    component = dict()
    if component_type == 'processor':
        component['name'] = 'Sample Processor'
        component['type'] = 'processor'
    elif component_type == 'controller_service':
        component['name'] = 'Sample Controller Service'
    elif component_type == 'reporting_task':
        component['name'] = 'Sample Reporting Task'

    component['config'] = dict()
    component['config']['package_id'] = package_id
    component['config']['properties'] = dict()
    for desc in descriptors.values():
        if desc['required']:
            component['config']['properties'][desc['name']] = desc.get('default_value')

    return yaml.safe_dump([component], default_flow_style=False, sort_keys=False)


def list_components(doc_dir, component_type):
    """
    List the available components for a given component_type
    :param component_type: One of [processors, controllers, reporting-tasks]
    :type component_type: str
    """
    if component_type not in ['processors', 'controllers', 'reporting-tasks']:
        raise FlowLibException("Invalid component type: {}. Must be one of ('processors', 'controllers', 'reporting-tasks')".format(component_type))

    component_dir = os.path.join(doc_dir, component_type)
    if not os.path.exists(component_dir) or not os.path.isdir(component_dir):
        log.error("Run 'flowlib --generate-docs {}' to use this command".format(doc_dir))
        raise FlowLibException("Docs directory {} does not exist".format(doc_dir))

    print('\n'.join([ c[:-5] for c in os.listdir(component_dir) if c.endswith('.yaml') ]))


def describe_component(doc_dir, component_type, package_id):
    """
    Describe available properties for a given component
    :param component_type: One of [processor, controller, reporting-task]
    :type component_type: str
    :type package_id: str
    """
    if component_type not in ['processor', 'controller', 'reporting-task']:
        raise FlowLibException("Invalid component type: {}. Must be one of ('processor', 'controller', 'reporting-task')".format(component_type))

    component_dir = os.path.join(doc_dir, "{}s".format(component_type))
    desc = os.path.join(component_dir, "{}.yaml".format(package_id))
    if not os.path.exists(desc) or not os.path.isfile(desc):
        log.error("Run 'flowlib --generate-docs {}' to use this command".format(doc_dir))
        raise FlowLibException("Component descriptor {} does not exist".format(desc))

    with open(desc, 'r') as f:
        descriptor = yaml.safe_load(f)

    headers = ['Name', 'Default', 'Allowable Values', 'Required', 'Sensitive', 'Supports EL', 'Description']
    items = list()
    for d in descriptor.values():
        name = d.get('name')
        default = d.get('default_value', '')
        values = d.get('allowable_values') or list()
        allowable_values = ','.join(list(map(lambda v: v['allowable_value']['value'], values)))
        required = d.get('required')
        sensitive = d.get('sensitive')
        supports_el = d.get('supports_el')
        description = d.get('description')
        field = [name, default, allowable_values, required, sensitive, supports_el, description]
        items.append(field)

    print(tabulate(items, headers=headers, stralign="left", tablefmt="psql"))

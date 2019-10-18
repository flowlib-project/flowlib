# -*- coding: utf-8 -*-
import os
import yaml

import jinja2
import nipyapi.nifi
import nipyapi.canvas

from flowlib.layout import TOP_LEVEL_PG_LOCATION
from flowlib.model import FlowLibException
from flowlib.logger import log
import flowlib.nifi.rest

### TODO: Write nifi and flowlib version info
### TODO: Suppress info logs during doc generation
### TODO: Fix CLI flags for --list and --describe (use static yaml or prompt user to create it)
### TODO: Implement --force cli option to overwrite output
### TODO: Finish example yaml page with copy to clipboard button
### TODO: Add buttons for 'descriptors' and 'example' from index.html

def generate_docs(config, dest):
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

    reporting_task_doc_dir = os.path.join(dest, 'reporting_tasks')
    controllers_doc_dir = os.path.join(dest, 'controllers')
    processors_doc_dir = os.path.join(dest, 'processors')

    # list the available component types using the NiFi api
    reporting_tasks = _get_available_component_package_ids(config.nifi_endpoint, 'reporting-tasks')
    controller_services = _get_available_component_package_ids(config.nifi_endpoint, 'controllers')
    processors = _get_available_component_package_ids(config.nifi_endpoint, 'processors')

    # get the component document descriptors from the NiFi api
    root_id = nipyapi.canvas.get_root_pg_id()
    root_pg = nipyapi.canvas.get_process_group(root_id, identifier_type='id')
    _gen_reporting_task_doc_descriptors(reporting_task_doc_dir, reporting_tasks)
    _gen_controller_service_doc_descriptors(controllers_doc_dir, controller_services, root_pg)
    _gen_processor_doc_descriptors(processors_doc_dir, processors, root_pg)
    _gen_doc_html(dest)


def _get_available_component_package_ids(nifi_endpoint, component_type):
    """
    List the available component package ids using the provided NiFi endpoint
    :param nifi_endpoint: A NiFi api endpoint
    :type nifi_endpoint: str
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


def _gen_reporting_task_doc_descriptors(doc_dir, reporting_tasks):
    if os.path.exists(doc_dir):
        log.warn("Reporting task descriptors already exist in {}, skipping...".format(doc_dir))
    else:
        os.makedirs(doc_dir)
        for rt in reporting_tasks:
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
            # write props to doc file
            with open('{}.{}'.format(os.path.join(doc_dir, rt), 'yaml'), 'x') as f:
                f.write(yaml.safe_dump({ k:v.to_dict() for k,v in task.component.descriptors.items() }))
            # delete the temp reporting task
            nipyapi.nifi.ReportingTasksApi().remove_reporting_task(
                id=task.id,
                version=task.revision.version,
                client_id=task.revision.client_id
            )


def _gen_controller_service_doc_descriptors(doc_dir, controller_services, root_pg):
     if os.path.exists(doc_dir):
        log.warn("Controller service descriptors already exist in {}, skipping...".format(doc_dir))
     else:
        os.makedirs(doc_dir, exist_ok=True)
        for cs in controller_services:
            # create temp controller service in root pg
            controller_type = nipyapi.nifi.models.DocumentedTypeDTO(type=cs)
            controller = nipyapi.canvas.create_controller(root_pg, controller_type, name='doc-temp')
            # write props to doc file
            with open('{}.{}'.format(os.path.join(doc_dir, cs), 'yaml'), 'x') as f:
                f.write(yaml.safe_dump({ k:v.to_dict() for k,v in controller.component.descriptors.items() }))
            # delete the temp controller service
            nipyapi.canvas.delete_controller(controller, force=True)


def _gen_processor_doc_descriptors(doc_dir, processors, root_pg):
    if os.path.exists(doc_dir):
        log.warn("Processor descriptors already exist in {}, skipping...".format(doc_dir))
    else:
        os.makedirs(doc_dir, exist_ok=True)
        for p in processors:
            # create temp processor in root pg
            processor_type = nipyapi.nifi.models.DocumentedTypeDTO(type=p)
            processor = nipyapi.canvas.create_processor(root_pg, processor_type, TOP_LEVEL_PG_LOCATION, name='doc-temp')
            # write props to doc file
            with open('{}.{}'.format(os.path.join(doc_dir, p), 'yaml'), 'x') as f:
                f.write(yaml.safe_dump({ k:v.to_dict() for k,v in processor.component.config.descriptors.items() }))
            # delete the temp processor
            nipyapi.canvas.delete_processor(processor, force=True)


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
    reporting_task_doc_dir = os.path.join(doc_dir, 'reporting_tasks')
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
            example = _create_example_from_descriptors(descriptors)
            context['reporting_tasks'].append(rt)

        with open(os.path.join(reporting_task_doc_dir, rt + '.descriptors.html'), 'w') as f:
            f.write(descriptors_html_template.render(component_type='Reporting Task',
                key=rt, descriptors=descriptors, flowlib_info=context['flowlib_info']))
        with open(os.path.join(controllers_doc_dir, rt + '.example.html'), 'w') as f:
            f.write(example_html_template.render(component_type='Reporting Task',
                key=rt, example=example, flowlib_info=context['flowlib_info']))

    # generate controller service docs
    for cs in [ f for f in os.listdir(controllers_doc_dir) if f.endswith('.yaml') ]:
        with open(os.path.join(controllers_doc_dir, cs)) as f:
            cs = cs[:-5] # trim .yaml extension
            descriptors = yaml.safe_load(f)
            example = _create_example_from_descriptors(descriptors)
            context['controller_services'].append(cs)

        with open(os.path.join(controllers_doc_dir, cs + '.descriptors.html'), 'w') as f:
            f.write(descriptors_html_template.render(component_type='Controller Service',
                key=cs, descriptors=descriptors, flowlib_info=context['flowlib_info']))
        with open(os.path.join(controllers_doc_dir, cs + '.example.html'), 'w') as f:
            f.write(example_html_template.render(component_type='Controller Service',
                key=cs, example=example, flowlib_info=context['flowlib_info']))

    # generate processor docs
    for p in [ f for f in os.listdir(processors_doc_dir) if f.endswith('.yaml') ]:
        with open(os.path.join(processors_doc_dir, p)) as f:
            p = p[:-5] # trim .yaml extension
            descriptors = yaml.safe_load(f)
            example = _create_example_from_descriptors(descriptors)
            context['processors'].append(p)

        with open(os.path.join(processors_doc_dir, p + '.descriptors.html'), 'w') as f:
            f.write(descriptors_html_template.render(component_type='Processor',
                key=p, descriptors=descriptors, flowlib_info=context['flowlib_info']))
        with open(os.path.join(processors_doc_dir, p + '.example.html'), 'w') as f:
            f.write(example_html_template.render(component_type='Processor',
                key=p, example=example, flowlib_info=context['flowlib_info']))

    with open(os.path.join(doc_dir, 'index.html'), 'w') as f:
        f.write(index_html_template.render(**context))


def _create_example_from_descriptors(descriptors):
    return ''


def describe_component(nifi_endpoint, component_type, package_id):
    """
    Describe available properties for a given component
    :param nifi_endpoint: A NiFi api endpoint
    :type nifi_endpoint: str
    :type component_type: str
    :type package_id: str
    """
    # TODO:

    # wait_for_nifi_api(nifi_endpoint)
    # if component_type == 'processor':
    #     config = nipyapi.nifi.apis.flow_api.FlowApi().get_processor_types(type=package_id).processor_types
    # elif component_type == 'controller':
    #     config = nipyapi.nifi.apis.flow_api.FlowApi().get_controller_service_types(type_filter=package_id).controller_service_types
    # elif component_type == 'reporting-task':
    #     config = nipyapi.nifi.apis.flow_api.FlowApi().get_reporting_task_types(type=package_id).reporting_task_types
    # else:
    #     raise FlowLibException("Invalid component_type")

    # print(yaml.dump(config))

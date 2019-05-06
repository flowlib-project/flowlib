# -*- coding: utf-8 -*-
import logging
import copy
import os
import yaml

import jinja2
from jinja2 import Environment

import flowlib
from flowlib.model import (FlowLibException, FlowComponent, FlowElement,
    Processor, ProcessGroup)

def _env_var(value, key):
    return os.getenv(key, value)
env = Environment()
env.filters['env_var'] = _env_var


def init_from_file(flow, _file, component_dir):
    """
    Initialize a Flow from from a yaml definition
    :param flow: An unitialized Flow instance
    :type flow: flowlib.model.Flow
    :param f: A File object
    :type f: io.TextIOWrapper
    """
    raw = yaml.safe_load(_file)
    flow.flowlib_version = flowlib.__version__
    flow.flowlib_release = flowlib.__git_version__
    flow.name = raw.get('name')
    flow.version = str(raw.get('version'))
    flow.controllers = raw.get('controllers')
    flow.canvas = raw.get('canvas')
    flow.comments = raw.get('comments', '')

    # If --component-dir is specified, use that. Otherwise use
    # the components/ directory relative to flow.yaml
    if component_dir:
        flow.component_dir = os.path.abspath(component_dir)
    else:
        flow.component_dir = os.path.abspath(os.path.join(os.path.dirname(_file.name), 'components'))

    logging.info("Loading component lib: {}".format(flow.component_dir))
    _load_components(flow.component_dir, flow)

    logging.info("Initializing root Flow {} from file {}".format(flow.name, _file.name))
    for elem_dict in flow.canvas:
        elem_dict['parent_path'] = flow.name
        el = FlowElement.from_dict(elem_dict)

        if isinstance(el, ProcessGroup):
            _init_component(el, flow)

        if flow.elements.get(el.name):
            raise FlowLibException("Root FlowElement is already defined: {}".format(el.name))
        else:
            flow.elements[el.name] = el

    _replace_flow_element_vars(flow.elements, flow.loaded_components)


def _load_components(component_dir, flow):
    for root, subdirs, files in os.walk(component_dir):
        for _file in files:
            if _file.endswith('.yaml') or _file.endswith('.yml'):
                logging.info("Loading component: {}".format(_file))
                with open(os.path.join(root, _file)) as f:
                    raw_component = yaml.safe_load(f)
                    raw_component['source_file'] = f.name

                loaded_component = FlowComponent(**raw_component)
                component_ref = loaded_component.source_file.split(component_dir)[1].lstrip(os.sep)
                flow.loaded_components[component_ref] = loaded_component


def _init_component(pg_element, flow):
    logging.info("Loading ProcessGroup: {}".format(pg_element.name))
    component = flow.loaded_components.get(pg_element.component_ref)
    if not component:
        parent = flow.get_parent_element(pg_element)
        source = parent.source_file if hasattr(parent, 'source_file') else 'Root:flow.yaml'
        raise FlowLibException("Component reference {} not found for ProcessGroup {} loaded from {}".format(
            pg_element.component_ref, pg_element.name, source))

    # Validate required variables are present
    if component.required_vars:
        for v in component.required_vars:
            if not v in pg_element.vars:
                raise FlowLibException("Missing Required Var. {} is undefined but is required by {}".format(v, component.source_file))

    # Call FlowElement.from_dict() on each element in the process_group
    for elem_dict in component.process_group:
        elem_dict['parent_path'] = "{}/{}".format(pg_element.parent_path, pg_element.name)
        el = FlowElement.from_dict(elem_dict)

        if isinstance(el, ProcessGroup):
            if el.component_ref == pg_element.component_ref:
                raise FlowLibException("Recursive component reference found in {}. A component cannot reference itself.".format(pg_element.component_ref))
            else:
                _init_component(el, flow)

        if pg_element.elements.get(el.name):
            raise FlowLibException("Found Duplicate Elements. FlowElement {} is already defined in: {}".format(el.name, pg_element.component_ref))
        else:
            pg_element.elements[el.name] = el


def _replace_flow_element_vars(elements, loaded_components):
    """
    Recusively apply the variable evaluation to each element in the flow
    :param elements: The elements to deploy
    :type elements: list(flowlib.model.FlowElement)
    :param loaded_components: The components that were imported during flow.init()
    :type loaded_components: map(str:flowlib.model.FlowComponent)
    """
    for el in elements.values():
        if isinstance(el, ProcessGroup):
            source_component = loaded_components[el.component_ref]
            _replace_vars(el, source_component)
            _replace_flow_element_vars(el.elements, loaded_components)


def _replace_vars(process_group, source_component):
    """
    Replace vars for all Processor elements inside a given ProcessGroup

    Note: We already valdated that required vars were present during flow.init()
      so don't worry about it here

    :param process_group: The processorGroup processors that need vars evaluated
    :type process_group: flowlib.model.ProcessGroup
    :param component: The source component that the processGroup was created from
    :type component: flowlib.model.FlowComponent
    """
    # Create a dict of vars to replace
    context = copy.deepcopy(source_component.defaults) or dict()
    if process_group.vars:
        for key,val in process_group.vars.items():
            context[key] = val

    # Apply var replacements for each value of processor.config.properties
    for el in process_group.elements.values():
        if isinstance(el, Processor):
            for k,v in el.config.properties.items():
                t = env.from_string(v)
                el.config.properties[k] = t.render(**context)

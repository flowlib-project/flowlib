# -*- coding: utf-8 -*-
import logging
import copy
import re
import os
import yaml

import flowlib
from flowlib.model import (FlowLibException, FlowComponent, FlowElement,
    Processor, ProcessGroup)

VAR_WRAPPER = "$({})"

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
    flow.comments = raw.get('comments', "")

    if component_dir:
        flow.component_dir = component_dir
    else:
        flow.component_dir = _find_component_dir(os.path.dirname(_file.name))

    logging.info("Initializing root Flow {} from file {} with component lib {}".format(flow.name, _file.name, flow.component_dir))
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


def _init_component(pg_element, flow):
    logging.info("Loading ProcessGroup: {}".format(pg_element.name))
    file_ref = os.path.join(flow.component_dir, pg_element.component_ref)
    with open(file_ref) as f:
        raw = yaml.safe_load(f)

    try:
        process_group = raw.pop('process_group')
    except KeyError as e:
        raise FlowLibException("FlowLib component does not contain a process_group field: {}".format(loaded_component.source_file))

    raw['source_file'] = file_ref
    loaded_component = FlowComponent(**raw)
    if not pg_element.component_ref in flow.loaded_components:
        flow.loaded_components[pg_element.component_ref] = loaded_component

    # Validate required variables are present
    if loaded_component.required_vars:
        for v in loaded_component.required_vars:
            if not v in pg_element.vars:
                raise FlowLibException("Missing Required Var. {} is undefined but is required by {}".format(v, loaded_component.file_ref))

    # Call FlowElement.from_dict() on each element in the process_group
    for elem_dict in process_group:
        elem_dict['parent_path'] = "{}/{}".format(pg_element.parent_path, pg_element.name)
        el = FlowElement.from_dict(elem_dict)

        if isinstance(el, ProcessGroup):
            if el.component_ref == pg_element.component_ref:
                raise FlowLibException("Recursive component reference found in {}. A component cannot reference itself.".format(pg_element.component_ref))
            _init_component(el, flow)

        if pg_element.elements.get(el.name):
            raise FlowLibException("Found Duplicate Elements. FlowElement {} is already defined in: {}".format(el.name, ref))
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
            if (len(wrapped_vars.keys()) > 0):
                for k,v in el.config.properties.items():
                    pattern.sub(lambda x: wrapped_vars[x.group()], v)
                    el.config.properties[k] = pattern.sub(lambda x: wrapped_vars[x.group()], v)


def _find_component_dir(flow_source_path):
    """
    TODO: Support merging component directories

    Find a valid flowlib component directory if it was not specified with --component-dir
    From highest to lowest precedence:
    1. First check the directory containing the source flow.yaml for a lib/ directory
    2. Then check the FLOWLIB_COMPONENT_DIR environment variable
    ...
    """
    if os.path.isdir(os.path.join(flow_source_path, 'components')):
        return os.path.join(flow_source_path, 'components')
    else:
        return os.getenv('FLOWLIB_COMPONENT_DIR', '/etc/flowlib/components')

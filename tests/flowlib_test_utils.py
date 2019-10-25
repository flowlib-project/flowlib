# -*- coding: utf-8 -*-
import copy
import os
import yaml

import flowlib
from flowlib.parser import init_flow
from flowlib.model.config import FlowLibConfig
from flowlib.model.flow import Flow
from flowlib.model.component import FlowComponent


def load_init_config():
    init_dir = os.path.abspath(os.path.join(os.path.dirname(flowlib.__file__), 'init'))
    with open(os.path.join(init_dir, '.flowlib.yml')) as f:
        config = FlowLibConfig.new_from_file(f)

    return config

def load_init_flow(init=True):
    init_dir = os.path.abspath(os.path.join(os.path.dirname(flowlib.__file__), 'init'))
    flow_yaml = os.path.join(init_dir, 'flow.yaml')
    component_dir = os.path.join(init_dir, 'components')
    with open(flow_yaml, 'r') as f:
        raw = yaml.safe_load(f)

    flow = Flow(copy.deepcopy(raw), **raw)
    if init:
        init_flow(flow, component_dir)

    return flow


def load_init_component(path):
    init_dir = os.path.abspath(os.path.join(os.path.dirname(flowlib.__file__), 'init'))
    component_dir = os.path.join(init_dir, 'components')
    with open(os.path.join(component_dir, path), 'r') as f:
        raw = yaml.safe_load(f)

    raw['source_file'] = f.name.split(component_dir)[1].lstrip(os.sep)
    return FlowComponent(copy.deepcopy(raw), **raw)

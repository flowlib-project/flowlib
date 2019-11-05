# -*- coding: utf-8 -*-
import copy
import os
import yaml

import flowlib
from flowlib.parser import init_flow
from flowlib.model.config import FlowLibConfig
from flowlib.model.flow import Flow
from flowlib.model.component import FlowComponent

RESOURCES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'resources'))
COMPONENT_DIR = os.path.join(RESOURCES_DIR, 'components')


def load_test_config():
    with open(os.path.join(RESOURCES_DIR, '.flowlib.yml')) as f:
        config = FlowLibConfig.new_from_file(f)

    return config


def load_test_component(path):
    with open(os.path.join(COMPONENT_DIR, path), 'r') as f:
        raw = yaml.safe_load(f)

    raw['source_file'] = f.name.split(COMPONENT_DIR)[1].lstrip(os.sep)
    return FlowComponent(copy.deepcopy(raw), **raw)


def load_test_flow(init=True):
    flow_yaml = os.path.join(RESOURCES_DIR, 'flow.yaml')
    with open(flow_yaml, 'r') as f:
        raw = yaml.safe_load(f)

    flow = Flow(copy.deepcopy(raw), **raw)
    if init:
        flow.initialize(COMPONENT_DIR)

    return flow

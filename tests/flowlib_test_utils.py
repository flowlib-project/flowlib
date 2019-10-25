# -*- coding: utf-8 -*-
import copy
import os
import yaml

import flowlib
from flowlib.parser import init_flow
from flowlib.model.config import FlowLibConfig
from flowlib.model.flow import Flow
from flowlib.model.component import FlowComponent

INIT_DIR = os.path.abspath(os.path.join(os.path.dirname(flowlib.__file__), 'init'))

def load_test_config():
    with open(os.path.join(INIT_DIR, '.flowlib.yml')) as f:
        config = FlowLibConfig.new_from_file(f)

    return config


def load_test_component(path):
    component_dir = os.path.join(INIT_DIR, 'components')
    with open(os.path.join(component_dir, path), 'r') as f:
        raw = yaml.safe_load(f)

    raw['source_file'] = f.name.split(component_dir)[1].lstrip(os.sep)
    return FlowComponent(copy.deepcopy(raw), **raw)


def load_test_flow(init=True):
    flow_yaml = os.path.join(INIT_DIR, 'flow.yaml')
    component_dir = os.path.join(INIT_DIR, 'components')
    with open(flow_yaml, 'r') as f:
        raw = yaml.safe_load(f)

    flow = Flow(copy.deepcopy(raw), **raw)
    if init:
        init_flow(flow, component_dir)

    return flow


def load_simple_flow(init=True):
    raw = {
        'name': 'simple-test-flow',
        'global_vars': {
            'abc': 'xyz'
        },
        'controller_services': [{
            'name': 'asdf',
            'config': {
                'package_id': 'org.apache.nifi.avro.AvroReader',
                'properties': {
                    'schema-name': '{{ abc }}'
                }
            }
        }],
        'canvas': [{
            'name': 'debug',
            'type': 'processor',
            'config': {
                'package_id': 'org.apache.nifi.processors.standard.DebugFlow',
                'properties': {
                    'property': "{{ abc }}",
                    'controller': "{{ controller('asdf') }}"
                }
            }
        }]
    }
    simple_flow = Flow(copy.deepcopy(raw), **raw)
    if init:
        init_flow(simple_flow)

    return simple_flow

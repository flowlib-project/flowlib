# -*- coding: utf-8 -*-
import logging
import sys
import yaml

import flowlib.nifi
import flowlib.parser
from flowlib.model import FlowLibException, Flow


def new_flow_from_file(component_dir, flow_yaml):
    """
    Construct a new flow from a file or a running NiFi instance
    :param flow_yaml: The flow defined as a yaml file
    :type flow_yaml: Either a file path or a file object
    :param component_dir: The directory of re-useable flow components
    :type component_dir: str
    :raises: FlowLibException
    """
    flow = Flow()
    if isinstance(flow_yaml, str):
        flow_yaml = open(flow_yaml)
    flowlib.parser.init_from_file(flow, flow_yaml, component_dir)
    flow_yaml.close()
    return flow


def new_flow_from_nifi(nifi_endpoint=None):
    """
    :param nifi_endpoint: The endpoint of a running NiFi instance
    :type nifi_endpoint: str
    :raises: FlowLibException
    """
    flow = Flow()
    flowlib.nifi.init_from_nifi(flow, nifi_endpoint)
    return flow


def validate_flow_yaml(config):
    logging.info("Validating NiFi Flow YAML...")
    try:
        new_flow_from_file(config.component_dir, config.flow_yaml)
        # todo: validate connections, init nifi processor DTOs, etc..
        # but dont actually try to connect to the NiFi API
    except FlowLibException as e:
        logging.error(e)
        sys.exit(1)


def export_flow_yaml(config):
    """
    :type config: FlowLibConfig
    """
    logging.info("Exporting NiFi flow to YAML...")
    try:
        flow = new_flow_from_nifi(config.nifi_endpoint)
        yaml.dump(flow, config.export_yaml, default_flow_style=False)
    except FlowLibException as e:
        logging.error(e)
        sys.exit(1)


def deploy_flow_yaml(config):
    """
    :type config: FlowLibConfig
    """
    logging.info("Deploying NiFi flow from YAML...")
    try:
        flow = new_flow_from_file(config.component_dir, config.flow_yaml)
        flowlib.nifi.deploy_flow(flow, config.nifi_endpoint)
    except FlowLibException as e:
        logging.error(e)
        sys.exit(1)

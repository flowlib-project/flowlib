# -*- coding: utf-8 -*-
import logging
import sys

import flowlib.nifi
import flowlib.parser
from flowlib.model import FlowLibException, Flow


def new_flow(component_dir=None, flow_yaml=None, nifi_url=None):
    """
    Construct a new flow from a file or a running NiFi instance
    :param flow_yaml: The flow defined as a yaml file
    :type flow_yaml: Either a file path or a file object
    :param nifi_url: The endpoint of a running NiFi instance
    :type nifi_url: str
    :raises: FlowLibException
    """
    if flow_yaml is None and nifi_url is None:
        raise FlowLibException("flow_yaml or nifi_url must be specified to create a new Flow")

    flow = Flow()
    if flow_yaml is not None:
        if isinstance(flow_yaml, str):
            flow_yaml = open(flow_yaml)
        flowlib.parser.init_from_file(flow, flow_yaml, component_dir)
        flow_yaml.close()
    else:
        flowlib.nifi.init_from_nifi(flow, nifi_url)

    return flow


# def validate_flow(config):
#     try:
#         flow = new_flow(flow_yaml=config.flow_yaml)
#         # flow.validate()
#     except FlowLibException as e:
#         logging.error(e)
#         sys.exit(1)


def deploy_flow_yaml(config):
    """
    :type config: FlowLibConfig
    """
    logging.info("Deploying NiFi flow from YAML with config:")
    logging.info(config)

    nifi_endpoint = "http://{}:{}/nifi-api".format(config.nifi_address, config.nifi_port)
    try:
        flow = new_flow(flow_yaml=config.flow_yaml, component_dir=config.component_dir)
        flowlib.nifi.deploy_flow(flow, nifi_endpoint)
    except FlowLibException as e:
        logging.error(e)
        sys.exit(1)

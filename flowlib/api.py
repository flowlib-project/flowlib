# -*- coding: utf-8 -*-
import logging
import sys

import flowlib.nifi
from flowlib.model import FlowLibException, Flow

def validate_flow(config):
    try:
        flow = Flow.load_from_file(config.flow_yaml)
        # flow.validate()
    except FlowLibException as e:
        logging.error(e)
        sys.exit(1)


def deploy_flow_yaml(config):
    """
    :type config: FlowLibConfig
    """
    logging.info("Deploying NiFi flow from YAML with config:")
    logging.info(config)

    nifi_endpoint = "http://{}:{}/nifi-api".format(config.nifi_address, config.nifi_port)
    try:
        flow = Flow.load_from_file(config.flow_yaml)
        # flow.validate()
        flowlib.nifi.deploy_flow(flow, nifi_endpoint)

    except FlowLibException as e:
        logging.error(e)
        sys.exit(1)

# -*- coding: utf-8 -*-
import os
import sys
import shutil
import yaml


import flowlib.parser
import flowlib.nifi.rest
import flowlib.nifi.docs
from flowlib.model import FlowLibException
from flowlib.model.flow import Flow
from flowlib.logger import log


def gen_flow_scaffold(dest):
    """
    :param dest: The destination directory to create a new flowlib project scaffold
    :type dest: str
    """
    if os.path.exists(dest):
        raise FlowLibException("Destination directory already exists {}".format(dest))

    log.info("Generating Flowlib project scaffold at {}".format(dest))
    init_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'init'))
    shutil.copytree(init_dir, dest)


def gen_flowlib_docs(config, dest):
    """
    Use the configured NiFi api endpoint to generate html docs containing example YAML definitions for the available
      processors, controller service, and reporting tasks
    :type config: FlowLibConfig
    :param dest: The destination directory to create the flowlib documentation
    :type dest: str
    """
    log.info("Generating Flowlib documentation for {} at {}".format(config.nifi_endpoint, dest))
    try:
        flowlib.nifi.docs.generate_docs(config, dest)
    except FlowLibException as e:
        log.error(e)
        sys.exit(1)


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
    flowlib.parser.init_flow_from_file(flow, flow_yaml, component_dir)
    return flow


def new_flow_from_nifi(nifi_endpoint=None):
    """
    :param nifi_endpoint: The endpoint of a running NiFi instance
    :type nifi_endpoint: str
    :raises: FlowLibException
    """
    flow = Flow()
    flowlib.nifi.rest.init_from_nifi(flow, nifi_endpoint)
    return flow


def validate_flow(config):
    """
    :type config: FlowLibConfig
    """
    log.info("Validating NiFi Flow YAML {}".format(config.flow_yaml.name))
    try:
        flow = new_flow_from_file(config.component_dir, config.flow_yaml)
        print("Flow is valid")
        print("Flow Name: {}".format(flow.name), file=sys.stdout)
        print("Flow Version: {}".format(flow.version), file=sys.stdout)
        # todo: validate connections, init nifi processor DTOs, etc..
        # but dont actually try to connect to the NiFi API
    except FlowLibException as e:
        log.error(e)
        sys.exit(1)


def export_flow(config):
    """
    :type config: FlowLibConfig
    """
    log.info("Exporting NiFi flow deployment from {}".format(config.nifi_endpoint))
    try:
        flow = new_flow_from_nifi(config.nifi_endpoint)
        yaml.dump(flow, config.export, default_flow_style=False)
    except FlowLibException as e:
        log.error(e)
        sys.exit(1)


def deploy_flow(config):
    """
    :type config: FlowLibConfig
    """
    log.info("Deploying NiFi flow to {}".format(config.nifi_endpoint))
    try:
        flow = new_flow_from_file(config.component_dir, config.flow_yaml)
        flowlib.nifi.rest.deploy_flow(flow, config.nifi_endpoint, force=config.force)
        log.info("Flow deployment completed successfully")
    except FlowLibException as e:
        log.error("Flow deployment failed")
        log.error(e)
        sys.exit(1)


def configure_flow_controller(config):
    """
    :type config: FlowLibConfig
    """
    log.info("Configuring Flow Controller for {}".format(config.nifi_endpoint))
    try:
        flowlib.nifi.rest.configure_flow_controller(config.nifi_endpoint, config.reporting_task_controllers,
            config.reporting_tasks, config.max_timer_driven_threads, config.max_event_driven_threads, config.force)
        log.info("Flow Controller configuration completed successfully")
    except FlowLibException as e:
        log.error("Flow Controller configuration failed")
        log.error(e)
        sys.exit(1)


def list_components(config, component_type):
    """
    :type config: FlowLibConfig
    :param component_type: List the available components for this type
    :type component_type: str
    """
    log.debug("Listing all available {}...".format(component_type))
    try:
        flowlib.nifi.rest.list_components(config.nifi_endpoint, component_type)
    except FlowLibException as e:
        log.error(e)
        sys.exit(1)


def describe_component(config, component_type, package_id):
    """
    :type config: FlowLibConfig
    :param component_type: The type of component being described
    :type component_type: str
    :param package_id: The package id of the component to describe
    :type package_id: str
    """
    log.debug("Describing {}: {}...".format(component_type, package_id))
    try:
        flowlib.nifi.docs.describe_component(config.nifi_endpoint, component_type, package_id)
    except FlowLibException as e:
        log.error(e)
        sys.exit(1)

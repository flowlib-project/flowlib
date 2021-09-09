# -*- coding: utf-8 -*-
import copy
import io
import os
import shutil
import json
import uuid
from nipyapi.registry.apis.buckets_api import BucketsApi
from nipyapi.registry.apis.items_api import ItemsApi
from nipyapi.registry.apis.bucket_flows_api import BucketFlowsApi
import yaml
from nipyapi.registry.rest import ApiException
from nipyapi.utils import fs_write
import flowlib.parser
import flowlib.nifi.rest
import flowlib.nifi.docs
from flowlib.exceptions import FlowLibException
from flowlib.model.flow import Flow
from flowlib.model.deployment import FlowDeployment
from flowlib.logger import log
from flowlib.convert2flowlib.structure import NIFIFILECONTENTS, STRUCTURE


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
        flowlib.nifi.docs.generate_docs(config, dest, config.force)
    except FlowLibException as e:
        log.error(e)
        raise


def new_flow_from_deployment(deployment_json, validate=True):
    """
    Construct a new flow from a deployment json file.
    Deployment json is created using the --export option
    :param deployment_json: The flow deployment as a json file
    :type deployment_json: io.TextIOWrapper
    :raises: FlowLibException
    """
    deployment = FlowDeployment.from_dict(json.load(deployment_json))
    flow = Flow(copy.deepcopy(deployment.flow), **deployment.flow)
    flow.flowlib_version = flowlib.__version__
    flow.initialize(with_components=deployment.components)
    if validate:
        flow.validate()
    return (flow, deployment)


def new_flow_from_yaml(flow_yaml, component_dir=None, validate=True):
    """
    Construct a new flow from a yaml file
    :param flow_yaml: The flow defined as a yaml file
    :type flow_yaml: io.TextIOWrapper
    :param component_dir: The directory of re-useable flow components
    :type component_dir: str
    :raises: FlowLibException
    """
    raw = yaml.safe_load(flow_yaml)

    # If --component-dir is specified, use that.
    # Otherwise use the components/ directory relative to flow.yaml
    if component_dir:
        component_dir = os.path.abspath(component_dir)
    else:
        component_dir = os.path.abspath(os.path.join(os.path.dirname(flow_yaml.name), 'components'))

    flow = Flow(copy.deepcopy(raw), **raw)
    flow.flowlib_version = flowlib.__version__
    flow.initialize(component_dir=component_dir)
    if validate:
        flow.validate()
    return flow


def validate_flow(config):
    """
    :type config: FlowLibConfig
    """
    log.info("Validating NiFi Flow YAML {}".format(config.flow_yaml))
    try:
        with open(config.flow_yaml, 'r') as f:
            new_flow_from_yaml(f, config.component_dir)
    except FlowLibException as e:
        log.error(e)
        raise


def deploy_flow(config):
    """
    :type config: FlowLibConfig
    """
    log.info("Deploying NiFi flow to {}".format(config.nifi_endpoint))
    try:
        deployment = None
        if config.flow_yaml:
            with open(config.flow_yaml, 'r') as f:
                flow = new_flow_from_yaml(f, config.component_dir)
        elif config.deployment_json:
            with open(config.deployment_json, 'r') as f:
                flow, deployment = new_flow_from_deployment(f)
        else:
            raise FlowLibException("One of config.flow_yaml or config.deployment_json must be specified")

        flowlib.nifi.rest.deploy_flow(flow, config, deployment=deployment, force=config.force)
        log.info("Flow deployment completed successfully")
    except FlowLibException as e:
        log.error("Flow deployment failed")
        log.error(e)
        raise


def registry_import_flow(config):
    try:
        if config.registry_import:
            flowlib.nifi.rest.registry_import(config.registry_import)
        print("Import complete...")
    except Exception as e:
        print(f"Error: {e}")


def registry_convert_flow(config):
    nifi_contents = NIFIFILECONTENTS("registry-output.json", config.output_format)

    structure = STRUCTURE()
    structure.construct_flowlib_format(child_pgs=nifi_contents.return_root_processor_group())
    structure.write_to_files()


def registry_export_flow(registry_options, syntax_format=None):
    """
    :type config: FlowLibConfig
    """
    buckets = BucketsApi()
    flows = ItemsApi()
    bucketFlows = BucketFlowsApi
    bucket_tracker = []
    bucket_counter = 0
    flow_tracker = []
    flow_counter = 0
    export_bucket_id = None
    export_flow_id = None

    try:
        if registry_options:
            desired_bucket_name = registry_options[0]
            print(desired_bucket_name)

            found_buckets = buckets.get_buckets()
            normalized_data = [{"name": _x.name, "identifier": _x.identifier, "revision": _x.revision.version} for _x in found_buckets]

            if desired_bucket_name == 'all':
                obj = [_x for _x in normalized_data]
            else:
                obj = [_x for _x in normalized_data if str(_x["name"]).startswith(desired_bucket_name)]

            for _t in obj:
                _t["counter"] = bucket_counter
                bucket_counter += 1
                bucket_tracker.append(_t)

            user_options_headers = '* Option | Bucket Name *'

            print('*'*len(user_options_headers))
            print(user_options_headers)
            print('*'*len(user_options_headers), "\n")

            for _t in bucket_tracker:
                option = f'{_t["counter"]} | {_t["name"]}'
                print(option)

            print(f"{str(bucket_counter)} | Create New Bucket")

            user_option = input("\nOption: ")
            print()
            verify_digit = user_option.isdigit()
            verify_range = (int(user_option) in list(range(bucket_counter + 1))) if verify_digit else False

            while not verify_digit or not verify_range:
                user_option = input("\nOption isn't a number or \nValue is not an option: ")
                verify_digit = user_option.isdigit()
                verify_range = (int(user_option) in list(range(bucket_counter + 1))) if verify_digit else False

            if bucket_counter == int(user_option):
                msg = "* Creating a new bucket and flow *"
                print("*" * len(msg))
                print(msg)
                print("*" * len(msg))
                new_bucket = input("Bucket name: ")
                new_flow = input("Flow name: ")

                bucket_creation = buckets.create_bucket(
                    body={
                        "name": new_bucket
                    }
                )

                theFlow = bucketFlows()
                theFlow.create_flow(
                    bucket_id=bucket_creation.identifier,
                    body={
                        "name": new_flow
                    }
                )

                print("\nBucket and flow created successfully!!")

            else:
                bucket_data = [_x for _x in bucket_tracker if _x["counter"] == int(user_option)][0]
                export_bucket_id = bucket_data["identifier"]
                found_flows = flows.get_items_in_bucket(bucket_data["identifier"])
                flow_obj = [{"name": _x.name, "identifier": _x.identifier} for _x in found_flows]

                for _t in flow_obj:
                    _t["counter"] = flow_counter
                    flow_counter += 1
                    flow_tracker.append(_t)

                user_options_headers = f'* Bucket: {bucket_data["name"]} | Flow Name *'

                print('*' * len(user_options_headers))
                print(user_options_headers)
                print('*' * len(user_options_headers), "\n")

                for _t in flow_tracker:
                    option = f'{_t["counter"]} | {_t["name"]}'
                    print(option)

                print(f"{str(flow_counter)} | Create New Flow")

                user_option = input("\nOption: ")
                print()
                verify_digit = user_option.isdigit()
                verify_range = (int(user_option) in list(range(flow_counter + 1))) if verify_digit else False

                while not verify_digit or not verify_range:
                    user_option = input("\nOption isn't a number or \nValue is not an option: ")
                    verify_digit = user_option.isdigit()
                    verify_range = (int(user_option) in list(range(flow_counter + 1))) if verify_digit else False

                if int(user_option) == flow_counter:
                    new_flow = input("\nName of new flow: ")
                    theFlow = bucketFlows()
                    theFlow.create_flow(
                        bucket_id=bucket_data["identifier"],
                        body={
                            "name": new_flow
                        }
                    )

                    print("\nBucket and flow created successfully!!")
                else:
                    flow_data = [_x for _x in flow_tracker if _x["counter"] == int(user_option)][0]
                    export_flow_id = flow_data["identifier"]

            if export_flow_id is not None and export_bucket_id is not None:
                json_content = flowlib.nifi.rest.registry_export((export_bucket_id, export_flow_id))
                content = json.dumps(json_content, indent=2, sort_keys=True)
                fs_write(content, "registry-output.json")

    except ApiException as e:
        print(f'Error: {e.status} {e.reason}')
    except ValueError as e:
        print(e)


def export_flow(config, fp=None):
    """
    :type config: FlowLibConfig
    :param fp: A python file object to write to, if this is not provided then return a string buffer
    :return: io.TextIOWrapper or None
    """
    log.info("Exporting NiFi flow deployment {} from {}".format(config.export, config.nifi_endpoint))
    try:
        deployment = flowlib.nifi.rest.get_previous_deployment(config.nifi_endpoint, config.export)
        if fp:
            deployment.save(fp)
        else:
            s = io.StringIO()
            deployment.save(s)
            return s
    except FlowLibException as e:
        log.error(e)
        raise


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
        raise


def list_components(config, component_type):
    """
    :type config: FlowLibConfig
    :param component_type: List the available components for this type
    :type component_type: str
    :return: list(str)
    """
    log.debug("Listing all available {}...".format(component_type))
    try:
        return flowlib.nifi.docs.list_components(config.docs_directory, component_type)
    except FlowLibException as e:
        log.error(e)
        raise


def describe_component(config, component_type, package_id):
    """
    :type config: FlowLibConfig
    :param component_type: The type of component being described
    :type component_type: str
    :param package_id: The package id of the component to describe
    :type package_id: str
    :return: dict(str:dict(PropertyDescriptorDTO))
    """
    log.debug("Describing {}: {}...".format(component_type, package_id))
    try:
        return flowlib.nifi.docs.describe_component(config.docs_directory, component_type, package_id)
    except FlowLibException as e:
        log.error(e)
        raise

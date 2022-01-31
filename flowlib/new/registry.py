# -*- coding: utf-8 -*-
import sys

from flowlib.new.util import call_cmd, call_move_cmd
import json


def list_flows(config, bucket_name):
    all_buckets = __get_buckets(config.container, config.registry_endpoint)
    for bucket in all_buckets:
        if bucket_name == "all" or bucket_name == bucket['name']:
            print("Bucket: {}".format(bucket['name']))
            __display_flows(config, bucket['identifier'])


def deploy_flows(config, flows, dest_registry_endpoint):
    source_buckets = __get_buckets(config.container, config.registry_endpoint, True)

    if not source_buckets:
        print("! No flows in the {} registry to move over".format(config.registry_endpoint))
        sys.exit(0)

    dest_buckets = __get_buckets(config.container, dest_registry_endpoint, True)
    flows_input_dict = json.loads(flows)

    if bool(flows_input_dict):
        for bucket_name in flows_input_dict:
            specified_flows = flows_input_dict[bucket_name]
            source_bucket_id = source_buckets[bucket_name]['identifier'] if bucket_name in source_buckets else None
            dest_bucket_id = dest_buckets[bucket_name]['identifier'] if bucket_name in dest_buckets else None

            if not source_bucket_id or not dest_bucket_id:
                print("Bucket: {} does not exist in the {} registry".format(
                    bucket_name, config.registry_endpoint if not source_bucket_id else dest_registry_endpoint))
            else:
                for flow_name in specified_flows:
                    source_flows = __get_flows(config.container, config.registry_endpoint, source_bucket_id)
                    source_flow = __filter_flows(source_flows, flow_name)
                    __move_flow(config, dest_registry_endpoint, source_flow, dest_bucket_id, bucket_name, flow_name)
    elif source_buckets:
        for source_bucket_name in source_buckets.keys():
            source_flows = __get_flows(config.container, config.registry_endpoint,
                                       source_buckets[source_bucket_name]['identifier'])
            for source_flow in source_flows:
                flow_name = source_flow['name']
                dest_bucket_id = dest_buckets[source_bucket_name]['identifier']
                __move_flow(config, dest_registry_endpoint, source_flow, dest_bucket_id, source_bucket_name, flow_name)


def __display_flows(config, bucket_id):
    flows = __get_flows(config, bucket_id)
    if flows:
        i = 1
        for key in flows:
            print('\t{}. {}\tVersion {}'.format(i, key['name'], key['versionCount']))
            i += 1
    else:
        print("\t! No flows available")
    print()


def __filter_flows(flows, flow_name):
    for flow in flows:
        if flow['name'] == flow_name:
            return flow
    return None


def __get_buckets(container, registry_endpoint, as_map=False):
    buckets = call_cmd(container, registry_endpoint, "registry list-buckets")
    if not as_map:
        return buckets
    else:
        return {bucket['name']: bucket for bucket in buckets}


def __get_flows(container, registry_endpoint, bucket_id):
    return call_cmd(container, registry_endpoint,
                    "registry list-flows --bucketIdentifier {}".format(bucket_id))


def __move_flow(config, dest_registry_endpoint, source_flow, dest_bucket_id, bucket_name, flow_name):
    dest_flows = __get_flows(config.container, dest_registry_endpoint, dest_bucket_id)
    dest_flow = __filter_flows(dest_flows, flow_name)
    if source_flow and dest_flow:
        call_move_cmd(config.container, config.registry_endpoint, dest_registry_endpoint,
                      "registry transfer-flow-version --sourceFlowIdentifier {} --flowIdentifier {}".format(
                          source_flow['identifier'], dest_flow['identifier']))
    else:
        print("Bucket: {} Flow: {} cannot be found in the {} registry".format(
            bucket_name, flow_name, config.registry_endpoint if not source_flow else dest_registry_endpoint))
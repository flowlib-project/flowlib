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


def transfer_flows(config, flows):
    source_buckets = __get_buckets(config.container, config.registry_endpoint, True)
    dest_buckets = __get_buckets(config.container, config.dest_registry_endpoint,
                                 True) if config.dest_registry_endpoint else None

    if not source_buckets:
        print("! No buckets and flows in the {} registry to move over".format(config.registry_endpoint))
        sys.exit(0)

    if not dest_buckets and config.dest_registry_endpoint:
        print("! No buckets and flows in the {} registry to move flows to".format(config.dest_registry_endpoint))
        sys.exit(0)

    flows_input_dict = json.loads(flows)

    for move_direction in flows_input_dict:
        bucket_names = move_direction.split(":")
        source_bucket_name = bucket_names[0]
        dest_bucket_name = bucket_names[1]
        if len(bucket_names) != 2:
            print("! Invalid format: {} must be source_bucket:destination_bucket".format(move_direction))
        else:
            source_bucket = source_buckets[source_bucket_name] if source_bucket_name in source_buckets else None
            dest_bucket = dest_buckets[dest_bucket_name] if dest_buckets else source_buckets[dest_bucket_name]
            specified_flows = flows_input_dict[move_direction]

            if not source_bucket or not dest_bucket:
                print("Bucket: {} does not exist in the {} registry".format(
                    source_bucket_name if not source_bucket else dest_bucket_name, config.registry_endpoint))
            else:
                source_flows = __get_flows(config.container, config.registry_endpoint, source_bucket['identifier'])
                dest_flows = __get_flows(config.container,
                                         config.dest_registry_endpoint if config.dest_registry_endpoint
                                         else config.registry_endpoint, dest_bucket['identifier'])

                if bool(specified_flows):
                    for flow_name in specified_flows:
                        source_flow = __filter_flows(source_flows, flow_name)
                        if not bool(source_flow):
                            print("Bucket: {} Flow: {} cannot be found in the {} registry".format(
                                source_bucket_name, flow_name, config.registry_endpoint))
                        else:
                            dest_flow = __filter_flows(dest_flows, flow_name)
                            __move_flow(config, source_flow, dest_flow, dest_bucket)
                else:
                    for source_flow in source_flows:
                        flow_name = source_flow['name']
                        dest_flow = __filter_flows(dest_flows, flow_name)
                        __move_flow(config, source_flow, dest_flow, dest_bucket)


def __display_flows(config, bucket_id):
    flows = __get_flows(config.container, config.registry_endpoint, bucket_id)
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


def __move_flow(config, source_flow, dest_flow, dest_bucket):
    dest_flow_id = None
    if not dest_flow:
        dest_flow_id = call_cmd(config.container,
                                config.registry_endpoint if not config.dest_registry_endpoint else config.dest_registry_endpoint,
                                "registry create-flow --bucketIdentifier {} --flowName \"{}\" --flowDesc \"{}\""
                                .format(dest_bucket['identifier'], source_flow['name'], source_flow['description']))
    else:
        dest_flow_id = dest_flow['identifier']

    call_move_cmd(config.container, config.registry_endpoint, config.dest_registry_endpoint,
                  "registry transfer-flow-version --sourceFlowIdentifier {} --flowIdentifier {}".format(
                      source_flow['identifier'], dest_flow_id))

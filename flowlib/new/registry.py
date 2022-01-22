# -*- coding: utf-8 -*-
from flowlib.new.util import call_cmd

def list_flows(config, bucket_name):
    all_buckets = call_cmd(config.registry_endpoint, "registry list-buckets")
    for bucket in all_buckets:
        if bucket_name == "all" or bucket_name == bucket['name']:
            print("Bucket: {}".format(bucket['name']))
            __display_flows(config, bucket['identifier'])


def __display_flows(config, bucket_id):
    flows = call_cmd(config.registry_endpoint, "registry list-flows --bucketIdentifier {id}".format(id=bucket_id))
    if flows:
        i = 1
        for key in flows:
            print('\t{}. {}\tVersion {}'.format(i, key['name'], key['versionCount']))
            i += 1
    else:
        print("\t! No flows available")
    print()

# -*- coding: utf-8 -*-
from flowlib.new.util import parse_output

def list_flows(config, bucket_name):
    all_buckets = parse_output(config.registry_endpoint, "registry list-buckets")
    if bucket_name == "all":
        for (k,v) in all_buckets.items():
            print("Bucket: {}".format(k))
            __display_flows(config, v)
    else:
        bucket_id = {v for (k,v) in all_buckets.items() if k in bucket_name}
        print("Bucket: {}".format(bucket_name))
        __display_flows(config, bucket_id.pop())

def __display_flows(config, bucket_id):
    flows = parse_output(config.registry_endpoint, "registry list-flows --bucketIdentifier {id}".format(id=bucket_id))
    if flows:
        i = 1;
        for key in flows.keys():
            print('\t{}. {}'.format(i, key))
            i += 1
    else:
        print("\t! No flows available")
    print()

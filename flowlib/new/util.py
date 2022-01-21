# -*- coding: utf-8 -*-
import subprocess
import sys
from functools import partial

def parse_output(endpoint, cmd, key_field_name="Name", value_field_name="Id"):
    output = call_cmd(endpoint, cmd)
    lines = list(filter(None, map(lambda line: line.strip(), output.stdout.readlines())))
    if len(lines) == 1 and lines[0].startswith("ERROR:"):
        print (lines[0])
        sys.exit(-1)
    elif lines:
        header_split = lines[0].split()
        key_index = header_split.index(key_field_name)
        value_index = header_split.index(value_field_name)
        partial_func = partial(__parse_line, key_index=key_index, value_index=value_index)
        return dict(map(partial_func, lines[2:]))
    else:
        return None

def __parse_line(line, key_index, value_index):
    split = line.split()
    return (split[key_index], split[value_index])

def call_cmd(endpoint, cmd):
    cmd = "docker exec -it nifi-arm /bin/sh /opt/nifi/nifi-toolkit-1.11.4/bin/cli.sh {cmd} --baseUrl {endpt}"\
        .format(cmd=cmd, endpt=endpoint)
    return subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='UTF-8')
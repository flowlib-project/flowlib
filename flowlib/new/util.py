# -*- coding: utf-8 -*-
import subprocess
import sys
import json

def call_move_cmd(container, source, destination, command):
    cmd = None
    if container:
        cmd = "docker run -it --rm --entrypoint /bin/sh {container} -c \"echo 'baseUrl={source}' >> /tmp/sourceProps && " \
              "/opt/nifi/nifi-toolkit-current/bin/cli.sh {cmd} --baseUrl {dest} --sourceProps /tmp/sourceProps -ot json\"" \
            .format(container=container, source=source, cmd=command, dest=destination)
    else:
        cmd = "echo 'baseUrl={source}' >> /tmp/sourceProps && " \
              "/opt/nifi/nifi-toolkit-current/bin/cli.sh {cmd} --baseUrl {dest} --sourceProps /tmp/sourceProps -ot json" \
            .format(source=source, cmd=cmd, dest=destination)
    return __process_output(cmd)

def call_cmd(container, endpoint, command):
    cmd = None
    if container:
        cmd = "docker run -it --rm --entrypoint /opt/nifi/nifi-toolkit-current/bin/cli.sh {container} {cmd} --baseUrl {endpt} -ot json" \
            .format(container=container, cmd=command, endpt=endpoint)
    else:
        cmd = "/opt/nifi/nifi-toolkit-current/bin/cli.sh {cmd} --baseUrl {endpt} -ot json" \
            .format(cmd=command, endpt=endpoint)
    return __process_output(cmd)

def __process_output(cmd):
    cmd_output = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='UTF-8')
    response = cmd_output.communicate()[0]
    if response.strip().startswith("ERROR:"):
        print(response)
        sys.exit(-1)
    elif not response.strip() == "OK":
        return json.loads(response)
    else:
        return None

# -*- coding: utf-8 -*-
import subprocess
import sys
import json

def call_cmd(container, endpoint, command):
    cmd = None
    if container:
        cmd = "docker run -it --rm --entrypoint /opt/nifi/nifi-toolkit-current/bin/cli.sh {container} {cmd} --baseUrl {endpt} -ot json"\
            .format(container=container, cmd=command, endpt=endpoint)
    else:
        cmd = "/opt/nifi/nifi-toolkit-current/bin/cli.sh {cmd} --baseUrl {endpt} -ot json" \
            .format(container=container, cmd=command, endpt=endpoint)
    cmd_output = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='UTF-8')
    response = cmd_output.communicate()[0]
    if response.strip().startswith("ERROR:"):
        print(response)
        sys.exit(-1)
    else:
        return json.loads(response)
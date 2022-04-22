# -*- coding: utf-8 -*-
import subprocess
import sys
import json
import re
import requests

def call_move_cmd(container, source_endpoint, dest_endpoint, command):
    cmd = "/opt/nifi/nifi-toolkit-current/bin/cli.sh {cmd} --baseUrl {url} -ot json"

    if dest_endpoint:
        cmd = "echo 'baseUrl={source}' >> /tmp/sourceProps && " + cmd + " --sourceProps /tmp/sourceProps"

    if container:
        cmd = "docker run -it --rm --entrypoint /bin/sh {container} -c \"" + cmd + "\""

    cmd = cmd.format(container=container, cmd=command, url=source_endpoint if not dest_endpoint else dest_endpoint,
                     source=source_endpoint)
    return __process_output(cmd)


def call_multi_cmd(container, endpoint, commands):
    cmd = None
    command = commands.pop(0)
    if container:
        cmd = "docker run -it --rm --entrypoint /bin/sh " \
              "{container} -c \"/opt/nifi/nifi-toolkit-current/bin/cli.sh {cmd} -ot json" \
            .format(container=container, cmd=command, endpt=endpoint)
    else:
        cmd = "/opt/nifi/nifi-toolkit-current/bin/cli.sh {cmd} --baseUrl {endpt} -ot json" \
            .format(cmd=command, endpt=endpoint)
    for c in commands:
        cmd = cmd + " && /opt/nifi/nifi-toolkit-current/bin/cli.sh {cmd}    -ot json".format(cmd=c, endpt=endpoint)
    cmd = cmd + "\""
    return __process_output(cmd)


def call_cmd(container, endpoint, command):
    cmd = None
    if container:
        cmd = "docker run -it --rm --entrypoint /opt/nifi/nifi-toolkit-current/bin/cli.sh " \
              "{container} {cmd} --baseUrl {endpt} -ot json" \
            .format(container=container, cmd=command, endpt=endpoint)
    else:
        cmd = "/opt/nifi/nifi-toolkit-current/bin/cli.sh {cmd} --baseUrl {endpt} -ot json" \
            .format(cmd=command, endpt=endpoint)
    return __process_output(cmd)


def call_api(endpoint, method, path, data=None):
    url = "{}/nifi-api/{}".format(endpoint, path)
    if method.casefold() == 'delete':
        requests.delete(url)
    elif method.casefold() == 'post':
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        response = requests.post(url=url, headers=headers, data=json.dumps(data))
        if response.status_code != 201:
            return response.text
        else:
            return json.loads(response.text)


def __process_output(cmd):
    cmd_output = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='UTF-8')
    response = cmd_output.communicate()[0].strip()
    if response.startswith("ERROR:"):
        print(response)
        sys.exit(-1)
    elif __is_uuid(response):
        return response
    elif not response == "OK" and not response == "":
        return json.loads(response)
    else:
        return None


def __is_uuid(response):
    return bool(re.match("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", response))

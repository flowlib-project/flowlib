def extract_processors(processors: list) -> list:
    _data = []

    for processor in processors:
        build_processor = {
            "name": processor["name"],
            "type": processor["componentType"].lower(),
            "config": {
                "package_id": processor["type"],
                "properties": processor["properties"]
            }
        }

        if processor["autoTerminatedRelationships"]:
            build_processor["config"].update(
                {"auto_terminated_relationships": processor["autoTerminatedRelationships"]})

        _data.append(build_processor)

    return _data


def extract_remote_process_group(remote_processor_groups: list) -> list:
    _data = []

    for remoteProcessGroup in remote_processor_groups:
        build_remote_process_group = {
            "name": remoteProcessGroup["name"].replace(" ", "_"),
            "type": remoteProcessGroup["componentType"].lower(),
            "config": {
                "target_uri": remoteProcessGroup["targetUri"]
            }
        }

        _data.append(build_remote_process_group)
    return _data


def extract_input_ports(input_ports: list) -> list:
    _data = []

    for inputPort in input_ports:
        _data.append({"name": inputPort["name"], "type": inputPort["type"].lower()})

    return _data


def extract_output_ports(output_ports: list) -> list:
    _data = []

    for outputPort in output_ports:
        _data.append({"name": outputPort["name"], "type": outputPort["type"].lower()})

    return _data


def extract_controller_services(controller_services: list) -> list:
    _data = []

    for controller_service in controller_services:
        build_controller_service = {
            "name": controller_service["name"],
            "config": {
                "package_id": controller_service["type"],
                "properties": controller_service["properties"]
            }
        }

        _data.append(build_controller_service)

    return _data


def multiple_resources_with_no_connections(data: dict) -> dict:
    """
    Flow will break if an output port exists without source connection
    """
    _tmp = {
        "canvas": []
    }

    if data["inputPorts"]:
        old_data = _tmp["canvas"]
        for inputPort in extract_input_ports(data["inputPorts"]):
            old_data.append(inputPort)

    if data["outputPorts"]:
        old_data = _tmp["canvas"]
        for outputPort in extract_output_ports(data["outputPorts"]):
            old_data.append(outputPort)

    if data["remoteProcessGroups"]:
        old_data = _tmp["canvas"]
        for remote_process_group in extract_remote_process_group(data["remoteProcessGroups"]):
            old_data.append(remote_process_group)

    if data["processors"]:
        old_data = _tmp["canvas"]
        for processor in extract_processors(data["processors"]):
            old_data.append(processor)

    return _tmp


def process_group_identity(data: dict) -> dict:
    content = {
        "version": 1.0
    }

    content.update({"name": data["name"]})

    if data["comments"]:
        content.update({"comments": data["comments"]})

    return content


def controller_services(data: dict) -> dict:
    if data["controllerServices"]:
        return {"controller_services": extract_controller_services(data["controllerServices"])}
    else:
        return {"controller_services": None}


def processor_group_variables(data: dict) -> dict:
    _data = {}

    if data["variables"]:
        _data.update(data["variables"])
        return {"global_vars": _data}
    else:
        return {"global_vars": None}


def build_connection_type(resource: dict, parent_processor_group: dict, child_processor_group: dict) -> list:
    _data = []

    connection_resources = [_x for _x in child_processor_group["connections"] if _x["source"]["id"] == resource["identifier"]]

    if connection_resources:
        for connection_resources_entry in connection_resources:
            source_entry_type, destination_entry_type = (connection_resources_entry["source"]["type"], connection_resources_entry["destination"]["type"])

            if source_entry_type == "INPUT_PORT" and destination_entry_type == "PROCESSOR":
                connection_record = {
                    "name": connection_resources_entry["destination"]["name"],
                    "back_pressure_data_size_threshold": connection_resources_entry["backPressureDataSizeThreshold"],
                    "back_pressure_object_threshold": connection_resources_entry["backPressureObjectThreshold"],
                    "flow_file_expiration": connection_resources_entry["flowFileExpiration"],
                    "load_balance_strategy": connection_resources_entry["loadBalanceStrategy"],
                }

                if connection_resources_entry["prioritizers"]:
                    connection_record[""] = connection_resources_entry["prioritizers"]

                _data.append(connection_record)

            elif source_entry_type == "PROCESSOR" and destination_entry_type == "PROCESSOR":
                connection_record = {
                    "name": connection_resources_entry["destination"]["name"],
                    "relationships": connection_resources_entry["selectedRelationships"],
                    "back_pressure_data_size_threshold": connection_resources_entry["backPressureDataSizeThreshold"],
                    "back_pressure_object_threshold": connection_resources_entry["backPressureObjectThreshold"],
                    "flow_file_expiration": connection_resources_entry["flowFileExpiration"],
                    "load_balance_strategy": connection_resources_entry["loadBalanceStrategy"],
                }

                if connection_resources_entry["prioritizers"]:
                    connection_record[""] = connection_resources_entry["prioritizers"]

                _data.append(connection_record)

            elif source_entry_type == "PROCESSOR" and destination_entry_type == "INPUT_PORT":
                connection_record = {
                    "name": [x["name"] for x in child_processor_group["processGroups"] if x["identifier"] == connection_resources_entry["destination"]["groupId"]][0],
                    "relationships": connection_resources_entry["selectedRelationships"],
                    "to_port": connection_resources_entry["destination"]["name"],
                    "back_pressure_data_size_threshold": connection_resources_entry["backPressureDataSizeThreshold"],
                    "back_pressure_object_threshold": connection_resources_entry["backPressureObjectThreshold"],
                    "flow_file_expiration": connection_resources_entry["flowFileExpiration"],
                    "load_balance_strategy": connection_resources_entry["loadBalanceStrategy"],
                }

                if connection_resources_entry["prioritizers"]:
                    connection_record[""] = connection_resources_entry["prioritizers"]

                _data.append(connection_record)

            elif source_entry_type == "PROCESSOR" and destination_entry_type == "OUTPUT_PORT":
                connection_record = {
                    "name": connection_resources_entry["destination"]["name"],
                    "relationships": connection_resources_entry["selectedRelationships"],
                    "back_pressure_data_size_threshold": connection_resources_entry["backPressureDataSizeThreshold"],
                    "back_pressure_object_threshold": connection_resources_entry["backPressureObjectThreshold"],
                    "flow_file_expiration": connection_resources_entry["flowFileExpiration"],
                    "load_balance_strategy": connection_resources_entry["loadBalanceStrategy"],
                }

                if connection_resources_entry["prioritizers"]:
                    connection_record[""] = connection_resources_entry["prioritizers"]

                _data.append(connection_record)

            else:
                print("missed one..")
                print(source_entry_type, destination_entry_type)

    return _data


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


def extract_processors_with_connections(parent_data: dict, child_data: dict) -> list:
    _data = []

    for processor in child_data["processors"]:
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

        connections = build_connection_type(processor, parent_data, child_data)

        if connections:
            build_processor.update({"connections": connections})

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


def extract_input_ports_with_connections(parent_data: dict, child_data: dict) -> list:
    _data = []

    for inputPort in child_data["inputPorts"]:
        build_inputPort = {
            "name": inputPort["name"],
            "type": inputPort["componentType"].lower()
        }

        connections = build_connection_type(inputPort, parent_data, child_data)

        if connections:
            build_inputPort.update({"connections": connections})

        _data.append(build_inputPort)

    return _data


def extract_output_ports(output_ports: list) -> list:
    _data = []

    for outputPort in output_ports:
        _data.append({"name": outputPort["name"], "type": outputPort["type"].lower()})

    return _data


def extract_output_ports_with_connections(parent_data: dict, child_data: dict) -> list:
    _data = []

    for outputPort in child_data["outputPorts"]:
        build_outputPort = {
            "name": outputPort["name"],
            "type": outputPort["componentType"].lower()
        }

        connections = build_connection_type(outputPort, parent_data, child_data)

        if connections:
            build_outputPort.update({"connections": connections})

        _data.append(build_outputPort)

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


def multiple_resources_with_connections(parent_process_group_data=None, child_process_group_data=None) -> dict:
    _tmp = {
        "canvas": []
    }

    if child_process_group_data["inputPorts"]:
        old_data = _tmp["canvas"]
        for inputPort in extract_input_ports_with_connections(parent_process_group_data, child_process_group_data):
            old_data.append(inputPort)

    if child_process_group_data["outputPorts"]:
        old_data = _tmp["canvas"]
        for outputPort in extract_output_ports_with_connections(parent_process_group_data, child_process_group_data):
            old_data.append(outputPort)

    # if child_process_group_data["remoteProcessGroups"]:
    #     old_data = _tmp["canvas"]
    #     for remote_process_group in extract_remote_process_group(data["remoteProcessGroups"]):
    #         old_data.append(remote_process_group)

    if child_process_group_data["processors"]:
        old_data = _tmp["canvas"]
        for processor in extract_processors_with_connections(parent_process_group_data, child_process_group_data):
            old_data.append(processor)

    return _tmp


def processor_group_connection(parent_pg: dict, child_pg: dict) -> list:
    _data = []

    for connections in [_x for _x in parent_pg["connections"] if _x["source"]["groupId"] == child_pg["identifier"]]:
        source_entry_type, destination_entry_type = (connections["source"]["type"], connections["destination"]["type"])
        if source_entry_type == "OUTPUT_PORT" and destination_entry_type == "PROCESSOR":
            connection_record = {
                "name": connections["destination"]["name"],
                "from_port": connections["source"]["name"],
                "back_pressure_data_size_threshold": connections["backPressureDataSizeThreshold"],
                "back_pressure_object_threshold": connections["backPressureObjectThreshold"],
                "flow_file_expiration": connections["flowFileExpiration"],
                "load_balance_strategy": connections["loadBalanceStrategy"],
            }

            if connections["prioritizers"]:
                connection_record[""] = connections["prioritizers"]

            _data.append(connection_record)

        if source_entry_type == "OUTPUT_PORT" and destination_entry_type == "INPUT_PORT":
            connection_record = {
                "name": [x["name"] for x in parent_pg["processGroups"] if x["identifier"] == connections["destination"]["groupId"]][0],
                "from_port": connections["source"]["name"],
                "to_port": connections["destination"]["name"],
                "back_pressure_data_size_threshold": connections["backPressureDataSizeThreshold"],
                "back_pressure_object_threshold": connections["backPressureObjectThreshold"],
                "flow_file_expiration": connections["flowFileExpiration"],
                "load_balance_strategy": connections["loadBalanceStrategy"],
            }

            if connections["prioritizers"]:
                connection_record[""] = connections["prioritizers"]

            _data.append(connection_record)

        else:
            # print("missed one..")
            # print(source_entry_type, destination_entry_type)
            pass

    return _data


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


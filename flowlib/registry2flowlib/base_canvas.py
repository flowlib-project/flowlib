import yaml
import json

class CONSTRUCTBASE:
    flow_file_conten = ''
    output_format = ""
    processor_groups = []
    root_pg_yaml = {
        "canvas": [],
        "version": 1.0
    }

    def return_normalized_pg(self, data: list) -> dict:
        return [data[_root_key] for _root_key in [_pg for _pg in data]][0]

    def write_content_to_file(self, content: dict, file_location: str) -> None:
        if self.output_format == "yaml":
            with open(file_location, 'w') as outfile:
                yaml.dump(content, outfile, default_flow_style=False)

        else:
            json_obj = json.dumps(content, sort_keys=True, indent=2)
            with open(file_location, 'w') as outfile:
                outfile.write(json_obj)

    def append_to_root_pg_yaml(self, **kwargs) -> None:
        root_key = [x for x in kwargs][0]

        if kwargs[root_key]:
            if "pg_name" == root_key:
                self.root_pg_yaml.update(kwargs[root_key])

            elif "controller_services" == root_key:
                self.root_pg_yaml.update({root_key: kwargs[root_key]})

            elif "processors" == root_key:
                old_data = self.root_pg_yaml["canvas"]
                for processor in kwargs[root_key]:
                    old_data.append(processor)

            elif "inputPorts" == root_key and kwargs[root_key] is not None:
                old_data = self.root_pg_yaml["canvas"]
                for ports in kwargs[root_key]:
                    old_data.append(ports)

            elif "outputPorts" == root_key and kwargs[root_key] is not None:
                for _port in kwargs[root_key]:
                    self.root_pg_yaml["canvas"].append(_port)

            elif "remote-process-groups" == root_key and kwargs[root_key] is not None:
                old_data = self.root_pg_yaml["canvas"]
                for _rp in kwargs[root_key]:
                    old_data.append(_rp)

    def pg_name(self, content: dict) -> dict:
        return {"pg_name": {"name": content["name"]}}

    def controller_services(self, content: dict) -> dict:
        controllers = []
        if content["controllerServices"]:
            for controller in content["controllerServices"]:
                controller_services = {
                    "name": controller["name"],
                    "config": {
                        "package_id": controller["type"],
                        "properties": controller["properties"]
                    }
                }
                controllers.append(controller_services)

            return {"controller_services": controllers}
        else:
            return {"controller_services": None}

    def input_ports(self, content: dict) -> dict:
        inputPorts = []

        if content["inputPorts"]:
            ports = [{"type": str(x["componentType"]).lower(), "groupId": x["groupIdentifier"],
                      "identifier": x["identifier"], "name": x["name"]} for x in content["inputPorts"]]
            for port in ports:
                if content["connections"]:
                    _pConnections = [x for x in content["connections"] if
                                     x["source"]["groupId"] == port["groupId"] and x["source"]["name"] == port["name"]]
                    if _pConnections:
                        for _connection in _pConnections:
                            _con = {
                                "name": port["name"],
                                "type": port["type"],
                                "connections": [{"name": _connection["destination"]["name"]}]
                            }
                            inputPorts.append(_con)
                    else:
                        inputPorts.append({"type": port["type"], "name": port["name"]})
                else:
                    inputPorts.append({"type": port["type"], "name": port["name"]})

        if inputPorts:
            return {"inputPorts": inputPorts}

        else:
            return {"inputPorts": None}

    def output_ports(self, content: dict) -> dict:
        outputPorts = []

        if content["outputPorts"]:
            ports = [{"type": str(x["componentType"]).lower(), "groupId": x["groupIdentifier"],
                      "identifier": x["identifier"], "name": x["name"]} for x in content["outputPorts"]]

            for port in ports:
                outputPorts.append({"name": port["name"], "type": port["type"]})

        if outputPorts:
            return {"outputPorts": outputPorts}
        else:
            return {"outputPorts": None}

    def components_with_no_connections_in_canvas(self, processors: list) -> list:
        current_local_process_group_connections = []
        _processors = []

        for _processor_group in self.processor_groups:
            _normalized_data = self.return_normalized_pg(_processor_group)
            current_local_process_group_connections = _normalized_data["connections"]

        for _processor_ids in [x["identifier"] for x in processors]:
            if _processor_ids not in [x["source"]["id"] for x in current_local_process_group_connections]:
                for _entry in [x for x in processors if x["identifier"] == _processor_ids]:
                    _proc = {
                        "name": _entry["name"],
                        "type": _entry["componentType"].lower(),
                        "config": {
                            "package_id": _entry["type"],
                            "properties": _entry["properties"]
                        }
                    }

                    _processors.append(_proc)

        return _processors

    def extract_processor_name(self, match_groupId: list, data: list) -> str:
        for _a in data:
            for _s in _a:
                content = _a[_s]
                if content["identifier"] == match_groupId:
                    return content["name"]

    def append_connection(self, processor: dict, connection: dict) -> dict:
        if connection["source"]["type"] == "PROCESSOR" and connection["destination"]["type"] == "PROCESSOR" or \
                connection["source"]["type"] == "PROCESSOR" and connection["destination"]["type"] == "OUTPUT_PORT":
            if connection:
                _con = {
                    "connections": [
                        {
                            "name": connection["destination"]["name"],
                            "relationships": connection["selectedRelationships"]
                        }
                    ]
                }

                processor.update(_con)

                return processor

        elif connection["source"]["type"] == "PROCESSOR" and connection["destination"]["type"] == "INPUT_PORT":
            if connection:
                _con = {
                    "connections": [
                        {
                            "name": self.extract_processor_name(connection["destination"]["groupId"],
                                                                self.processor_groups),
                            "relationships": connection["selectedRelationships"],
                            "to_port": connection["destination"]["name"]
                        }
                    ]
                }

                processor.update(_con)

                return processor

    def connections_processor_2_processor(self, processor_connection: dict, processor_group: dict) -> dict:
        _processors = [x for x in processor_group["processors"] if x["identifier"] == processor_connection["source"]["id"]]

        for _processor_combine_connections in _processors:
            _extracted_process_data = {
                "name": _processor_combine_connections["name"],
                "type":  _processor_combine_connections["componentType"].lower(),
                "config": {
                    "package_id": _processor_combine_connections["type"],
                    "properties": _processor_combine_connections["properties"]
                }
            }

            if _processor_combine_connections["autoTerminatedRelationships"]:
                _extracted_process_data["config"].update(
                    {"auto_terminated_relationships": _processor_combine_connections["autoTerminatedRelationships"]})

            return self.append_connection(_extracted_process_data, processor_connection)

    def connections_processor_2_child_pg(self, processor_connection: dict, processor_group: dict) -> dict:
        _processors = [x for x in processor_group["processors"] if
                       x["identifier"] == processor_connection["source"]["id"]]
        for _processor_combine_connections in _processors:
            _extracted_process_data = {
                "name": _processor_combine_connections["name"],
                "type":  _processor_combine_connections["componentType"].lower(),
                "config": {
                    "package_id": _processor_combine_connections["type"],
                    "properties": _processor_combine_connections["properties"]
                }
            }

            if _processor_combine_connections["autoTerminatedRelationships"]:
                _extracted_process_data["config"].update(
                    {"auto_terminated_relationships": _processor_combine_connections["autoTerminatedRelationships"]})

            return self.append_connection(_extracted_process_data, processor_connection)

    def connections_child_pg_2_child_pg(self, processor_connection: dict, processor_group: dict) -> dict:
        _connection = {
            f'for_processor_{self.extract_processor_name(processor_connection["source"]["groupId"], self.processor_groups)}': {
                "connections": {
                    "from_port": processor_connection["source"]["name"],
                    "to_port": processor_connection["destination"]["name"],
                    "name": self.extract_processor_name(processor_connection["destination"]["groupId"],
                                                        self.processor_groups)
                }
            }
        }

        return _connection

    def connections_child_pg_2_processor(self, processor_connection: dict, processor_group: dict) -> dict:
        # print([x for x in processor_group["processors"] if x["identifier"] == processor_connection["source"]["id"]])
        # _processors = [x for x in processor_group["processors"] if x["identifier"] == processor_connection["source"]["id"]]

        # print(json.dumps(processor_connection, indent=2, sort_keys=True))
        pass

    def remote_processor_groups_with_no_connections(self, remote_processors: list) -> list:
        _grouped = []

        for _remote_processors in remote_processors:
            _rp = {
                "name": _remote_processors["name"].replace(" ", "_"),
                "type": _remote_processors["componentType"].lower(),
                "config": {
                    "target_uri":  _remote_processors["targetUri"]
                }
            }
            _grouped.append(_rp)

        return _grouped

    def remote_processor_groups(self, processor_group: dict) -> dict:
        _remote_processor_groups = processor_group["remoteProcessGroups"]
        return {"remote-process-groups": self.remote_processor_groups_with_no_connections(_remote_processor_groups)}

    def connections(self, processor_group: dict) -> dict:
        canvas = []
        core_procesgroup_connections = []
        _processor_connections = processor_group["connections"]
        _processors = processor_group["processors"]
        _remote_processor_groups = processor_group["remoteProcessGroups"]

        if _processor_connections:
            for _connection in _processor_connections:
                if _connection["source"]["type"] == "PROCESSOR" and _connection["destination"]["type"] == "PROCESSOR":
                    # print("1")
                    _data = self.connections_processor_2_processor(_connection, processor_group)
                    if _data:
                        canvas.append(_data)

                elif _connection["source"]["type"] == "PROCESSOR" and _connection["destination"]["type"] == "INPUT_PORT":
                    _data = self.connections_processor_2_child_pg(_connection, processor_group)
                    # print("2")
                    if _data:
                        canvas.append(_data)

                elif _connection["source"]["type"] == "INPUT_PORT" and _connection["destination"]["type"] == "PROCESSOR":
                    _data = self.connections_child_pg_2_processor(_connection, processor_group)
                    # print("3")
                    if _data:
                        canvas.append(_data)

                elif _connection["source"]["type"] == "PROCESSOR" and _connection["destination"]["type"] == "OUTPUT_PORT":
                    _data = self.connections_processor_2_child_pg(_connection, processor_group)
                    # print("4")
                    if _data:
                        canvas.append(_data)

                elif _connection["source"]["type"] == "OUTPUT_PORT" and _connection["destination"]["type"] == "INPUT_PORT" or \
                        _connection["source"]["type"] == "INPUT_PORT" and _connection["destination"]["type"] == "OUTPUT_PORT":
                    # print("5")
                    core_procesgroup_connections.append(self.connections_child_pg_2_child_pg(_connection, processor_group))

                else:
                    print(_connection["source"]["type"], _connection["destination"]["type"])
                    print("This didn't not get caught...")

            for _solo_processor in self.components_with_no_connections_in_canvas(_processors):
                if not [x for x in canvas if _solo_processor["name"] in x["name"]]:
                    canvas.append(_solo_processor)

            if canvas:
                return {"processors": canvas}
            else:
                return {"processors": None}

        elif _processors:
            # print("6")
            return {"processors": self.components_with_no_connections_in_canvas(_processors)}

        elif _remote_processor_groups:
            # print("7")
            return {"remote-process-groups": self.remote_processor_groups_with_no_connections(_remote_processor_groups)}

        else:
            return {"processors": None}

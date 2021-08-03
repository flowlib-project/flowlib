from nipyapi.utils import dump
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
            print(inputPorts)
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

    def connections_processor_2_processor(self, processor_connections: list, processors: list) -> dict:
        _tmp_processors = []

        for _x in processors:
            processorName = _x["name"]
            componentType = _x["componentType"]
            javaClassType = _x["type"]
            configProp = _x["properties"]
            identifier = _x["identifier"]

            processor = {
                "name": processorName,
                "type": str(componentType).lower(),
                "config": {
                    "package_id": javaClassType,
                    "properties": configProp
                }
            }

            if [{"name": x["destination"]["name"], "relationships": x["selectedRelationships"]} for x in
                processor_connections if x["source"]["id"] == identifier]:
                processor["connections"] = [
                    {"name": x["destination"]["name"], "relationships": x["selectedRelationships"]} for
                    x in processor_connections if x["source"]["id"] == identifier]

            if _x["autoTerminatedRelationships"]:
                processor["config"].update({"auto_terminated_relationships": _x["autoTerminatedRelationships"]})

            _tmp_processors.append(processor)

        return _tmp_processors

    def extract_processor_name(self, match_id: list, data: dict) -> str:
        if match_id == data["identifier"]:
            return ([x["name"] for x in data["processGroups"] if x["groupIdentifier"] == match_id][0])
        else:
            print('nope')

    def connections_processor_2_child_pg(self, processor_connections: dict, processors: list) -> dict:
        _tmp_processors = []

        for _x in processors:
            processorName = _x["name"]
            componentType = _x["componentType"]
            javaClassType = _x["type"]
            configProp = _x["properties"]
            identifier = _x["identifier"]

            processor = {
                "name": processorName,
                "type": str(componentType).lower(),
                "config": {
                    "package_id": javaClassType,
                    "properties": configProp
                }
            }

            _t = [{"name": self.extract_processor_name(_x["groupIdentifier"], self.flow_file_conten["flowContents"]),
                   "to_port": x["destination"]["name"], "relationships": x["selectedRelationships"]} for x in
                  processor_connections if x["source"]["id"] == identifier]
            if _t:
                return {processorName: _t}

    def components_with_no_connections_in_canvas(self, data: list) -> dict:
        components = []
        for processor in data:
            processorName = processor["name"]
            componentType = processor["componentType"]
            javaClassType = processor["type"]
            configProp = processor["properties"]
            identifier = processor["identifier"]

            processor = {
                "name": processorName,
                "type": str(componentType).lower(),
                "config": {
                    "package_id": javaClassType,
                    "properties": configProp
                }
            }

            components.append(processor)

            return processor

    def connections(self, content: dict) -> dict:
        canvas = []

        if content["connections"]:
            _t = self.connections_processor_2_processor([x for x in content["connections"] if
                                                    x["source"]["type"] == "PROCESSOR" and x["destination"][
                                                        "type"] == "PROCESSOR"], content["processors"])

            _q = self.connections_processor_2_child_pg([x for x in content["connections"] if
                                                        x["source"]["type"] == "PROCESSOR" and x["destination"][
                                                            "type"] == "INPUT_PORT"], content["processors"])

            [canvas.append(x) for x in _t]

            if _q:
                for _x in [x for x in canvas if x["name"] == [x for x in _q][0]]:
                    if "connections" not in [y for y in _x]:
                        _x.update({"connections": [_q[[x for x in _q][0]][0]]})

            return {"processors": canvas}
        else:
            processors = self.components_with_no_connections_in_canvas(content["processors"])
            if processors:
                return {"processors": processors}
            else:
                return {"processors": None}
class CONSTRUCTBASE:
    processor_groups = []
    root_pg_yaml = {
        "version": 1.0
    }

    def append_to_root_pg_yaml(self, **kwargs) -> None:
        root_key = [x for x in kwargs][0]

        if "pg_name" == root_key:
            self.root_pg_yaml.update(kwargs[root_key])

        elif "controller_services" == root_key:
            self.root_pg_yaml.update({root_key: kwargs[root_key]})

        elif "processors" == root_key:
            self.root_pg_yaml.update({"canvas": kwargs[root_key]})

        elif "inputPortConnection" == root_key and kwargs[root_key] is not None:
            self.root_pg_yaml["canvas"].append(kwargs[root_key])

        elif "allOutputPorts" == root_key and kwargs[root_key] is not None:
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
        if content["inputPorts"]:
            input_ports = [{"type": x["componentType"].lower(), "name": x["name"], "identifier": x["identifier"]} for x in content["inputPorts"]]

            for _input_identity in input_ports:
                _connection = [x for x in [x for x in content["connections"]] if x["source"]["id"] == _input_identity["identifier"]][0]
                inputPortInfo = {
                    "name": _input_identity["name"],
                    "type": _input_identity["type"],
                    "connections": [{"name": _connection["destination"]["name"]}]
                }
                return {"inputPortConnection": inputPortInfo}
        else:
            return {"inputPortConnection": inputPortInfo}

    def output_ports(self, content: dict) -> dict:
        if content["outputPorts"]:
            output_ports = [{"type": x["componentType"].lower(), "name": x["name"]} for x in content["outputPorts"]]
            return {"allOutputPorts": output_ports}
        else:
            return {"allOutputPorts": None}

    def processor_connection(self, connections, processor_id, processor_type, processor_name):
        found_connections = []

        for _connection in connections:
            if _connection["source"]["id"] == processor_id and _connection["source"]["name"] == processor_name and \
                    _connection["source"]["type"] == processor_type:
                found_connections.append(_connection)

        needed_fields = [{"relationships": x["selectedRelationships"], "name": x["destination"]["name"]} for x in
                         found_connections]
        return needed_fields

    def processors(self, content: dict) -> dict:
        processors = []

        if content["processors"]:
            for processor in content["processors"]:
                processor_data = {
                    "name": processor["name"],
                    "type": str(processor["componentType"]).lower(),
                    "config": {
                        "package_id": processor["type"],
                        "properties": processor["properties"]
                    },
                    "connections": self.processor_connection(content["connections"], processor["identifier"],
                                                             processor["componentType"], processor["name"])
                }

                processors.append(processor_data)
        return {"processors": processors}
import json
from nipyapi.utils import dump


class CONVERTION:
    output_format = ""
    registry_file_content = ''
    skeleton = {
        "name": '',
        "version": 1.0,
        "comments": "",
        "canvas": []
    }
    rec_counter = 0


    def __init__(self, registry_content_file):
        with open(registry_content_file, "r") as rf:
            self.registry_file_content = json.loads(rf.read())
            rf.close()

    def append_to_skeleton(self, **kwargs):
        main_key = [x for x in kwargs][0]
        if 'main' == main_key:
            self.skeleton["name"] = kwargs["main"]["name"]
            self.skeleton["comments"] = kwargs["main"]["comments"]

        elif 'controller_services' == main_key:
            self.skeleton[main_key] = kwargs[main_key]

        elif 'canvas' == main_key:
            for _x in kwargs[main_key]:
                self.skeleton[main_key].append(_x)

    def get_processor_connection(self, connections, processor_id, processor_type, processor_name):
        found_connections = []

        for _connection in connections:
            if _connection["source"]["id"] == processor_id and _connection["source"]["name"] == processor_name and _connection["source"]["type"] == processor_type:
                found_connections.append(_connection)
                # print(json.dumps(_connection, sort_keys=True, indent=2))

        needed_fields = [{"relationships": x["selectedRelationships"], "name": x["destination"]["name"], "to_port": x["destination"]["name"]} for x in found_connections]
        return needed_fields

    def build_flowlib_json_yaml_content(self, data_content, output_syntax_option):
        self.output_format = output_syntax_option
        root_content = data_content["flowContents"]
        self.build_processor_group([root_content])

    def get_external_controllers(self, body):
        controllers = []

        if len(body["controllerServices"]) > 0:
            for controller in body["controllerServices"]:
                controller_services = {
                    "name": controller["name"],
                    "config": {
                        "package_id": controller["type"],
                        "properties": controller["properties"]
                    }
                }
                controllers.append(controller_services)
        return {"controller_services": controllers}

    def get_processors(self, body):
        processors = []

        if len(body["processors"]) > 0:
            for processor in body["processors"]:
                processor_data = {
                    # "position": processor["position"],
                    "name": processor["name"],
                    "type": str(processor["componentType"]).lower(),
                    "config": {
                        "package_id": processor["type"],
                        "properties": processor["properties"]
                    },
                    "connections": self.get_processor_connection(body["connections"], processor["identifier"], processor["componentType"], processor["name"])
                }

                processors.append(processor_data)

        return {"canvas": processors}

    def get_pg_headers(self, body):
        info = {
            "name": body["name"],
            "comments": body["comments"]
        }

        return {"main": info}

    def get_out_in_ports(self, body):
        input_ports = [{"type": x["componentType"].lower(), "name": x["name"]} for x in body["inputPorts"]]
        output_ports = [{"type": x["componentType"].lower(), "name": x["name"]} for x in body["outputPorts"]]
        total = output_ports + input_ports
        return {"canvas": total}

    def build_processor_group(self, data):
        for _pg in data:
            self.append_to_skeleton(**self.get_pg_headers(_pg))
            self.append_to_skeleton(**self.get_external_controllers(_pg))
            self.append_to_skeleton(**self.get_processors(_pg))
            self.append_to_skeleton(**self.get_out_in_ports(_pg))

            print(dump(self.skeleton, mode=self.output_format))
            new_data = _pg["processGroups"]
            self.build_processor_group(new_data)
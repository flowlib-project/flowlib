import json

from nipyapi.utils import dump
from .base_canvas import CONSTRUCTBASE
import os
import yaml


class CONSTRUCTIONCOMPONENT(CONSTRUCTBASE):
    flow_file_conten = ''
    output_format = ""
    _main_canvas_structure = {}
    main_canvas_structure = []
    _component_canvas_structure = {}

    def relationships(self, parent_processor: list, child_processor: list) -> None:
        for _child in child_processor:
            self._main_canvas_structure = {}
            self.build_child_canvas_components(_child, parent_processor)
            self.main_canvas_structure.append(self._main_canvas_structure)

    def create_component_file(self, component_file: str) -> None:
        if "components" not in os.listdir():
            os.mkdir("components")

        dirs = 'components'

        directories = [x if "." not in x else None for x in component_file.split("/")]

        for directory in directories[:-1]:
            if directory and directory not in os.listdir(dirs):
                dirs = dirs + f"/{directory}"
                os.makedirs(f"{dirs}")

        dirs = 'components'
        self.write_content_to_file(self._component_canvas_structure, f"{dirs}/{component_file}")

    def append_to_main_canvas_structure(self, data: dict) -> None:
        if data is not None:
            self._main_canvas_structure.update(data)

    def append_to_component_canvas(self, **kwargs: dict) -> None:
        root_key = [x for x in kwargs][0]

        if kwargs[root_key]:
            if "processors" == root_key:
                if "process_group" in [x for x in self._component_canvas_structure]:
                    self._component_canvas_structure.update({"process_group": kwargs[root_key]})
                else:
                    self._component_canvas_structure["process_group"] = kwargs[root_key]

            elif "componentGroupName" == root_key:
                name = str(kwargs[root_key]).split("/")[1].split(".")[0]
                self._component_canvas_structure.update({"name": name.replace("_", "-")})

            elif "inputPorts" == root_key:
                for _x in kwargs[root_key]:
                    _current_process_group_data = self._component_canvas_structure["process_group"]
                    _current_process_group_data.append(_x)
                    self._component_canvas_structure.update({"process_group": _current_process_group_data})

            elif "outputPorts" == root_key:
                for _x in kwargs[root_key]:
                    _current_process_group_data = self._component_canvas_structure["process_group"]
                    _current_process_group_data.append(_x)
                    self._component_canvas_structure.update({"process_group": _current_process_group_data})
        else:
            if root_key == "processors":
                self._component_canvas_structure.update({"process_group": []})

    def return_normalized_pg(self, data: list) -> dict:
        return [data[_root_key] for _root_key in [_pg for _pg in data]][0]

    def core_pg_connections(self, child_data: dict, parent_data: list) -> dict:
        _pg = self.return_normalized_pg(child_data)

        for _single_data_payload in parent_data:
            for _root_key in _single_data_payload:
                if _single_data_payload[_root_key]["identifier"] == _pg["groupIdentifier"]:
                    _parent_processor_group = _single_data_payload[_root_key]
                    for _connections in _parent_processor_group["connections"]:

                        if _connections["source"]["type"] == "PROCESSOR":
                            if _connections["source"]["groupId"] == _pg["identifier"] and _connections["groupIdentifier"] == \
                                    _pg["groupIdentifier"]:
                                connections = {
                                    "name": _connections["destination"]["name"],
                                    "from_port": _connections["source"]["name"],
                                }
                                return {"connections": [connections]}

                        elif _connections["source"]["type"] == "OUTPUT_PORT":
                            if _connections["source"]["groupId"] == _pg["identifier"] and _connections["groupIdentifier"] == \
                                    _pg["groupIdentifier"]:
                                connections = {
                                    "name": self.extract_processor_name(_connections["destination"]["groupId"], self.processor_groups),
                                    "from_port": _connections["source"]["name"],
                                    "to_port": _connections["destination"]["name"],
                                }
                                return {"connections": [connections]}

    def core_pg_vars(self, data: dict) -> dict:
        _pg = self.return_normalized_pg(data)

        if _pg["variables"]:
            return {"vars": [_pg["variables"]]}

    def core_pg_parameters(self, data: dict) -> dict:
        processor_root_canvas_info = {}

        _pg = self.return_normalized_pg(data)
        processor_root_canvas_info.update({"name": _pg["name"]})
        processor_root_canvas_info.update(
            {"component_path": f"common/{str(_pg['name']).replace('-', '_')}_component.{self.output_format}"})
        processor_root_canvas_info.update({"type": "process_group"})
        if processor_root_canvas_info:
            return processor_root_canvas_info

    def build_child_canvas_components(self, child_content: dict, parent_content: list) -> None:
        """
        Processor Group can not be empty or it will fail
        """
        self.append_to_main_canvas_structure(self.core_pg_parameters(child_content))
        self.append_to_main_canvas_structure(self.core_pg_vars(child_content))
        self.append_to_main_canvas_structure(self.core_pg_connections(child_content, parent_content))

        self.append_to_component_canvas(**{"componentGroupName": self._main_canvas_structure["component_path"]})
        self.append_to_component_canvas(**self.controller_services(self.return_normalized_pg(child_content)))
        self.append_to_component_canvas(**self.connections(self.return_normalized_pg(child_content)))
        # print(self.connections(self.return_normalized_pg(child_content)))
        self.append_to_component_canvas(**self.input_ports(self.return_normalized_pg(child_content)))
        self.append_to_component_canvas(**self.output_ports(self.return_normalized_pg(child_content)))

        self.create_component_file(self._main_canvas_structure["component_path"])
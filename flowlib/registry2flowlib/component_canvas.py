from nipyapi.utils import dump

class CONSTRUCTIONCOMPONENT:
    _main_canvas_structure = {}
    main_canvas_structure = []

    def __init__(self):
        pass

    def relationships(self, parent_processor: list, child_processor: list) -> None:
        for _child in child_processor:
            self._main_canvas_structure = {}
            self.build_child_canvas(_child, parent_processor)
            self.main_canvas_structure.append(self._main_canvas_structure)

    def append_to_main_canvas_structure(self, data: dict) -> None:
        if data is not None:
            self._main_canvas_structure.update(data)

    def return_normalized_pg(self, data: list) -> dict:
        return [data[_root_key] for _root_key in [_pg for _pg in data]][0]

    def core_pg_connections(self, child_data: dict, parent_data: list) -> dict:
        _pg = self.return_normalized_pg(child_data)

        for _single_data_payload in parent_data:
            for _root_key in _single_data_payload:
                if _single_data_payload[_root_key]["identifier"] == _pg["groupIdentifier"]:
                    _parent_processor_group = _single_data_payload[_root_key]
                    for _connections in _parent_processor_group["connections"]:
                        if _connections["source"]["groupId"] == _pg["identifier"] and _connections["groupIdentifier"] == _pg["groupIdentifier"]:
                            connections = {
                                "name": _connections["destination"]["name"],
                                "from_port": _connections["source"]["name"],
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
        processor_root_canvas_info.update({"component_path": f"components/{_pg['name']}-component.yaml"})
        processor_root_canvas_info.update({"type": "process_group"})
        if processor_root_canvas_info:
            return processor_root_canvas_info

    def build_child_canvas(self, child_content: dict, parent_content: list) -> None:
        self.append_to_main_canvas_structure(self.core_pg_parameters(child_content))
        self.append_to_main_canvas_structure(self.core_pg_vars(child_content))
        self.append_to_main_canvas_structure(self.core_pg_connections(child_content, parent_content))
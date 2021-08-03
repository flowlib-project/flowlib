import json
from nipyapi.utils import dump, fs_write
from .base_canvas import CONSTRUCTBASE
from .component_canvas import CONSTRUCTIONCOMPONENT


class CONVERTION:
    flow_file_conten = ''
    processor_groups = []

    def __init__(self, registry_content_file, output_format):
        with open(registry_content_file, "r") as rf:
            self.flow_file_conten = json.loads(rf.read())
            rf.close()

        self.base_structure = CONSTRUCTBASE()
        self.base_structure.output_format = output_format
        self.base_structure.flow_file_conten = self.flow_file_conten

        self.comp_structure = CONSTRUCTIONCOMPONENT()
        self.comp_structure.output_format = output_format
        self.comp_structure.flow_file_conten = self.flow_file_conten

        self.recursively_find_processor_groups([self.flow_file_conten["flowContents"]], 0)

        relationship_levels = list(set([[int(y.split("_")[1]) for y in x][0] for x in self.processor_groups]))

        self.base_pg_specifics(
            [x for x in [x for x in self.processor_groups] if int(str(x).split("_")[1]) == relationship_levels[0]][0])

        for relationship in relationship_levels[1:]:
            self.comp_structure.relationships(
                [y for y in [x for x in self.processor_groups] if int(str(y).split("_")[1]) == (relationship - 1)],
                [y for y in [x for x in self.processor_groups] if int(str(y).split("_")[1]) == relationship]
            )
        self.merge_main_canvas_component_with_base_structure(self.comp_structure.main_canvas_structure)

        # print(dump(self.base_structure.root_pg_yaml, mode=output_format))
        self.base_structure.write_content_to_file(self.base_structure.root_pg_yaml, f"./flow.{output_format}")

    def merge_main_canvas_component_with_base_structure(self, data: list) -> None:
        for _data in data:
            self.base_structure.root_pg_yaml["canvas"].append(_data)

    def recursively_find_processor_groups(self, processor_data :list, pg_counter :int) -> None:
        for _pg in processor_data:
            _tmp_pg = dict(_pg)

            if _tmp_pg["processGroups"]:
                del _tmp_pg["processGroups"]

            self.processor_groups.append({f'canvasLevel_{pg_counter}_{_pg["name"]}': _tmp_pg})

            if [x for x in _pg["processGroups"]]:
                self.recursively_find_processor_groups(_pg["processGroups"], (pg_counter + 1))

    def base_pg_specifics(self, content: dict) -> None:
        """
        No input or output ports can be created in the root canvas
        """
        _pg_content = content[[x for x in content][0]]

        self.base_structure.append_to_root_pg_yaml(**self.base_structure.pg_name(_pg_content))
        self.base_structure.append_to_root_pg_yaml(**self.base_structure.controller_services(_pg_content))
        self.base_structure.append_to_root_pg_yaml(**self.base_structure.connections(_pg_content))
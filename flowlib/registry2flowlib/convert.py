import json
from nipyapi.utils import dump
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
        self.comp_structure = CONSTRUCTIONCOMPONENT()

        self.recursively_find_processor_groups([self.flow_file_conten["flowContents"]], 0)


        relationship_levels = list(set([[int(y.split("_")[1]) for y in x][0] for x in self.processor_groups]))

        self.base_pg_specifics(
            [x for x in [x for x in self.processor_groups] if int(str(x).split("_")[1]) == relationship_levels[0]][0])

        for relationship in relationship_levels[1:]:
            self.comp_structure.ingest_relationships(
                [y for y in [x for x in self.processor_groups] if int(str(y).split("_")[1]) == (relationship - 1)],
                [y for y in [x for x in self.processor_groups] if int(str(y).split("_")[1]) == relationship]
            )

        # print(dump(self.base_structure.root_pg_yaml, mode=output_format))
        # print(dump(self.processor_groups, mode=output_format))

    def recursively_find_processor_groups(self, processor_data :list, pg_counter :int) -> None:
        for _pg in processor_data:
            _tmp_pg = dict(_pg)

            if _tmp_pg["processGroups"]:
                del _tmp_pg["processGroups"]

            self.processor_groups.append({f'canvasLevel_{pg_counter}_{_pg["name"]}': _tmp_pg})

            if [x for x in _pg["processGroups"]]:
                self.recursively_find_processor_groups(_pg["processGroups"], (pg_counter + 1))

    def base_pg_specifics(self, content: dict) -> None:
        _pg_content = content[[x for x in content][0]]

        self.base_structure.append_to_root_pg_yaml(**self.base_structure.pg_name(_pg_content))
        self.base_structure.append_to_root_pg_yaml(**self.base_structure.controller_services(_pg_content))
        self.base_structure.append_to_root_pg_yaml(**self.base_structure.processors(_pg_content))
        self.base_structure.append_to_root_pg_yaml(**self.base_structure.input_ports(_pg_content))
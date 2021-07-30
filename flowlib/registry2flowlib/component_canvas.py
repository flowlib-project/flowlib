class CONSTRUCTIONCOMPONENT:
    def ingest_relationships(self, parent_processor: list, child_processor: list) -> None:
        # print(parent_processor)
        for _x in parent_processor:
            for _y in _x:
                print(_y)
        print('')
        # print(child_processor)
        for _x in child_processor:
            for _y in _x:
                print(_y)
        print("*" * 20)
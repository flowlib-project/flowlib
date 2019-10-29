# -*- coding: utf-8 -*-

class FlowComponent:
    def __init__(self, raw, name, source_file, process_group, defaults=None, required_controllers=None, required_vars=None):
        """
        A reuseable component of a flow. Referenced by a ProcessGroup which is an instantiation of a FlowComponent
        """
        self.raw = raw
        self.name = name
        self.source_file = source_file
        self.process_group = process_group
        self.defaults = defaults or dict()
        self.required_controllers = required_controllers or dict()
        self.required_vars = required_vars or list()
        self._is_used = False

    def __repr__(self):
        return str(vars(self))

    def as_dict(self):
        return {
            'name': self.name,
            'source_file': self.source_file,
            'process_group': self.process_group,
            'defaults': self.defaults,
            'required_controllers': self.required_controllers,
            'required_vars': self.required_vars
        }

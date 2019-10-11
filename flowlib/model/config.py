# -*- coding: utf-8 -*-
import yaml

class FlowLibConfig:

    DEFAULT_CFG = '.flowlib.yml'
    DEFAULTS = {
        'component_dir': 'components',
        'nifi_endpoint': 'http://localhost:8080'
    }

    def __init__(self, **kwargs):
        """
        :type flow_yaml: str
        :type scaffold: str
        :type force: bool
        :type export: bool
        :type validate: bool
        :type deploy_reporting_tasks: bool
        :type component_dir: str
        :type nifi_endpoint: str
        :type max_timer_driven_threads: int
        :type max_event_driven_threads: int
        :type reporting_task_controllers: list(dict)
        :type reporting_tasks: list(dict)
        """
        # cli only flags
        self.flow_yaml = None
        self.scaffold = None
        self.force = None
        self.export = None
        self.deploy_reporting_tasks = None
        self.validate = None

        # file configs with flag overrides
        self.component_dir = kwargs.get('component_dir', FlowLibConfig.DEFAULTS['component_dir'])
        self.nifi_endpoint = kwargs.get('nifi_endpoint', FlowLibConfig.DEFAULTS['nifi_endpoint'])

        # file only configs
        self.max_timer_driven_threads = kwargs.get('max_timer_driven_threads')
        self.max_event_driven_threads = kwargs.get('max_event_driven_threads')
        self.reporting_task_controllers = kwargs.get('reporting_task_controllers', list())
        self.reporting_tasks = kwargs.get('reporting_tasks', list())

    def with_flag_overrides(self, flags):
        """
        Construct merge a config read from a yaml file with the provided cli flags
        :type flags: FlowLibConfig
        """
        flags = vars(flags)

        # remove any unset keys
        for k in list(flags.keys()):
            if not flags[k]:
                del flags[k]

        for k,v in flags.items():
            setattr(self, k, v)

        return self

    def __repr__(self):
        return str(self.__dict__)

    @staticmethod
    def new_from_file(stream):
        """
        Construct a FlowLibConfig from a yaml config file
        :param stream: A python file like object
        """
        d = yaml.safe_load(stream) or dict()
        return FlowLibConfig(**d)

# -*- coding: utf-8 -*-
import yaml

class FlowLibConfig:

    DEFAULT_CFG = '.flowlib.yml'
    DEFAULTS = {
        'component_dir': 'components',
        'nifi_endpoint': 'http://localhost:8080',
        'registry_endpoint': 'http://localhost:18080',
        'zookeeper_root_node': '/nifi',
        'zookeeper_acl': 'open',
        'docs_directory': 'docs',
        'max_timer_driven_threads': 5,
        'max_event_driven_threads': 10
    }

    def __init__(self, **kwargs):
        """
        :type flow_yaml: str
        :type deployment_json: str
        :type scaffold: str
        :type generate_docs: str
        :type force: bool
        :type export: str
        :type validate: bool
        :type configure_flow_controller: bool
        :type component_dir: str
        :type nifi_endpoint: str
        :type registry_endpoint: str
        :type zookeeper_connection: str
        :type zookeeper_root_node: str
        :type zookeeper_acl: str
        :type max_timer_driven_threads: int
        :type max_event_driven_threads: int
        :type reporting_task_controllers: list(dict)
        :type reporting_tasks: list(dict)
        """
        # cli only flags
        self.flow_yaml = None
        self.deployment_json = None
        self.scaffold = None
        self.generate_docs = None
        self.force = None
        self.export = None
        self.configure_flow_controller = None
        self.validate = None

        # file configs with flag overrides
        self.component_dir = kwargs.get('component_dir', FlowLibConfig.DEFAULTS['component_dir'])
        self.nifi_endpoint = kwargs.get('nifi_endpoint', FlowLibConfig.DEFAULTS['nifi_endpoint'])
        self.registry_endpoint = kwargs.get('registry_endpoint', FlowLibConfig.DEFAULTS['registry_endpoint'])
        self.zookeeper_connection = kwargs.get('zookeeper_connection')
        self.zookeeper_root_node = kwargs.get('zookeeper_root_node', FlowLibConfig.DEFAULTS['zookeeper_root_node'])
        self.zookeeper_acl = kwargs.get('zookeeper_acl', FlowLibConfig.DEFAULTS['zookeeper_acl'])
        self.container = kwargs.get('container', None)

        # file only configs
        self.docs_directory = kwargs.get('docs_directory', FlowLibConfig.DEFAULTS['docs_directory'])
        self.max_timer_driven_threads = kwargs.get('max_timer_driven_threads', FlowLibConfig.DEFAULTS['max_timer_driven_threads'])
        self.max_event_driven_threads = kwargs.get('max_event_driven_threads', FlowLibConfig.DEFAULTS['max_event_driven_threads'])
        self.reporting_task_controllers = kwargs.get('reporting_task_controllers', list())
        self.reporting_tasks = kwargs.get('reporting_tasks', list())

    def with_flag_overrides(self, flags):
        """
        Construct merge a config read from a yaml file with the provided cli flags
        :type flags: FlowLibConfig
        """
        flags = vars(flags)
        for k,v in flags.items():
            if flags.get(k):
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

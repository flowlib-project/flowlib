import argparse

class FlowGenCLI:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="Deploy a NiFi flow from YAML")
        self.parser.add_argument('--flow-yaml',
            nargs='?',
            type=argparse.FileType('r'),
            default='./flow.yaml',
            help='YAML file defining a NiFi flow')
        self.parser.add_argument('--nifi-address',
            type = str,
            default = 'localhost',
            help = 'Address of the NiFi API'
        )
        self.parser.add_argument('--nifi-port',
            type = str,
            default = '8080',
            help = 'HTTP port for the NiFi API'
        )
        self.config = self.parser.parse_args()

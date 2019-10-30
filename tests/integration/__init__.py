# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from contextlib import contextmanager, ExitStack

import flowlib.api
from flowlib.model import FlowLibException
from flowlib.nifi.rest import wait_for_nifi_api


@contextmanager
def tmp_project_dir(endpoint):
    """
    Returns the path to a new scaffold project dir which will be cleaned up after the test suite executes
    :raises: unittest.SkipTest if the provided NiFi rest endpoint is not up
    """
    with ExitStack() as stack:
        tmp_dir = stack.enter_context(tempfile.TemporaryDirectory())
        scaffold_dir = os.path.join(tmp_dir, 'dataflow')
        flowlib.api.gen_flow_scaffold(scaffold_dir)
        try:
            wait_for_nifi_api(endpoint, retries=2, delay=3)
        except FlowLibException:
            raise unittest.SkipTest("NiFi Rest endpoint is not available on {}, will not run TestCase".format(endpoint))

        yield scaffold_dir


class ITestBase(unittest.TestCase):

    def __init__(self, host, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nifi = 'http://{}:8080'.format(host)
        self.zookeeper = '{}:2181'.format(host)

    def setUp(self):
        os.chdir(self.project_dir)

    def run(self, result=None):
        with tmp_project_dir(self.nifi) as project_dir:
            self.project_dir = project_dir
            super(ITestBase, self).run(result)

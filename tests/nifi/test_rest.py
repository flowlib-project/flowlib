# -*- coding: utf-8 -*-
import unittest

from flowlib.nifi.rest import wait_for_nifi_api
from flowlib.model import FlowLibException

class TestFlowLibRest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            wait_for_nifi_api('http://127.0.0.1:8080', retries=2, delay=3)
        except FlowLibException:
            raise unittest.SkipTest("NiFi Rest endpoint is not available, will not test flowlib.nifi.rest")

    def test_wait_for_nifi_api(self):
        print('running') # todo

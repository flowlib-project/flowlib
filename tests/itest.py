# -*- coding: utf-8 -*-
import sys
import unittest

from tests.integration.itest_scaffold_deploy import ITestScaffoldDeploy
from tests.integration.itest_docs import ITestDocs
from tests.integration.itest_rest import ITestRest


def suite(host='127.0.0.1'):
    suite = unittest.TestSuite()
    suite.addTest(ITestScaffoldDeploy(host))
    suite.addTest(ITestDocs(host))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner(failfast=True)
    if len(sys.argv) >= 2:
        runner.run(suite(sys.argv[1]))
    else:
        runner.run(suite())

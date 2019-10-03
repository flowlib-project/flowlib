# -*- coding: utf-8 -*-
from pkg_resources import get_distribution, DistributionNotFound

__author__ = "B23"

try:
    __version__ = get_distribution('b23-flowlib').version
except DistributionNotFound:
    # package is not installed
    pass

STATEFUL_PROCESSORS = [
    "org.apache.nifi.processors.standard.MonitorActivity",
    "org.apache.nifi.processors.standard.ListSFTP",
    "org.apache.nifi.processors.standard.ListFile",
    "org.apache.nifi.processors.standard.ListDatabaseTables",
    "org.apache.nifi.processors.standard.GenerateTableFetch",
    "org.apache.nifi.processors.standard.TailFile",
    "org.apache.nifi.processors.standard.QueryDatabaseTableRecord",
    "org.apache.nifi.processors.script.ExecuteScript",
    "org.apache.nifi.processors.script.InvokeScriptedProcessor",
    "org.apache.nifi.processors.hadoop.inotify.GetHDFSEvents",
    "org.apache.nifi.processors.hadoop.ListHDFS",
    "org.apache.nifi.processors.solr.GetSolr",
    "org.apache.nifi.processors.splunk.GetSplunk",
    "org.apache.nifi.processors.aws.s3.ListS3",
    "org.apache.nifi.processors.gcp.storage.ListGCSBucket",
    "org.apache.nifi.processors.azure.storage.ListAzureBlobStorage",
    "org.apache.nifi.cdc.mysql.processors.CaptureChangeMySQL",
    "org.apache.nifi.hbase.GetHBase"
]

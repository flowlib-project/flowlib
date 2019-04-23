# -*- coding: utf-8 -*-

# TODO: popen git rev-parse HEAD
# def parse_git_revision():
#     return "Not Found"

# TODO: handle snapshot versions if no git tag

snapshot = True
version = 0.1

if snapshot:
    version = "{}-SNAPSHOT".format(version)

git_revision = "Not Found"

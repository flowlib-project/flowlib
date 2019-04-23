# -*- coding: utf-8 -*-

def parse_git_revision():
    # TODO: popen git rev-parse HEAD
    return "Not Found"

# TODO: handle snapshot versions if no git tag

snapshot = True
version = 0.1

if snapshot:
    version = "{}-SNAPSHOT".format(version)

git_revision = parse_git_revision()

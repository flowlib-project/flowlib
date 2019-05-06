# -*- coding: utf-8 -*-
import os

def parse_git_version():
    try:
        with open(os.path.join(os.path.dirname(__file__), 'git_version')) as f:
            return f.read()
    except FileNotFoundError:
        return "git-version-not-found"

version = 0.1
git_version = parse_git_version()

if 'dirty' in git_version:
    version = "pre-{}".format(version)

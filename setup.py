# -*- coding: utf-8 -*-
import logging
import importlib
import os
from setuptools import setup, find_packages

logger = logging.getLogger(__name__)
version = importlib.import_module(
    'flowlib.version', os.path.join('flowlib', 'version.py')).version

def git_version(version):
    repo = None
    try:
        import git
        repo = git.Repo('.git')
    except ImportError:
        logger.warning('git python module not found, unable to parse git version')
        return 'dirty'
    except Exception as e:
        logger.warning('Cannot compute the git version. {}'.format(e))
        return 'dirty'

    if repo:
        sha = repo.head.commit.hexsha
        if repo.is_dirty():
            return '{sha}.dirty'.format(sha=sha)

        return 'release:{version}+{sha}'.format(version=version, sha=sha)
    else:
        return 'dirty'

def write_version(filename=os.path.join('flowlib', 'git_version')):
    if not os.path.exists(filename):
        text = "{}".format(git_version(version))
        with open(filename, 'w') as a:
            a.write(text)

write_version()
setup(
    name="b23-flowlib",
    version=version,
    packages=find_packages(exclude=['tests*']),
    package_data={'flowlib': ['git_version', 'logging.conf']},
    include_package_data=True,
    install_requires=['nipyapi>=0.12.1', 'pyyaml', 'jinja2', 'urllib3<1.25,>=1.21.1'],
    author="David Kegley",
    author_email="kegs@b23.io",
    description="A library for composing and deploying NiFi flows from YAML",
    keywords="b23 flowlib NiFi dataflow",
    url="https://b23.io",
    download_url="https://github.com/B23admin/b23-flowlib/releases/latest",
    project_urls={
        "Source Code": "https://github.com/B23admin/b23-flowlib"
    },
    entry_points={
        'console_scripts': [
            'flowlib=flowlib.main:main',
        ],
    }
)

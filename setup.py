# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name="b23-flowlib",
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    packages=find_packages(exclude=['tests*']),
    package_data={
        'flowlib': ['logging.conf', 'init/*'],
    },
    include_package_data=True,
    install_requires=['nipyapi>=0.13.3', 'pyyaml', 'jinja2', 'numpy>=1.17.0', 'networkx>=2.3'],
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

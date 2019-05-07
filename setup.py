# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

def get_flowlib_version():
    from setuptools_scm.version import get_local_dirty_tag
    def clean_scheme(version):
        return get_local_dirty_tag(version) if version.dirty else '+clean'

    return {
        'local_scheme': clean_scheme,
        'write_to': 'version.py'
    }

setup(
    name="b23-flowlib",
    use_scm_version=get_flowlib_version,
    setup_requires=['setuptools_scm'],
    packages=find_packages(exclude=['tests*']),
    package_data={
        'flowlib': ['logging.conf']
    },
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

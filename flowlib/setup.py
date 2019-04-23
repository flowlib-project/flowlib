from setuptools import setup, find_packages

setup(
    name="b23-flowlib",
    version="0.1",
    packages=find_packages(),
    install_requires=['nipyapi>=0.12.1', 'pyyaml'],
    author="David Kegley",
    author_email="kegs@b23.io",
    description="A library for composing and deploying NiFi flows from YAML",
    keywords="b23 flowlib NiFi dataflow",
    url="https://b23.io",
    project_urls={
        "Source Code": "https://github.com/B23admin/b23-flowlib"
    }
)

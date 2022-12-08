# FlowLib #

## Install ##

Download the [latest release](https://github.com/B23admin/b23-flowlib/releases/latest) and install with pip:

```shell
pip install b23-flowlib-$VERSION.tar.gz
```

Check out the [User Guide](./docs/FLOWLIB_USER_GUIDE.md) to get started


## Why FlowLib? ##

- (Data Flow as Code) FlowLib provides data flow developers the ability to maintain their data flow logic as code.
- (Fully automated) NiFi admins can then deploy that code to a running NiFi instance in a fully automated way with no user intervention.
- No user interface required.
- (State migration) Processor state is maintained across deployments which is not possible when using NiFi.
- (Reuse common flow logic) FlowLib Components can be used to encapsulate common data flow paradigms which can then be configured at runtime via variable injection.
- (Global Flow Controller Configuration) FlowLib allows users to version and configure a NiFi instance’s Flow Controller (max event threads, max timer threads, reporting tasks/controllers) which is not possible with Registry.


## Developer Getting Started ##

The following commands will allow a virtualenv to be setup where the packages required will be installed along with FlowLib itself.  Any changes in FlowLib will be picked up and can be ran in this environment; hence, pip install does not need to be ran every time when testing changes.

```shell
git clone git@github.com:B23admin/b23-flowlib.git && cd b23-flowlib
virtualenv env --python=$(which python3)
source env/bin/activate
pip install requirements-dev.txt
pip install -e ./
```

## Dependencies ##

All packages/libraries needed for FlowLib are specified and installed using the `requirements-dev.txt` file.  How to install that is mentioned in the section above.

FlowLib does allow two workflows to promote flows from one NiFi instance to another and would require you have more than one NiFi instance up and running.  The first workflow just works with templates where you can use FlowLib to create templates, transfer templates to another instance, and instantiate it in destination instance.  The second workflow would require at least one in of a Registry and can transfer template between buckets or two Registry instances and change a flow's version to either the latest or one specified.

## Testing ##

Run `./test.sh` to run all the unit/integration tests


## Release ##

For a major/minor release, pass the version as an argument to the release script

```bash
./release.sh 1.0.0
```

for a patch release, do not pass any arguments

```bash
./release.sh
```

Please note that the archive still needs to be uploaded to GitHub.  This is first accomplished by creating the release via GitHub
and then uploading the archives to that release from your local machine.  You will need to ensure that the local archive has been
named to the appropriated release (i.e. b23-flowlib-1.2.1.tar.gz) since a local build using adds a dist + # to the archive name.


## Build Docker ##

The `build.sh` in the root folder will allow for a specified release or a local build to be used and a Docker image to be created.

For local development, the version does not need to be passed in and the tar containing
local changes will be created and used in the Docker image using the following script:

```bash
./build.sh
```

If a specific tagged version is required for the Docker image then the script can be
provided a version:

```bash
./build.sh 1.1.0
```

Please note, that `gh` needs to be installed since this is used to download the release
archive.  You may need to login in using the following command:

```bash
gh auth login
```

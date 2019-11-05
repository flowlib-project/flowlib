# B23 FlowLib #

## Install ##

Download the latest release from https://github.com/B23admin/b23-flowlib/releases/latest

```shell
pip install b23-flowlib-$VERSION.tar.gz
```

Check out the [User Guide](./docs/FLOWLIB_USER_GUIDE.md) to get started


## User Stories ##

1. As a NiFi flow developer, I would like the ability to develop data flows in a way that is easily version controlled and code reviewed, and the ability to deploy those flows in a fully automated way with no user interaction.
2. [#63] As a NiFi flow developer, I would like the ability to modify an existing data flow (that was previously deployed by FlowLib) and deploy the modified flow while maintaining processor state if it exists.
3. [#59] As a NiFi flow developer, I would like the ability to export an existing data flow (that was previously deployed by FlowLib) and deploy the data flow to a new NiFi instance while maintaining processor state if it exists.
4. [roadmap] As a NiFi flow developer, I would like the ability to export an existing data flow (that was *__not__* deployed by FlowLib) to a format that is compatible with FlowLib so that it can be modified as code and deployed by FlowLib.


## Why FlowLib? ##

- (Data Flow as Code) FlowLib provides data flow developers the ability to maintain their data flow logic as code.
- (Fully automated) NiFi admins can then deploy that code to a running NiFi instance in a fully automated way with no user intervention.
- No user interface required.
- (State migration) Processor state is maintained across deployments which is not possible when using NiFi.
- (Reuse common flow logic) FlowLib Components can be used to encapsulate common data flow paradigms which can then be configured at runtime via variable injection.
- (Global Flow Controller Configuration) FlowLib allows users to version and configure a NiFi instance’s Flow Controller (max event threads, max timer threads, reporting tasks/controllers) which is not possible with Registry.


## Developer Getting Started ##

```shell
git clone git@github.com:B23admin/b23-flowlib.git && cd b23-flowlib
virtualenv env --python=$(which python3)
source env/bin/activate
pip install requirements-dev.txt
pip install -e ./
```


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

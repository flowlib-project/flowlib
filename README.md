# B23 FlowLib #

## Install ##

Download the latest release from https://github.com/B23admin/b23-flowlib/releases/latest

```shell
pip install b23-flowlib-$VERSION.tar.gz
```

Check out the [User Guide](./docs/FLOWLIB_USER_GUIDE.md) to get started


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

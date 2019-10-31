## Quick start ##

To create a new flowlib project, users can run `flowlib --scaffold ./dataflow`. This will create a default project scaffold in the target folder which includes everything you need to get a local instance of nifi running on kubernetes, and a sample flow defined as a starting point.

The sample data flow defined in [flow.yaml](../flowlib/init/flow.yaml) can be deployed as-is or modified to suite your needs.  The `components/` directory contains sample components that can be imported to your `flow.yaml` or from other components.

Start a local nifi instance on kubernetes by running `./nifi.sh`. To access the NiFi UI, forward the container port to one of your local ports using [kubefwd](https://github.com/txn2/kubefwd) and visit `http://nifi-dev:8080/nifi` in your browser

> This can be also be accomplished with bare `kubectl port-forward` but you'll need to forward both ports 8080 and 2181 and then update `.flowlib.yml` to specify the right `nifi_endpoint` or provide the `--nifi-endpoint` flag at runtime

Deploy the default reporting tasks defined in the [project configuration](#Project\ Configuration) with: `flowlib --configure-flow-controller`

Deploy the default flow with `flowlib --flow-yaml ./flow.yaml`

To re-deploy a flow that has already been deployed with flowlib, provide the `--force` cli flag. This will overwrite the existing flow and attempt to migrate zookeeper state for any stateful processors in the flow.  See [FLOWLIB_STATE.md](./FLOWLIB_STATE.md) for details on how flowlib manages proecessor state migration


## Project Configuration ##

The project configuration is defined in [.flowlib.yml](../flowlib/init/.flowlib.yml). By default flowlib will look for the project config in the current working directory. This behavior can be overridden by setting the environment variable `FLOWLIB_CFG`

The project config contains useful defaults like `nifi_endpoint` and `zookeeper_connection` so that you don't need to specify the flags for every cli command. See [config.py](../flowlib/model/config.py) for the available project configurations and run `flowlib --help` to see the available cli flags


## Creating a new component ##

Adding a new component is as simple as adding a component yaml definition to the `components/` directory:

```yaml
# component.yaml
---
name: csv-to-parquet

# Provide default values, these may be overridden when the component is instantiated
defaults:
  abc: 'A default value'

# Define any required variables of this component
required_vars:
- xyz

# These controllers will be defined in the `controller_services`
# field of flow.yaml and provided when the component is instantiated
required_controllers:
  reader-controller: 'org.apache.nifi.csv.CSVReader'
  writer-controller: 'org.apache.nifi.parquet.ParquetRecordSetWriter'

# Defines the flow logic
process_group:
- name: input
  type: input_port
  connections:
  - name: debug

- name: convert-record
  type: processor
  config:
    package_id: org.apache.nifi.processors.standard.ConvertRecord
    properties:
      record-reader: "{{ controller('reader-controller') }}"
      record-writer: "{{ controller('writer-controller') }}"
  connections:
  - name: update-attribute
    relationships: ['success']
  - name: failure-output
    relationships: ['failure']

- name: update-attribute
  type: processor
  config:
    package_id: org.apache.nifi.processors.attributes.UpdateAttribute
    properties:
      abc: "{{ abc }}"
      xyz: "{{ xyz }}"
  connections:
  - name: success-output
    relationships: ['success']
  - name: failure-output
    relationships: ['failure']

- name: success-output
  type: output_port

- name: failure-output
  type: output_port
```

And then referencing the component from your flow:

```yaml
# flow.yaml
canvas:
...
- name: convert-record
  type: process_group
  component_path: component.yaml
  vars:
    # abc: "Here we could override the default value, but this not required"
    xyz: This variable is required
  controllers: # Specifies the controller services to inject into the component
    reader-controller: csv-reader
    writer-controller: parquet-writer
  connections:
  - name: debug
    from_port: success-output
    to_port: input
...
```

Check out [FLOWLIB_CONCEPTS.md](FLOWLIB_CONCEPTS.md) for details about each of the different types of elements that can be used in your flow definitions


## Doc Generation ##

Developing flows with flowlib is a very iterative process of deploying and re-deploying to a running nifi instance. Because each NiFi instance may have different processors or versions of proecessors available, flowlib provides the ability to generate html documentation as a convenience for determining a processor's properties based on its descriptors.

To generate documentation, use: `flowlib --generate-docs ./docs`

This command will generate a yaml file for each type of reporting-task, controller, and processor available to the current nifi instance defined in the configuration.  It does this by creating and then deleteing an instance of each type via NiFi's REST api. Since this is a longish process (~1m) and somewhat intensive for NiFi, it is recommended that you do this 1x on a dev cluster and commit the docs directory to git for others to use. (That is assuming everyone is using the same version of NiFi for this project) Otherwise the docs directory can be gitignored.  If a new api type is added, it is safe to re-run the `generate-docs` command. Any existing api types will be skipped and new ones will be added. The HTML is always re-generated from the yaml. Use the `--force` flag to completely re-generate the documentation

Open `docs/index.html` to view the available api types, their field descriptors and a sample YAML definition.

The generated html has external js/css dependencies so for offline use, there are cli flags for `--list` and `--describe` which just reads the yaml in the `docs/` directory

For example:

```bash
$ flowlib --list controllers
...
org.apache.nifi.confluent.schemaregistry.ConfluentSchemaRegistry
org.apache.nifi.schema.inference.VolatileSchemaCache
org.apache.nifi.redis.service.RedisDistributedMapCacheClientService
org.apache.nifi.websocket.jetty.JettyWebSocketServer
...

$ flowlib --describe controller org.apache.nifi.websocket.jetty.JettyWebSocketServer
+------+-----------+--------------------+------------+-------------+---------------+-------------+
| Name | Default   | Allowable Values   | Required   | Sensitive   | Supports EL   | Description |
|------+-----------+--------------------+------------+-------------+---------------+-------------|
...
```

## Variable injection and Jinja helpers ##

Flowlib provides the ability to inject variables via [Jinja templates](https://jinja.palletsprojects.com/en/2.10.x) however not all yaml values can be templated.

For `Processors` and `ControllerServices`, only the values of fields in `config.properties` can be templated. All other values will not have any preprocessing done.

For example:

```yaml
- name: list-s3
  type: processor
  config:
    package_id: org.apache.nifi.processors.aws.s3.ListS3
    scheduling_strategy: 'TIMER_DRIVEN' # These do not support jinja
    scheduling_period: '10 sec'
    properties: # All the fields of `properties` do support jinja
      Bucket: "{{ bucket }}"
      Region: "{{ region }}"
      AWS Credentials Provider service: "{{ controller('aws_credential_service') }}"
      prefix: "{{ prefix }}"
      min-age: "{{ min_object_age }}"
  connections: # These do not support jinja
  - name: filter-directories
    relationships: ['success']
```

The variables available during jinja templating might be defined by the `global_vars` field in `flow.yaml`

```yaml
# flow.yaml
...
global_vars:
  some_var: 'Some value to inject'
...
```

or the `defaults` field of a `Component`

```yaml
# component.yaml
...
defaults:
  some_var_with_default: 'A default value'
...
```

Flowlib also provides some jinja helpers, currently:

`env('ENV_VAR', default=None)` - The `env` helper can be used to lookup an environment variable. The default is used if the environment variable is not not set.

`controller('controller-name')` - The `controller` helper is used to reference a controller service defined in the `controller_services` field of the `flow.yaml`

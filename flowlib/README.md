# FlowLib #

A python module and cli tool for deploying NiFi flows from YAML

### TODO ###

- Dist and version with SetupTools
- Implement flow.validate()
  - template vars
  - check connections are valid
  - warn on unconnected elements
- Write flowlib version and flow version to RootProcessGroup's comments section during deploy
- Implement flow.load_from_nifi() static method to initialize a flow from a running NiFi instance
- Implement flow.compare(flow) for diffing flows


### Concepts ###

`FlowComponent` - A re-useable process group definition

```yaml
component_name: Port Tester

process_group:
- name: success-input
  type: input_port
  connections:
  - name: debug

- name: failure-input
  type: input_port
  connections:
  - name: debug

- name: debug
  type: processor
  config:
    package_id: org.apache.nifi.processors.standard.DebugFlow
    properties: {}
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

`ProcessGroup` - The _instantiation_ of a `FlowComponent`

```yaml
- name: port-tester
  type: process_group
  component_ref: common/port_test.yaml
  connections:
  - name: debug
    from_port: success-output
    to_port: input
  - name: log-attribute
    from_port: failure-output
```

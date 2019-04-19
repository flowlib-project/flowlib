# FlowLib #

A python module and cli tool for deploying NiFi flows from YAML


#### Concepts ####

`FlowComponent` - A re-useable process group definition. Here's an example a flow component

```yaml
component_name: Debug

accepts_inputs: True
accepts_outputs: True

process_group:
- name: input
  element_type: InputPort
  downstream:
  - name: debug
    relationships: []

- name: debug
  element_type: Processor
  config:
    package_id: org.apache.nifi.processors.standard.DebugFlow
    auto_terminated_relationships: ['failure']
    properties: {}
  downstream:
  - name: output
    relationships: ['success']

- name: output
  element_type: OutputPort
```

`ProcessGroup` - The _instantiation_ of a `FlowComponent`

```yaml
- name: listfetch-east
  element_type: ProcessGroup
  component_ref: common/s3_list_fetch.yaml
  vars:
    s3_bucket: stackspace-us-east-1
    s3_region: us-east-1
    s3_prefix: /abc/def/
  downstream:
  - name: debug
    relationships: []
```

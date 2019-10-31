## Concepts ##

__FlowElement__ - The [base type](../flowlib/model/flow.py) used to identify elements that can be created on a NiFi canvas.  Example types of elements include `process_group`, `processor`, `input_port`, `output_port`, or `remote_process_group`


__FlowComponent__ - A re-useable `process_group` definition.  The `process_group` field of a component definition may contain one to many `FlowElements`. The Component may also define `required_controllers` or `required_vars` to let users know what values are required to use the Component

```yaml
# component.yaml
---
name: csv-to-parquet

required_vars:
- abc
- xyz

required_controllers:
  reader-controller: 'org.apache.nifi.csv.CSVReader'
  writer-controller: 'org.apache.nifi.parquet.ParquetRecordSetWriter'

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


__ControllerService__ - Controllers services are defined at the root level of a flow and can be injected into Components

```yaml
# flow.yaml
...
controller_services:
- name: csv-reader
  config:
    package_id: 'org.apache.nifi.csv.CSVReader'
- name: parquet-writer
  config:
    package_id: 'org.apache.nifi.parquet.ParquetRecordSetWriter'
...
```


__process_group__ - The _instantiation_ of a `FlowComponent`.  A `process_group` is a special type of FlowElement and is one of the core features of flowlib. They allow users to inject variables and ControllerServices into a Component

```yaml
# flow.yaml
...
canvas:
- name: convert-record
  type: process_group
  component_path: component.yaml
  vars:
    abc: "123"
    xyz: Some value to inject
  controllers:
    reader-controller: csv-reader
    writer-controller: parquet-writer
  connections:
  - name: debug
    from_port: success-output
    to_port: input
  - name: log-attribute
    from_port: failure-output
...
```

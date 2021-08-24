# Export From Registry
* Make sure you have a NiFi registry connected to your nifi instance
* Create your flow in the nifi cluster and place it into version control through the nifi registry
* Once in version control (Nifi Registry), we can export it through the tool
    * flowlib --registry-export Bucket_Identifier Flow_Identifier Version
        * The identifiers can be found in the nifi registry interface
        * Version, is an int value or the word latest to retrieve the latest version
        * You can also the **--output-format** to specify between json or yaml output
        * To specify the registry or nifi endpoint desired, use the **--nifi-endpoint** flag
    * Ex:
        * flowlib --output-format json --nifi-endpoint http://localhost:18080 --registry-export 58045f90-0b5c-40ac-85ce-140df7dc11c1 159a95d4-3ffe-4122-905d-b1e05a230eb4 latest > registry-output.json

# Import Into Registry
To import a flow that was exported from the registry using this tool, you need to make sure that it's exported in json format.

* Using the flag --registry-import you'll be able to import the json flow back into a disired bucket and flow
    * flowlib --registry-import File_Location Bucket_Name New_Desired_Flowname
    * Bucket name has to previously exist before running this command
    * A new flow will be created if it doesn't already exist and if it does, it will insert this as a new version
    * File location references the json file that was exported from the registry
    * Ex:
        * flowlib --nifi-endpoint http://localhost:18080 --registry-import ./registry-output.json sample4 brad

# Convert To Flowlib Format
To convert the registry json file to a flowlib format just make sure your in the same directory of where the registry json output file is located. Make sure you specify to convert with the **--output-format** value to yaml
*  flowlib --output-format yaml --registry-convert-flowlib ./registry-output.json

This command should create all the dependancies, components and valid structure in order to create the flow in the nifi cluster
# Export From Registry
* Make sure you have a NiFi registry connected to your nifi instance
* Create your flow in the nifi cluster and place it into version control through the nifi registry
* Once in version control (Nifi Registry), we can export it through the tool
    * flowlib --registry-export Bucket_Identifier Flow_Identifier Version
        * The identifiers can be found in the nifi registry interface
        * Version, is an int value or the word latest to retrieve the latest version
        * You can also the **--output-format** to specify between json or yaml output
        * To specify the registry or nifi endpoint desired, use the **--nifi-endpoint** flag
        * Specify the portion of the bucket name and the tool will return all buckets that start with the value you used
        * Using the "**all**" value will return all buckets in the registry
    * Ex:
        * flowlib --output-format json --nifi-endpoint http://localhost:18080 --registry-export all
        * flowlib --output-format json --nifi-endpoint http://localhost:18080 --registry-export pims

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
Conversion is now done automatically when the export command is run
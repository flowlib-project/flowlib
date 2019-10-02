package io.b23.processors.flowlib.metrics.nifi;

import org.apache.nifi.provenance.ProvenanceEventRecord;

import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class FetchS3Handler {


    public static Map<String, String> HandleFetchS3Event(ProvenanceEventRecord event){

        HashMap<String, String> returnMap = new HashMap<>();
        Map<String, String> attributes = event.getAttributes();

        returnMap.put("workload_id", attributes.get("workload_id"));
        returnMap.put("bucket_name", attributes.get("s3.bucket"));
        returnMap.put("key_name", attributes.get("orig_filename"));
        returnMap.put("key_size", attributes.get("s3.length"));
        returnMap.put("last_modified", attributes.get("s3.lastModified"));

        return returnMap;
    }
}

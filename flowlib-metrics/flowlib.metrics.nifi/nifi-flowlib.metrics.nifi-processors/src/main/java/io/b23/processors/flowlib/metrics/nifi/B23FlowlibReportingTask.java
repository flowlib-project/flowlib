/*
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package io.b23.processors.flowlib.metrics.nifi;

import org.apache.nifi.components.PropertyDescriptor;
import org.apache.nifi.controller.ConfigurationContext;
import org.apache.nifi.annotation.lifecycle.OnScheduled;
import org.apache.nifi.annotation.documentation.CapabilityDescription;
import org.apache.nifi.annotation.documentation.Tags;
import org.apache.nifi.processor.Relationship;
import org.apache.nifi.provenance.ProvenanceEventRecord;
import org.apache.nifi.provenance.ProvenanceEventType;
import org.apache.nifi.reporting.AbstractReportingTask;
import org.apache.nifi.reporting.ReportingContext;

import java.io.IOException;
import java.util.*;
import java.util.concurrent.atomic.AtomicLong;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

@Tags({"flowlib"})
@CapabilityDescription("Send flowlib metrics to dataflow metrics service")
public class B23FlowlibReportingTask extends AbstractReportingTask {

    private List<PropertyDescriptor> descriptors;

    private Set<Relationship> relationships;

    private String db_host;
    private String db_user;
    private String db_password;

    protected AtomicLong lastQuery = new AtomicLong(-1);

    @Override
    public final List<PropertyDescriptor> getSupportedPropertyDescriptors() {
        return descriptors;
    }

    @OnScheduled
    protected void onScheduled(final ConfigurationContext context) {

        db_host = "test";
        db_user = "test";
        db_password = "test";

    }

    @Override
    public void onTrigger(ReportingContext reportingContext) {
        final long timestamp = System.currentTimeMillis();
        getLogger().info("Running B23 Flowlib Reporting Task");

        try {
            List<ProvenanceEventRecord> provenanceEvents = reportingContext
                    .getEventAccess()
                    .getProvenanceEvents(lastQuery.get() + 1, 1000);

            provenanceEvents.stream()
                    .filter(event -> event.getComponentType().equals("FetchS3Object"))
                    .filter(event -> event.getEventType().equals(ProvenanceEventType.FETCH))
                    .forEach(event -> {
                        Map<String, String> flowlibMap = FetchS3Handler.HandleFetchS3Event(event);

                        GsonBuilder gsonMapBuilder = new GsonBuilder();
                        Gson gsonObject = gsonMapBuilder.create();
                        String jsonStr = gsonObject.toJson(flowlibMap);

                        getLogger().info(jsonStr);
                        lastQuery.set(event.getEventId());  // Update the last query value on each event
                    });

        } catch (IOException e) {
            e.printStackTrace();
        }

    }
}

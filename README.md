# **processing-operator**

`processing-operator` rates the `Reports` generated by the `metering-operator`.
When a `report` is created or updated, it will start its work.
It uses two `CustomResources`, the `RatingRules` to get its configuration and emits `RatedMetrics` after having rated data.

## CustomResources
### RatingRules
The configurations used in the processor are queried and mounted from the `api` component.
They are described by `RatingRules` objects, located in the namespace your `rating` is installed in.
Below an example `RatingRules`. It is composed of two parts, `metrics` and `rules`:

```yaml
---
apiVersion: rating.alterway.fr/v1
kind: RatingRule
metadata:
  name: example-rules
  namespace: example-namespace
spec:
  metrics:
    request_cpu:
      report_name: pod-rating-cpu-request-hourly
      presto_table: report_metering_pod_rating_cpu_request_hourly
      presto_column: pod_request_cpu_core_seconds
      unit: core-seconds
  rules:
  -
    name: rules_example
    labelSet:
        foo: bar
    rules:
    -
        metric: request_cpu
        price: 0.00075
        unit: core-hours
  -
    name: rules_default
    rules:
    -
      metric: request_cpu
      price: 0.5
      unit: core-hours
```
In the **metrics** part, `presto_table` and `presto_column` are values that comes from the `metering-operator`, and represent the location of data in the `presto` DBS, see [documentation](https://github.com/operator-framework/operator-metering/blob/master/Documentation/using-metering.md).
`report-name` is the name of the followed `report` and `unit` is the type of conversion to be applied (**byte-seconds** or **core-seconds**) to the metric.

The **rules** key is used to specify how to rate a given metric, according to the attached labels.
If a frame matches every label of a rule, and the metric is found in the `rules` sub-category, the `price` and `unit` will be used for the rating.
Defaults rules can be described without the `labelSet` key.
If a frame does not match any rules with labels, it will find the first rule that do not have labels and have the metric to rate.
If no rule matched, rating will be **NULL** in the database.

#### Configuration versioning

The processor will use his default configuration until a new one is added.
Every new `RatingRules` have to be validated by the `api` (see [documentation]() for details), before being used as a configuration.
Once it's done, a timestamp will be attributed to it, with the base configuration having 0.
The processor is selecting the configuration to use for a given report by comparing configurations timestamps and frame timestamps. This mechanism ensure that every frame will be rated with the right configuration, and give the opportunity to replay the rating if needed.

### RatedMetrics

Once the data frames are processed, the `processing-operator` emits a `RatedMetrics`, looking like below:

```yaml
apiVersion: rating.alterway.fr/v1
kind: RatedMetric
metadata:
  name: rated-example-request-cpu
  namespace: example-namespace
spec:
  date: "2020-04-09 15:03:18.716"
  metric: request_cpu
```

It is used to notify other systems that new data is available.
Creating this resource manually will do nothing, only the deletion of the generated ones matters.
Deleting the example `RatedMetrics` will remove the `request_cpu` data located in `postgresql`

## Results

Once processed, this is what you can expect to find in the database:

| frame_begin         	| frame_end           	| namespace 	| node         	| metric      	| pod                  	| quantity   	| frame_price   	| matched_rule                	|
|---------------------	|---------------------	|-----------	|--------------	|-------------	|----------------------	|------------	|---------------	|-----------------------------	|
| 2019-11-14 09:00:00 	| 2019-11-14 10:00:00 	| boinc     	| subtle-dog   	| usage_cpu   	| boinc-worldcommunity 	| 0.00663585 	| 7.299435e-06  	| {}                          	|
| 2019-11-14 09:00:00 	| 2019-11-14 10:00:00 	| boic      	| subtle-dog   	| request_cpu 	| boinc-worldcommunity 	| 0.1        	| 0.0005        	| {}                          	|
| 2019-11-14 09:00:00 	| 2019-11-14 10:00:00 	| metering  	| gentle-moray 	| usage_cpu   	| hive-metastore       	| 0.02196115 	| 1.9765035e-05 	| {'instance_type': 'medium'} 	|


The `matched_rule` columns indicate which `labelSet` have matched, and indirectly which rule was used.


## Tests

The critical parts of the project are covered by tests, those can be runned with tox (see tox.ini file)
Just run `$> tox` at the project root to run the tests.
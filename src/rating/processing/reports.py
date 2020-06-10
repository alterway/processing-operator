import kopf

from datetime import datetime as dt

from rating.processing import utils
from rating.processing import metrics
from rating.processing import rules
from rating.processing import rated_metrics
from rating.processing.bisect import get_closest_configs_bisect

def retrieve_configurations_from_API():
    return utils.get_from_rating_api(endpoint='/rating/configs')


def retrieve_last_rated_report(report_name):
    results = utils.get_from_rating_api(endpoint=f'/reports/{report_name}/last_rated')
    if results:
        return results[0]['last_insert']
    return None


def rated_or_not(report_name):
    timestamp = retrieve_last_rated_report(report_name)
    if timestamp:
        return dt.strptime(timestamp[:-4], '%a, %d %b %Y %H:%M:%S')
    return dt.utcfromtimestamp(0)


def select_end_period(valid_from,
                      valid_to):
    if valid_to == valid_from or \
       valid_to == dt(2100, 1, 1, 1, 1).strftime('%s'):  # Max date
        return dt.utcnow()
    return dt.utcfromtimestamp(int(valid_to))


def extract_metric_config(source, target, match):
    for key in source.keys():
        if source[key][target] == match:
            source[key]['metric'] = key
            return source[key]
    return None


def check_rating_conditions(report_name,
                            table_name,
                            begin,
                            configuration):
    metric_config = extract_metric_config(
        metrics.ensure_metrics_config(configuration['metrics']['metrics']),
        'report_name',
        report_name)
    if not metric_config:
        return {}

    rating_config = metric_config
    rating_config.update({
        'presto_table': table_name.replace('-', '_'),
        'begin': begin,
        'end': select_end_period(configuration['valid_from'],
                                 configuration['valid_to'])
    })
    return rating_config


@kopf.on.event('metering.openshift.io', 'v1', 'reports')
def report_event(body, spec, logger, **kwargs):
    metadata = body['metadata']
    if kwargs["type"] not in ['ADDED', 'MODIFIED']:
        return

    configurations = retrieve_configurations_from_API()
    if not configurations:
        raise utils.ConfigurationMissing(
            'Bad response from API, no configuration found.'
        )
    begin = rated_or_not(metadata['name'])
    configs = tuple(ts['valid_from'] for ts in configurations)
    choosen_config = get_closest_configs_bisect(
        begin.strftime('%s'),
        configs)

    table = kwargs['status'].get('tableRef')
    if not table:
        return
    metric_config = check_rating_conditions(metadata['name'],
                                            table['name'],
                                            begin,
                                            configurations[choosen_config])
    if not metric_config:
        return
    logger.info(f'using config with timestamp {configs[choosen_config]}')
    logger.info(
        'rating for {metric} in {table} for period {begin} to {end} started..'
        .format(metric=metric_config['metric'],
                table=metric_config['presto_table'],
                begin=metric_config['begin'],
                end=metric_config['end'])
    )
    rules.ensure_rules_config(configurations[choosen_config]['rules']['rules'])
    rated_metrics.retrieve_data(
        configurations[choosen_config]['rules']['rules'],
        metric_config,
        logger)

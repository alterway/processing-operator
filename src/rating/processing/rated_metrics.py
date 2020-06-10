import kopf

from datetime import datetime as dt
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from rating.processing import utils
from rating.processing import rates
from rating.processing import rules as rs


def get_frame_labels(labels_name, labels_value):
    labels = {}
    for name, value in zip(labels_name, labels_value):
        labels[name] = value
    return labels


def get_labels_from_table(table, column_name):
    columns = utils.get_from_rating_api(endpoint=f'/presto/{table}/columns')
    return [col['column_name'] for col in columns if col['column_name'] not in [
        'period_start',
        'period_end',
        'pod',
        'namespace',
        'node',
        column_name]
    ]


def extract_frames_labels(frame, column_name, labels_name):
    frame_labels = {}
    for key, value in frame.items():
        if key not in ['period_start',
                       'period_end',
                       'pod',
                       'namespace',
                       'node',
                       column_name] and key in labels_name:
            frame_labels[key] = value
    return frame_labels


def get_frames(metric_config, labels):
    payload = {
        'labels': labels,
        'column': metric_config['presto_column'],
        'start': metric_config['begin'].isoformat(sep=' ', timespec='milliseconds'),
        'end': metric_config['end'].isoformat(sep=' ', timespec='milliseconds')
    }
    return utils.get_from_rating_api(
        endpoint=f'/presto/{metric_config["presto_table"]}/frames',
        payload=payload)


def update_rated_data(rated_frames, rated_namespaces, metric_config, timestamp):
    payload = {
        'body': {
            'rated_frames': rated_frames,
            'rated_namespaces': rated_namespaces,
            'report_name': metric_config['report_name'],
            'metric': metric_config['metric'],
            'last_insert': timestamp
        }
    }
    return utils.post_for_rating_api(endpoint='/rated/frames/add',
                                     payload=payload)


def retrieve_data(rules,
                  metric_config,
                  logger):
    logger.info(f'Loading frames from {metric_config["presto_table"]}..')
    logger.info('checking for labels..')
    labels_name = get_labels_from_table(metric_config['presto_table'],
                                        metric_config['presto_column'])

    potential_labels = ', '.join(labels_name)
    if len(potential_labels) > 0:
        logger.info(f'found labels: {potential_labels}')
        potential_labels = f', {potential_labels}'
    else:
        logger.info('no labels found')

    frames = get_frames(metric_config, potential_labels)
    loaded = len(frames)
    if loaded == 0:
        logger.info('no frames loaded')
        return
    logger.info(f'{loaded} frames loaded')

    rated_frames, rated_namespaces = [], []
    rating_time = dt.utcnow()
    for frame in frames:
        # 6 here because every columns after is considered a label
        frame_labels = extract_frames_labels(frame,
                                             metric_config['presto_column'],
                                             labels_name)
        labels, rule = rs.find_match(metric_config['metric'],
                                     frame_labels,
                                     rules)
        converted = rates.convert_metrics_unit(
            metric_config['unit'],
            rule['unit'],
            frame[metric_config['presto_column']]
        )

        rated_frames.append((
            frame['period_start'],                              # frame_begin
            frame['period_end'],                                # frame_end
            frame['namespace'],                                 # namespace
            frame['node'],                                      # node
            metric_config['metric'],                            # metric
            frame['pod'],                                       # pod
            converted,                                          # quantity
            rates.rate(rule, {'qty': converted}),               # rating
            f'{labels}'
        ))
        rated_namespace = frame['namespace']
        if rated_namespace not in rated_namespaces:
            rated_namespaces.append(rated_namespace)
    logger.info('frame processed')

    logger.info('sending data..')
    result = update_rated_data(rated_frames,
                               rated_namespaces,
                               metric_config,
                               rating_time.isoformat(sep=' ', timespec='milliseconds'))
    if result:
        logger.info(f'updated rated-{metric_config["metric"].replace("_", "-")} object')
    logger.info('finished rating instance')


@kopf.on.delete('rating.alterway.fr', 'v1', 'ratedmetrics')
@utils.assert_rating_namespace
def delete_rated_metric(body, spec, logger, **kwargs):
    data = {
        'body': {
            'metric': spec['metric']
        }
    }
    response = utils.post_for_rating_api(endpoint='/rated/frames/delete',
                                         payload=data)
    if response:
        logger.info(f'deleted {response["results"]} rows associated with {body["metadata"]["name"]}')

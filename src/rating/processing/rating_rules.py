import kopf
import requests

from datetime import datetime as dt

from rating.processing import utils


@kopf.on.create('rating.alterway.fr', 'v1', 'ratingrules')
@utils.assert_rating_namespace
def rating_rules_creation(body, spec, logger, **kwargs):
    timestamp = body['metadata']['creationTimestamp']
    rules_name = body['metadata']['name']
    data = {
        'body': {
            'rules': spec.get('rules', {}),
            'metrics': spec.get('metrics', {}),
            'timestamp': timestamp
        }
    }
    try:
        utils.post_for_rating_api(endpoint='/rating/configs/add',
                                  payload=data)
    except utils.ConfigurationException as exc:
        logger.error(f'RatingRules {rules_name} is invalid. Reason: {exc}')
    except requests.exceptions.RequestException:
        raise kopf.TemporaryError(f'Request for RatingRules {rules_name} update failed. retrying in 30s', delay=30)
    else:
        logger.info(
            f'RatingRule {rules_name} created, valid from {timestamp}.')


@kopf.on.update('rating.alterway.fr', 'v1', 'ratingrules')
@utils.assert_rating_namespace
def rating_rules_update(body, spec, logger, **kwargs):
    timestamp = body['metadata']['creationTimestamp']
    rules_name = body['metadata']['name']
    data = {
        'body': {
            'metrics': spec['metrics'],
            'rules': spec['rules'],
            'timestamp': timestamp
        }
    }
    try:
        utils.post_for_rating_api(endpoint='/rating/configs/update',
                                  payload=data)
    except utils.ApiException:
        logger.warning(f'RatingRules {rules_name} does not exist in storage, ignoring.')
    except utils.ConfigurationException as exc:
        logger.error(f'RatingRules {rules_name} is invalid. Reason: {exc}')
    except requests.exceptions.RequestException:
        logger.error(f'Request for RatingRules {rules_name} update failed.')
    else:
        logger.info(f'Rating rules {rules_name} was updated.')


@kopf.on.delete('rating.alterway.fr', 'v1', 'ratingrules')
@utils.assert_rating_namespace
def rating_rules_deletion(body, spec, logger, **kwargs):
    timestamp = body['metadata']['creationTimestamp']
    rules_name = body['metadata']['name']
    data = {
        'body': {
            'timestamp': int(dt.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ').timestamp())
        }
    }

    try:
        utils.post_for_rating_api(endpoint='/rating/configs/delete',
                                  payload=data)
    except utils.ApiException:
        logger.warning(f'RatingRules {rules_name} does not exist in storage, ignoring.')
    except requests.exceptions.RequestException:
        logger.error(f'Request for RatingRules {rules_name} deletion failed.')
    else:
        logger.info(f'RatingRules {rules_name} ({timestamp}) was deleted.')

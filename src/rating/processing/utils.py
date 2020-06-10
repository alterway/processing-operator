import kopf
import logging
import os
import re
import requests
import sys


class ConfigurationMissing(Exception):
    pass


class ConfigurationException(Exception):
    pass


class ApiException(Exception):
    pass


def assert_rating_namespace(func):
    def wrapper(*args, **kwargs):
        namespace = kwargs['body']['metadata']['namespace']
        rating_namespace = envvar('RATING_NAMESPACE')
        if namespace != rating_namespace:
            kwargs['logger'].info(f'event not in {rating_namespace} namespace, discarding')
            return {}
        return func(**kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


def admin_token(func):
    def wrapper(*args, **kwargs):
        payload = kwargs.get('payload', {})
        payload.update({
            'token': envvar('RATING_ADMIN_API_KEY')
        })
        kwargs['payload'] = payload
        return func(**kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


@admin_token
def get_from_rating_api(endpoint, payload):
    api_url = envvar('RATING_API_URL')
    response = requests.get(f'{api_url}{endpoint}', params=payload)
    try:
        response.raise_for_status()
    except requests.exceptions.RequestException:
        raise kopf.TemporaryError('rated data failed to be retrieved, retrying in 5s..', delay=5)
    content = response.json()
    return content.get('results', {})


@admin_token
def post_for_rating_api(endpoint, payload):
    api_url = envvar('RATING_API_URL')
    headers = {
        'content-type': 'application/json'
    }
    response = requests.post(url=f'{api_url}{endpoint}', headers=headers,json=payload)
    if response.status_code == 400:  # When ratingrule is wrong
        raise ConfigurationException(response.content.decode("utf-8"))
    elif response.status_code == 404:  # When object is not found
        raise ApiException
    try:
        response.raise_for_status()
    except requests.exceptions.RequestException:
        raise kopf.TemporaryError('rated data failed to be transmitted (connection error), retrying in 5s..', delay=5)
    return response.json()


def is_valid_against(target, regexp):
    return re.match(regexp, target) is not None


def envvar(name):
    """Return the value of an environment variable, or die trying."""
    try:
        return os.environ[name]
    except KeyError:
        logging.error('Missing envvar $%s', name)
        sys.exit(1)

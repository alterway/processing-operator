import kopf
import rating.processing.reports
import rating.processing.rating_rules
from kubernetes import client, config
from base64 import b64decode
import os
from kubernetes.client.rest import ApiException

import rating.processing.utils as utils


def register_admin_key(api):
    namespace = utils.envvar('RATING_NAMESPACE')
    secret_name = f'{namespace}-admin'
    try:
        secret_encoded_bytes = api.read_namespaced_secret(secret_name, namespace).data
    except ApiException as exc:
        raise exc
    rating_admin_api_key = list(secret_encoded_bytes.keys())[0]
    os.environ[rating_admin_api_key] = b64decode(
        secret_encoded_bytes[rating_admin_api_key]).decode('utf-8')


@kopf.on.create('', 'v1', 'namespaces')
@kopf.on.update('', 'v1', 'namespaces')
def callback_namespace_tenant(body, spec, logger, **kwargs):
    update_namespace_tenant(body['metadata'])


def update_namespace_tenant(metadata):
    labels = metadata.get('labels')
    if not labels:
        labels = {}
    payload = {
        'body': {
            'tenant_id': labels.get('tenant', 'default'),
            'namespace': metadata['name']
        }
    }
    utils.post_for_rating_api(endpoint='/namespaces/tenant', payload=payload)


def scan_cluster_namespaces(api):
    try:
        namespace_list = api.list_namespace()
    except ApiException as exc:
        raise exc
    for namespace_obj in namespace_list.items:
        update_namespace_tenant(
            namespace_obj.to_dict()['metadata']
        )


@kopf.on.login()
def callback_login(**kwargs):
    config.load_incluster_config()
    api = client.CoreV1Api()
    register_admin_key(api)
    kwargs['logger'].info('Registered admin token.')
    scan_cluster_namespaces(api)
    kwargs['logger'].info('Registered active namespaces.')
    return kopf.login_via_client(**kwargs)

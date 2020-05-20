import requests
from flask import current_app

ACCEPT_JSON = {'Accept': 'application/json'}


class HapiMeta(type):
    """Meta class used for delayed init - need configured app"""
    @property
    def base_url(cls):
        if getattr(cls, '_base_url', None) is None:
            cls._base_url = current_app.config.get("HAPI_URL")
        return cls._base_url


class HapiRequest(metaclass=HapiMeta):
    """Methods to execute remote request, returning (json results, status)"""

    @classmethod
    def build_request(cls, path):
        if path is None:
            raise ValueError("can't request w/o path!")
        if cls.base_url is None:
            raise ValueError("config error; can't request w/o base_url")
        return cls.base_url + path

    @classmethod
    def find_bundle(cls, resource_type, search_dict):
        """Search for bundled results from given params and return"""
        url = HapiRequest.build_request(resource_type)
        current_app.logger.debug(f"HAPI query: {url} + {search_dict}")
        hapi_res = requests.get(HapiRequest.build_request(
            resource_type), headers=ACCEPT_JSON, params=search_dict)
        hapi_res.raise_for_status()
        bundle = hapi_res.json()
        assert bundle.get('resourceType') == 'Bundle'
        return bundle, hapi_res.status_code

    @classmethod
    def find_one(cls, resource_type, search_dict):
        """Search for single resource match, return if found

        Executes search for given parameters.  If a single
        result is found, extract from the results bundle and
        return

        """
        bundle, status = HapiRequest.find_bundle(resource_type, search_dict)
        if bundle.get('total') != 1:
            current_app.logger.warn(
                f"unexpected {bundle.get('total')} items in bundle")
            return ({
                'message': f"expected one; found {bundle.get('total')}"},
                400)

        cp = bundle['entry'][0]['resource']
        current_app.logger.debug(f"Found {resource_type}: {cp}")
        return cp, status

    @classmethod
    def find_by_id(cls, resource_type, resource_id):
        """Search for single resource match, return if found"""
        hapi_res = requests.get(HapiRequest.build_request(
            f"{resource_type}/{resource_id}"), headers=ACCEPT_JSON)
        hapi_res.raise_for_status()
        return hapi_res.json(), hapi_res.status_code

    @classmethod
    def delete_by_id(cls, resource_type, resource_id):
        """Delete a single resource"""
        hapi_res = requests.delete(HapiRequest.build_request(
            f"{resource_type}/{resource_id}"), headers=ACCEPT_JSON)
        hapi_res.raise_for_status()
        return hapi_res.json(), hapi_res.status_code

    @classmethod
    def post_resource(cls, resource):
        url = cls.build_request(f'{resource["resourceType"]}')
        result = requests.post(url, json=resource, headers=ACCEPT_JSON)
        result.raise_for_status()
        return result.json(), result.status_code

    @classmethod
    def put_resource(cls, resource):
        url = cls.build_request(
            f'{resource["resourceType"]}/{resource["id"]}')
        result = requests.put(url, json=resource, headers=ACCEPT_JSON)
        result.raise_for_status()
        return result.json(), result.status_code

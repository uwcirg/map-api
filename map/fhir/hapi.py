import requests
from flask import current_app


class HapiMeta(type):
    """Meta class used for delayed init - need configured app"""
    @property
    def base_url(cls):
        if getattr(cls, '_base_url', None) is None:
            cls._base_url = current_app.config.get("HAPI_URL")
        return cls._base_url


class HapiRequest(metaclass=HapiMeta):

    @classmethod
    def build_request(cls, path):
        return cls.base_url + path

    @classmethod
    def find_bundle(cls, resource_type, search_dict):
        """Search for bundled results from given params and return"""
        hapi_res = requests.get(HapiRequest.build_request(
            resource_type),
            params=search_dict)
        hapi_res.raise_for_status()
        bundle = hapi_res.json()
        assert bundle.get('resourceType') == 'Bundle'
        return bundle

    @classmethod
    def find_one(cls, resource_type, search_dict):
        """Search for single resource match, return if found

        Executes search for given parameters.  If a single
        result is found, extract from the results bundle and
        return

        """
        bundle = HapiRequest.find_bundle(resource_type, search_dict)
        if bundle.get('total') != 1:
            current_app.logger.warn(
                "unexpected {} items in bundle".format(bundle.get('total')))
            return

        cp = bundle['entry'][0]['resource']
        current_app.logger.debug(f"Found {resource_type}: {cp}")
        return cp

    @classmethod
    def find_by_id(cls, resource_type, resource_id):
        """Search for single resource match, return if found"""
        hapi_res = requests.get(HapiRequest.build_request(
            f"{resource_type}/{resource_id}"),
            params={'_pretty': 'true', '_format': 'json'})
        hapi_res.raise_for_status()
        return hapi_res.json()

    @classmethod
    def put_resource(cls, resource):
        url = cls.build_request(
            f'{resource["resourceType"]}/{resource["id"]}')
        result = requests.put(url, json=resource)
        result.raise_for_status()
        return result.json()

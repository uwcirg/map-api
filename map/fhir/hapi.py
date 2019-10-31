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

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
    def put_patient(cls, patient_fhir):
        url = cls.build_request(f'Patient/{patient_fhir["id"]}')
        result = requests.put(url, json=patient_fhir)
        if result.status_code != 200:
            raise RuntimeError(
                f"unable to update HAPI Patient {patient_fhir['id']}")
        return result.json()

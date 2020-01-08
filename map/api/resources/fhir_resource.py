from enum import Enum, auto
from flask import request
from flask_restful import Resource
import requests
from werkzeug.exceptions import BadRequest

from map.fhir import HapiRequest


class NameEnum(Enum):
    """Mechanism to auto generate enum values using enum.name"""
    def _generate_next_value_(name, start, count, last_values):
        return name


class ResourceType(NameEnum):
    """Enumeration of supported FHIR resourceTypes"""
    # Extend as needed, controlled to prevent abuse of the API
    CarePlan = auto()
    Encounter = auto()
    Observation = auto()
    Patient = auto()
    Procedure = auto()
    Questionnaire = auto()
    QuestionnaireResponse = auto()

    @classmethod
    def validate(cls, value):
        """validate given value is in ResourceType enumeration"""
        if value in cls.__members__:
            return True
        raise BadRequest(f"{value} not a supported FHIR resourceType")


class FhirSearch(Resource):
    """Search by parameters, return bundle resource of requested resourceType
    """
    def get(self, resource_type):
        ResourceType.validate(resource_type)
        params = {'_pretty': 'true', '_format': 'json'}
        params.update(request.args)
        hapi_pat = requests.get(HapiRequest.build_request(
            resource_type),
            params=params)
        return hapi_pat.json()


class FhirResource(Resource):
    """Single FHIR resource

    Pass through request to HAPI, return the resulting JSON
    """
    def get(self, resource_type, resource_id):
        ResourceType.validate(resource_type)
        hapi_pat = requests.get(HapiRequest.build_request(
            f"{resource_type}/{resource_id}"),
            params={'_pretty': 'true', '_format': 'json'})
        return hapi_pat.json()

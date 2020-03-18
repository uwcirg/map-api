from flask import request
from flask_restful import Resource
from werkzeug.exceptions import BadRequest

from map.fhir import HapiRequest, ResourceType


class FhirSearch(Resource):
    """Search by parameters, return bundle resource of requested resourceType
    """
    def get(self, resource_type):
        try:
            ResourceType.validate(resource_type)
        except ValueError as e:
            raise BadRequest(str(e))

        return HapiRequest.find_bundle(resource_type, request.args)


class FhirResource(Resource):
    """Single FHIR resource

    Pass through request to HAPI, return the resulting JSON
    """
    def get(self, resource_type, resource_id):
        try:
            ResourceType.validate(resource_type)
        except ValueError as e:
            raise BadRequest(str(e))

        return HapiRequest.find_by_id(resource_type, resource_id)

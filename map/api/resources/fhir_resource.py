from flask import current_app, request
from flask_restful import Resource
from werkzeug.exceptions import BadRequest, Unauthorized

from map.authz import AuthorizedUser, UnauthorizedUser
from map.fhir import HapiRequest, ResourceType


class FhirSearch(Resource):
    """Search by parameters, return bundle resource of requested resourceType
    """
    def get(self, resource_type):
        try:
            ResourceType.validate(resource_type)
        except ValueError as e:
            raise BadRequest(str(e))

        try:
            authz = AuthorizedUser.from_auth_header(
                request.headers.get('Authorization'))
        except Unauthorized:
            authz = UnauthorizedUser()

        bundle = HapiRequest.find_bundle(resource_type, request.args)
        authz.check('read', bundle)
        return bundle

    def post(self, resource_type):
        try:
            ResourceType.validate(resource_type)
        except ValueError as e:
            raise BadRequest(str(e))

        au = AuthorizedUser.from_auth_header(
            request.headers.get('Authorization'))
        if not request.headers.get('Content-Type', '').startswith(
                'application/json'):
            raise BadRequest(
                "required FHIR resource not found;"
                " 'Content-Type' header ill defined.")
        au.check('write', request.json)
        return HapiRequest.post_resource(request.json)


class FhirResource(Resource):
    """Single FHIR resource

    Pass through request to HAPI, return the resulting JSON
    """
    def get(self, resource_type, resource_id):
        try:
            ResourceType.validate(resource_type)
        except ValueError as e:
            raise BadRequest(str(e))

        try:
            authz = AuthorizedUser.from_auth_header(
                request.headers.get('Authorization'))
        except Unauthorized:
            authz = UnauthorizedUser()

        resource = HapiRequest.find_by_id(resource_type, resource_id)
        authz.check('read', resource)
        return resource

    def put(self, resource_type, resource_id):
        try:
            ResourceType.validate(resource_type)
        except ValueError as e:
            raise BadRequest(str(e))

        if not request.headers.get('Content-Type', '').startswith(
                'application/json'):
            raise BadRequest(
                "required FHIR resource not found;"
                " 'Content-Type' header ill defined.")

        if int(request.json['id']) != resource_id:
            raise BadRequest("mismatched resource ID")

        au = AuthorizedUser.from_auth_header(
            request.headers.get('Authorization'))
        au.check('write', request.json)
        return HapiRequest.put_resource(request.json)

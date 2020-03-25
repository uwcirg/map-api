from flask import current_app, make_response, request
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

        bundle, status = HapiRequest.find_bundle(resource_type, request.args)
        authz.check('read', bundle)
        return make_response(bundle, status)

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
        return make_response(HapiRequest.post_resource(request.json))


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

        resource, status = HapiRequest.find_by_id(resource_type, resource_id)
        authz.check('read', resource)
        return make_response(resource, status)

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
        return make_response(HapiRequest.put_resource(request.json))

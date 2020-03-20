import json

from flask import current_app, request
from flask_restful import Resource
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError
from werkzeug.exceptions import BadRequest

from map.fhir import HapiRequest, ResourceType



def validate_jwt(bearer_token):
    """Validate bearer token signature against Authorization server public key
    """
    # todo: decode JSON string in config
    json_web_keys = json.loads(current_app.config['AUTHZ_JWKS_JSON'])

    json_payload = jwt.decode(
        token=bearer_token,
        key=json_web_keys,
        # todo: fix JWTClaimsError
        options={'verify_aud': False},
    )
    return json_payload


class FhirSearch(Resource):
    """Search by parameters, return bundle resource of requested resourceType
    """
    def get(self, resource_type):
        try:
            ResourceType.validate(resource_type)
        except ValueError as e:
            raise BadRequest(str(e))

        bearer_token = request.headers['Authorization'].split()[-1]
        try:
            payload = validate_jwt(bearer_token)
        except (ExpiredSignatureError, JWTClaimsError) as e:
            raise BadRequest(str(e))
        else:
            current_app.logger.debug('JWT payload: %s', payload)

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

        bearer_token = request.headers['Authorization'].split()[-1]
        try:
            payload = validate_jwt(bearer_token)
        except (ExpiredSignatureError, JWTClaimsError) as e:
            raise BadRequest(str(e))
        else:
            current_app.logger.debug('JWT payload: %s', payload)

        return HapiRequest.find_by_id(resource_type, resource_id)

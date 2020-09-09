"""Authorization"""
from flask import current_app
import json
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError
from werkzeug.exceptions import Unauthorized

from map.fhir import Bundle, HapiRequest
from map.authz.authorizedresource import authz_check_resource


def validate_jwt(bearer_token):
    """Validate bearer token signature against Authorization server public key
    """
    # todo: decode JSON string in config
    keys = current_app.config['AUTHZ_JWKS_JSON']
    try:
        json_web_keys = json.loads(keys)
    except json.decoder.JSONDecodeError:
        json_web_keys = keys

    json_payload = jwt.decode(
        token=bearer_token,
        key=json_web_keys,
        # todo: fix JWTClaimsError
        options={'verify_aud': False},
    )
    return json_payload


def jwt_payload(bearer_token):
    try:
        payload = validate_jwt(bearer_token)
    except (ExpiredSignatureError, JWTClaimsError) as e:
        raise Unauthorized(str(e))

    # current_app.logger.debug('JWT payload: %s', payload)
    return payload


class UnauthorizedUser(object):
    """Back door for unauthorized resource access"""

    def check(self, verb, fhir):
        """Raises Unauthorized unless user has authority to verb the contents

        :param verb: 'read' or 'write'
        :param fhir: JSON formatted FHIR contents for which an exception
          must exist in the matching check resource class to allow for
          unauthorized access, or Unauthorized will be raised

        :returns unaltered fhir
        """
        if verb not in ('read', 'write'):
            raise ValueError(f'{verb} not in ("read", "write")')

        if verb == 'write':
            raise Unauthorized("no writes allowed as unauthorized")

        if fhir['resourceType'] == 'Bundle':
            bundle = Bundle(fhir)
            for item in bundle.resources():
                ar = authz_check_resource(authz_user=self, resource=item)
                ar.unauth_read()
        else:
            ar = authz_check_resource(authz_user=self, resource=fhir)
            ar.unauth_read()
        return fhir


class AuthorizedUser(object):

    def __init__(self, jwt_payload):
        self.email = jwt_payload['email']
        self.kc_identifier_system = jwt_payload['iss']
        self.kc_identifier_value = jwt_payload['sub']

        # IF the client requested a scope including roles, obtain
        # the list stored as a dict under 'realm_access', otherwise []
        self.roles = jwt_payload.get('realm_access', {}).get('roles', [])

    @classmethod
    def from_auth_header(cls, auth_header):
        if not auth_header:
            msg = "no Authorization header found"
            current_app.logger.error(msg)
            raise Unauthorized(msg)

        if not auth_header.startswith('Bearer ') or auth_header == 'Bearer null':
            raise Unauthorized("ill formed Bearer Token")

        bearer_token = auth_header.split()[-1]
        return cls(jwt_payload(bearer_token))

    def check(self, verb, fhir):
        """Raises Unauthorized unless user has authority to verb the contents

        :param verb: 'read' or 'write'
        :param fhir: JSON formatted FHIR contents for which AuthorizedPatient
          must have authorization to <verb> or Unauthorized will be raised

        :returns potentially modified (filtered) fhir
        """
        if verb not in ('read', 'write'):
            raise ValueError(f'{verb} not in ("read", "write")')

        if fhir['resourceType'] == 'Bundle':
            bundle = Bundle(fhir)
            remove_ids = []
            for item in bundle.resources():
                ar = authz_check_resource(authz_user=self, resource=item)
                try:
                    getattr(ar, verb)()
                except Unauthorized:
                    # For bundled/search results, filter out unauthorized
                    remove_ids.append(item['id'])

            if remove_ids:
                bundle.remove_entries(remove_ids)
            return bundle.bundle
        else:
            ar = authz_check_resource(authz_user=self, resource=fhir)
            return getattr(ar, verb)()

    def consented_same_org(self, resource):
        """Returns True if resource consented to common org"""
        return resource['id'] in self.consented_users(org_id=self.org_id())

    def consented_users(self, org_id):
        """Lookup all users with consent on given org"""
        if not org_id:
            return set()

        # shouldn't need to round trip twice
        if hasattr(self, '_consented_users'):
            return self._consented_users

        self._consented_users = set()
        result, status = HapiRequest.find_bundle('Consent', search_dict={
            'organization': '/'.join(("Organization", str(org_id))),
            '_include': "Consent.patient",
            '_count': 1000})
        bundle = Bundle(result)
        for i in bundle.resources():
            if (i['resourceType'] == 'Consent' and
                    i['provision']['type'] == 'permit'):
                self._consented_users.add(
                    i['patient']['reference'].split('/')[1])
        # current_app.logger.debug("consented users: %s" % self._consented_users)
        return self._consented_users

    def extract_internals(self, resource=None):
        """Round trip or extract identifiers for self"""
        # Skip out if already done.
        if hasattr(self, "_patient_id") and self._patient_id is not None:
            return

        if not resource:
            resource, status = HapiRequest.find_one('Patient', search_dict={
                'identifier': '|'.join((
                    self.kc_identifier_system, self.kc_identifier_value))})

        if resource['resourceType'] != 'Patient':
            raise ValueError(
                "Unexpected resourceType {resource['resourceType]}")

        self._patient_id = resource['id']
        self._org_id = resource.get('managingOrganization', {}).get(
            'reference', 'Organization/').split('/')[1]

    def org_id(self):
        """Return managingOrganization identifier, if available"""
        if not hasattr(self, '_org_id'):
            # Must round trip now to get user's org_id
            self.extract_internals()

        return self._org_id

    def patient_id(self):
        """Return patient identifier, if available

        Prior to initial POST, the identifier isn't available.
        """
        if not hasattr(self, '_patient_id'):
            # Must round trip now to get user's patient_id
            self.extract_internals()

        return self._patient_id

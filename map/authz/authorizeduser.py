"""Authorization"""
from flask import current_app
import json
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError
from werkzeug.exceptions import Unauthorized

from map.fhir import Bundle


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


def email_from_jwt(bearer_token):
    try:
        payload = validate_jwt(bearer_token)
    except (ExpiredSignatureError, JWTClaimsError) as e:
        raise Unauthorized(str(e))

    # current_app.logger.debug('JWT payload: %s', payload)
    return payload['email']


class AuthzCheckResource(object):
    """Base class for FHIR Resource authorization check"""
    def __init__(self, authz_user, fhir_resource):
        self.user = authz_user
        self.resource = fhir_resource

    def read(self):
        """Default case, FHIR objects all readable"""
        return True

    def write(self):
        """Default case, no FHIR objects writeable"""
        raise Unauthorized(f"can't write {self.resource['resourceType']}")


class AuthzCheckCarePlan(AuthzCheckResource):
    def __init__(self, authz_user, fhir_resource):
        super().__init__(authz_user, fhir_resource)

    owned = True

    def read(self):
        """Only owning patient may read"""
        if self.owned:
            return True

    def write(self):
        """Initial writes allowed, and updates if same patient"""
        if not self.user.patient_id():
            return True
        if not self.owned:
            raise Unauthorized("Write CarePlan failed; mismatched owner")


class AuthzCheckPatient(AuthzCheckResource):
    def __init__(self, authz_user, fhir_resource):
        super().__init__(authz_user, fhir_resource)

    owned = True

    def read(self):
        """Only owning patient may read"""
        if self.owned:
            return True

    def write(self):
        """Initial writes allowed, and updates if same patient"""
        if not self.user.patient_id():
            return True
        if not self.owned:
            raise Unauthorized("Write Patient failed; mismatched owner")


class AuthzCheckQuestionnaireResponse(AuthzCheckResource):
    def __init__(self, authz_user, fhir_resource):
        super().__init__(authz_user, fhir_resource)

    owned = True

    def read(self):
        """Only owning patient may read"""
        if self.owned:
            return True

    def write(self):
        """Initial writes allowed, and updates if same patient"""
        if not self.user.patient_id():
            return True
        if not self.owned:
            raise Unauthorized(
                "Write QuestionnaireResponse failed; mismatched owner")


def authz_check_resource(authz_user, resource):
    """Factory returns appropriate instance for authorization check"""
    t = resource['resourceType']
    if t == 'CarePlan':
        return AuthzCheckCarePlan(authz_user, resource)
    elif t == 'QuestionnaireResponse':
        return AuthzCheckQuestionnaireResponse(authz_user, resource)
    elif t == 'Patient':
        return AuthzCheckPatient(authz_user, resource)
    else:
        return AuthzCheckResource(authz_user, resource)


class AuthorizedUser(object):

    def __init__(self, email):
        self.email = email

    @classmethod
    def from_auth_header(cls, auth_header):
        if not auth_header:
            msg = "no Authorization header found"
            current_app.logger.error(msg)
            raise Unauthorized(msg)

        if not auth_header.startswith('Bearer '):
            raise Unauthorized("ill formed Bearer Token")

        bearer_token = auth_header.split()[-1]
        return cls(email_from_jwt(bearer_token))

    def check(self, verb, fhir):
        """Raises Unauthorized unless user has authority to verb the contents

        :param verb: 'read' or 'write'
        :param fhir: JSON formatted FHIR contents for which AuthorizedPatient
          must have authorization to <verb> or Unauthorized will be raised
        """
        if verb not in ('read', 'write'):
            raise ValueError(f'{verb} not in ("read", "write")')

        if fhir['resourceType'] == 'Bundle':
            bundle = Bundle(fhir)
            for item in bundle.resources():
                ar = authz_check_resource(authz_user=self, resource=item)
                getattr(ar, verb)()
        else:
            ar = authz_check_resource(authz_user=self, resource=fhir)
            getattr(ar, verb)()

    def patient_id(self):
        """Return patient identifier, if available

        Prior to initial POST, the identifier isn't available.
        """
        return None

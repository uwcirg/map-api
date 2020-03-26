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


def jwt_payload(bearer_token):
    try:
        payload = validate_jwt(bearer_token)
    except (ExpiredSignatureError, JWTClaimsError) as e:
        raise Unauthorized(str(e))

    # current_app.logger.debug('JWT payload: %s', payload)
    return payload


class AuthzCheckResource(object):
    """Base class for FHIR Resource authorization check"""
    def __init__(self, authz_user, fhir_resource):
        self.user = authz_user
        self.resource = fhir_resource

    def read(self):
        """Default case, FHIR objects all readable"""
        return True

    def unauth_read(self):
        """Override for unauthenticated reads (i.e. no token)"""
        raise Unauthorized(
            f"Unauthorized; can't view {self.resource['resourceType']}")

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

    def unauth_read(self):
        """Only allow if no patient is set in CarePlan"""
        if self.resource.get('subject'):
            raise Unauthorized(
                "Unauthorized can't view CarePlan with well defined 'subject'")
        return True

    def write(self):
        """Initial writes allowed, and updates if same patient"""
        if not self.user.patient_id():
            return True
        if not self.owned:
            raise Unauthorized("Write CarePlan failed; mismatched owner")


class AuthzCheckCommunication(AuthzCheckResource):
    def __init__(self, authz_user, fhir_resource):
        super().__init__(authz_user, fhir_resource)

    def write(self):
        """Initial writes allowed, and updates if same patient"""
        # allow for time being
        return True


class AuthzCheckDocumentReference(AuthzCheckResource):
    def __init__(self, authz_user, fhir_resource):
        super().__init__(authz_user, fhir_resource)

    def unauth_read(self):
        """DocumentReferences wide open for reads"""
        return True


class AuthzCheckPatient(AuthzCheckResource):
    def __init__(self, authz_user, fhir_resource):
        super().__init__(authz_user, fhir_resource)

    def _kc_ident_in_resource(self):
        """Keycloak Identifier found in FHIR Resource

        If the authorized user's JWT includes a keycloak system and value
        matching an identifier within the patient resource, return True
        """
        kc_sys_ids = [
            ident for ident in self.resource.get('identifier', []) if
            ident['system'] == self.user.kc_identifier_system]
        if not kc_sys_ids:
            return False
        if len(kc_sys_ids) != 1:
            raise ValueError(
                "unexpected multiple KC identifiers on Patient "
                f"{self.resource['id']}")
        return kc_sys_ids[0]['value'] == self.user.kc_identifier_value

    def read(self):
        """Only owning patient may read"""
        if not self._kc_ident_in_resource():
            raise Unauthorized("authorized identifier not found")
        return True

    def write(self):
        """Initial writes allowed, and updates if same patient"""
        if not self._kc_ident_in_resource():
            raise Unauthorized("authorized identifier not found")
        return True


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
    elif t == 'Communication':
        return AuthzCheckCommunication(authz_user, resource)
    elif t == 'DocumentReference':
        return AuthzCheckDocumentReference(authz_user, resource)
    elif t == 'QuestionnaireResponse':
        return AuthzCheckQuestionnaireResponse(authz_user, resource)
    elif t == 'Patient':
        return AuthzCheckPatient(authz_user, resource)
    else:
        return AuthzCheckResource(authz_user, resource)


class UnauthorizedUser(object):
    """Back door for unauthorized resource access"""

    def check(self, verb, fhir):
        """Raises Unauthorized unless user has authority to verb the contents

        :param verb: 'read' or 'write'
        :param fhir: JSON formatted FHIR contents for which an exception
          must exist in the matching check resource class to allow for
          unauthorized access, or Unauthorized will be raised
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


class AuthorizedUser(object):

    def __init__(self, jwt_payload):
        self.email = jwt_payload['email']
        self.kc_identifier_system = jwt_payload['iss']
        self.kc_identifier_value = jwt_payload['sub']

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

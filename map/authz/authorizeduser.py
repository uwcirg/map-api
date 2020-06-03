"""Authorization"""
from flask import current_app
import json
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError
from werkzeug.exceptions import Unauthorized

from map.fhir import Bundle, HapiRequest


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


class AuthzCheckResource(object):
    """Base class for FHIR Resource authorization check"""
    def __init__(self, authz_user, fhir_resource):
        self.user = authz_user
        self.resource = fhir_resource

    def read(self):
        """Default case, FHIR objects all readable"""
        return self.resource

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
            return self.resource

    def unauth_read(self):
        """Only allow if no patient is set in CarePlan"""
        if self.resource.get('subject'):
            raise Unauthorized(
                "Unauthorized can't view CarePlan with well defined 'subject'")
        return self.resource

    def write(self):
        """Initial writes allowed, and updates if same patient"""
        if not self.owned:
            raise Unauthorized("Write CarePlan failed; mismatched owner")
        return self.resource


class AuthzCheckConsent(AuthzCheckResource):
    def __init__(self, authz_user, fhir_resource):
        super().__init__(authz_user, fhir_resource)

    def write(self):
        """Allow consent writes"""
        return self.resource


class AuthzCheckCommunication(AuthzCheckResource):
    def __init__(self, authz_user, fhir_resource):
        super().__init__(authz_user, fhir_resource)

    def unauth_read(self):
        """Communication with matching identifier available for reads

        The configured `category` is used to tag Communications displayed
        prior to login - allow access if present.

        """
        open_communication = current_app.config.get("CODE_SYSTEM")[
            'open_communication']
        for i in self.resource.get('category', []):
            for coding in i['coding']:
                if coding == open_communication:
                    return self.resource

        raise Unauthorized(
            "Unauthorized; 'category' allowing unauthorized access not found")

    def write(self):
        """Writes allowed for now, to mark communications as read"""
        return self.resource


class AuthzCheckDocumentReference(AuthzCheckResource):
    def __init__(self, authz_user, fhir_resource):
        super().__init__(authz_user, fhir_resource)

    def unauth_read(self):
        """DocumentReferences wide open for reads"""
        return self.resource


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
        result = kc_sys_ids[0]['value'] == self.user.kc_identifier_value
        # Cache internals in self.user if this happens to be the owners
        if result:
            self.user.extract_internals()
        return result

    def same_user(self):
        """Returns true if resource refers to same user as self"""
        return self._kc_ident_in_resource()

    def read(self):
        """User's role determines read access"""
        # Admins get carte blanche
        if 'admin' in self.user.roles:
            return self.resource

        # Org admin and staff can only view patients with consents
        # on the same organization
        if 'org_admin' in self.user.roles or 'org_staff' in self.user.roles:
            if (self.same_user() or
                    self.user.consented_same_org(self.resource)):
                return self.resource
            raise Unauthorized()

        # Having not hit a role case above, user may only view
        # self owned resource
        if not self.same_user():
            raise Unauthorized("authorized identifier not found")
        return self.resource

    def write(self):
        """Initial writes allowed, and updates if same patient"""
        if not self._kc_ident_in_resource():
            raise Unauthorized("authorized identifier not found")
        return self.resource


class AuthzCheckQuestionnaireResponse(AuthzCheckResource):
    def __init__(self, authz_user, fhir_resource):
        super().__init__(authz_user, fhir_resource)

    owned = True

    def read(self):
        """Only owning patient may read"""
        if self.owned:
            return self.resource

    def write(self):
        """Initial writes allowed, and updates if same patient"""
        if not self.user.patient_id():
            return self.resource
        if not self.owned:
            raise Unauthorized(
                "Write QuestionnaireResponse failed; mismatched owner")
        return self.resource


def authz_check_resource(authz_user, resource):
    """Factory returns appropriate instance for authorization check"""
    t = resource['resourceType']
    if t == 'CarePlan':
        return AuthzCheckCarePlan(authz_user, resource)
    elif t == 'Communication':
        return AuthzCheckCommunication(authz_user, resource)
    elif t == 'Consent':
        return AuthzCheckConsent(authz_user, resource)
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

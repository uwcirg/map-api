from flask import current_app
from werkzeug.exceptions import Unauthorized


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
        raise Unauthorized(f"can't view {self.resource['resourceType']}")

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
                "can't view CarePlan with well defined 'subject'")
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
            "'category' allowing unauthorized access not found")

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

        if 'org_admin' in self.user.roles or 'org_staff' in self.user.roles:
            # Org admin and staff can only view patients with consents
            # on the same organization, UNLESS configuration is set to ignore
            if current_app.config['SAME_ORG_CHECK'] != True:
                return self.resource

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

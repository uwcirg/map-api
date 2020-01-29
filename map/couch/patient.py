"""Patient / Couch API

Each patient gets their own couch db, and couch user.
"""
from couchdb.http import ResourceNotFound, ServerError
from flask import current_app
from binascii import hexlify
from uuid import uuid4

from .server import couch
from ..fhir import Bundle, CarePlan, HapiRequest
from ..utils import dt_or_none

COUCHDB_SYSTEM = 'couchdb-name'
IDENTIFIER = 'identifier'
SYSTEM = 'system'
VALUE = 'value'
ALLOW_USERDB_REPLACEMENT = True


def dbname_from_id(patient_fhir):
    """Return couch dbname from Patient's identifiers, if present"""
    if IDENTIFIER in patient_fhir:
        for i in patient_fhir[IDENTIFIER]:
            if i[SYSTEM] == COUCHDB_SYSTEM:
                return i[VALUE]


def dbname_from_username(username):
    """reimplementation of couch hashing for user's db name

    With ``couch_peruser`` configured, a db is automatically generated
    with every add_user() call.  No API support to obtain the name of the
    generated db, but documented to be hashed as implemented below, including
    a common ``userdb-`` prefix

    :param username: couch username used to generate db name
    :return: name of user's personal couchdb

    """
    suffix = hexlify(username.encode('utf-8'))
    return 'userdb-{}'.format(suffix.decode('utf-8'))


class CouchPatientDB(object):
    """Build/sync user db for patient and related FHIR resources"""

    def __init__(self, patient_fhir):
        """Initialize couch user db for given patient"""
        self.userdb_name = None
        self.patient_fhir = patient_fhir
        self.sync_patient()
        self.sync_related_resources()

    def generate_user_db(self):
        """Add new couch user and db, store identifier and push upstream"""
        # Start with a fresh uuid as the user's 'name'
        username = uuid4().hex
        self.userdb_name = dbname_from_username(username)

        # Add the dbname as an identifier to the patient FHIR
        couch_id = {SYSTEM: COUCHDB_SYSTEM, VALUE: self.userdb_name}
        if IDENTIFIER not in self.patient_fhir:
            self.patient_fhir[IDENTIFIER] = [couch_id]
        else:
            # Overwrite if necessary:
            id_persisted = False
            for i in self.patient_fhir[IDENTIFIER]:
                if i[SYSTEM] == COUCHDB_SYSTEM:
                    i[VALUE] = self.userdb_name
                    id_persisted = True
            if not id_persisted:
                self.patient_fhir[IDENTIFIER].append(couch_id)

        # Push identifier upstream
        HapiRequest.put_resource(self.patient_fhir)

        # Add user to couch, which also generates db
        couch.add_user(name=username, password='auto', roles=['patient'])

        # Couch is configured (see ``couch_defaults.ini``) to generate a
        # per-user database on user creation.  Apparent race condition requires
        # the try try model below.
        db = None
        try:
            current_app.logger.debug("attempt to access new db")
            db = couch[self.userdb_name]
        except ResourceNotFound:
            current_app.logger.debug("404 on new user db")

        if not db:
            try:
                current_app.logger.debug("attempt to directly create new db")
                couch.create(self.userdb_name)
                current_app.logger.debug("success")
            except ServerError as e:
                assert 'conflict' in str(e)
            finally:
                db = couch[self.userdb_name]

        # Now persist the given/modified patient document
        self.sync_document(self.patient_fhir)

    def sync_document(self, document):
        """sync contents of any given document w/ couch user db

        Document may or may not previously exist in couch.  Guaranteed to
        exist after call.  If a newer version is found in couch, that will
        be returned.

        All documents are keyed by ``ResourceType/Id``, such as
        ``CarePlan/54``

        """
        key = f"{document['resourceType']}/{document['id']}"
        db = couch[self.userdb_name]
        if key not in db:
            db[key] = document
            return document

        # HAPI maintains last_updated (ISO 8601 format); replace if newer
        hapi_time = dt_or_none(
            document.get('meta', {}).get('lastUpdated'))
        couch_time = dt_or_none(db[key].get('meta', {}).get('lastUpdated'))
        if (couch_time and not hapi_time) or (couch_time > hapi_time):
            current_app.logger.debug(
                f"found newer data in couch for {key}; push to HAPI")
            document = HapiRequest.put_resource(db[key])

        elif (hapi_time and not couch_time) or (hapi_time > couch_time):
            current_app.logger.debug(
                f"found newer data in HAPI for {key}; push to couch")
            # Set couch id, revision to match current to avoid save conflict
            document['_id'] = key
            document['_rev'] = db[key].rev
            db[key] = document

        return document

    def sync_patient(self):
        """sync with couch

        If couch db exists for given patient, sync couch and HAPI such that
        the most recent (via meta.lastUpdated) patient_fhir resides in both.

        If no couch db exists for given patient, a new couch user and matching
        couch db will be generated, populated with the given patient_fhir.

        Returns potentially modified patient_fhir, if newer version is found

        """
        self.userdb_name = dbname_from_id(self.patient_fhir)
        if not self.userdb_name:
            # Generate couch user, database and persist patient_fhir
            self.generate_user_db()
            current_app.logger.info(
                f"New user db generated: {self.userdb_name}")
            return

        # Confirm existing db record is in sync
        if self.userdb_name not in couch:
            # Happens when changing servers - trigger replacement via new db
            if not ALLOW_USERDB_REPLACEMENT:
                raise RuntimeError(
                    f"Pre-existing user db not found {self.userdb_name}")
            self.generate_user_db()
            current_app.logger.info(
                f"Replacing user db, generated: {self.userdb_name}")
            return

        current_app.logger.info(
            f"Pre-existing user db found: {self.userdb_name}")
        self.patient_fhir = self.sync_document(self.patient_fhir)

    def sync_related_resources(self):
        """Pull any related resources into the couch user db for patient"""

        related_resource_types = (
            "CarePlan", "Questionnaire", "Procedure", "QuestionnaireResponse")

        patient_id = self.patient_fhir['id']

        # CarePlan
        qb_ids = set()
        cp_ids = set()
        for cp_doc in CarePlan.documents(patient_id=patient_id):
            best_doc = self.sync_document(cp_doc)
            cp_ids.add(best_doc['id'])
            for qb_id in CarePlan.questionnaire_ids(best_doc):
                qb_ids.add(qb_id)

        # Procedure
        for cp_id in cp_ids:
            procs = HapiRequest.find_bundle(
                "Procedure", {'based-on': f'CarePlan/{cp_id}'})
            for proc in Bundle(procs).resources():
                self.sync_document(proc)

        # Questionnaire
        for qb_id in qb_ids:
            qb_doc = HapiRequest.find_by_id('Questionnaire', qb_id)
            self.sync_document(qb_doc)

        # QuestionnaireResponse
        for cp_id in cp_ids:
            qrs = HapiRequest.find_bundle(
                "QuestionnaireResponse", {'based-on': f'CarePlan/{cp_id}'})
            for qr in Bundle(qrs).resources():
                self.sync_document(qr)


"""Patient / Couch API

Each patient gets their own couch db, and couch user.
"""
from couchdb.http import ResourceNotFound, ServerError
from flask import current_app
from binascii import hexlify
from uuid import uuid4

from ..fhir.hapi import HapiRequest
from ..utils import dt_or_none
from .server import couch

COUCHDB_SYSTEM = 'couchdb-name11'
IDENTIFIER = 'identifier'
SYSTEM = 'system'
VALUE = 'value'


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
    generated db, but documented to be hashed as follows, including a
    commone prefix

    :param username: couch username used to generate db name
    :return: name of user's personal couchdb

    """
    suffix = hexlify(username.encode('utf-8'))
    return 'userdb-{}'.format(suffix.decode('utf-8'))


def generate_user_db(patient_fhir):
    """Add new couch user and db, store identifier and push upstream"""
    # Start with a fresh uuid as the user's 'name'
    username = uuid4().hex
    dbname = dbname_from_username(username)

    # Add the dbname as an identifier to the patient FHIR
    couch_id = {SYSTEM: COUCHDB_SYSTEM, VALUE: dbname}
    if IDENTIFIER not in patient_fhir:
        patient_fhir[IDENTIFIER] = [couch_id]
    else:
        patient_fhir[IDENTIFIER].append(couch_id)

    # Push identifier upstream
    HapiRequest.put_patient(patient_fhir)

    # Add user to couch, which also generates db
    couch.add_user(name=username, password='auto', roles=['patient'])

    # Couch is configured (see ``couch_defaults.ini``) to generate a
    # per-user database on user creation.  Apparent race condition requires
    # the try try model below.
    db = None
    try:
        current_app.logger.debug("attempt to access new db")
        db = couch[dbname]
    except ResourceNotFound:
        current_app.logger.debug("404 on new user db")

    if not db:
        try:
            current_app.logger.debug("attempt to directly create new db")
            couch.create(dbname)
            current_app.logger.debug("success")
        except ServerError as e:
            assert 'conflict' in str(e)
        finally:
            db = couch[dbname]

    # Persist the given patient document into the user's couch database
    db['Patient'] = patient_fhir
    return dbname


def sync_patient(patient_fhir):
    """Given FHIR Patient Resource, sync with couch

    If couch db exists for given patient, sync couch and HAPI such that
    the most recent (via meta.lastUpdated) patient_fhir resides in both.

    If no couch db exists for given patient, a new couch user and matching
    couch db will be generated, populated with the given patient_fhir.

    Returns potentially modified patient_fhir, if newer version is found

    """
    userdb = dbname_from_id(patient_fhir)
    if not userdb:
        # Generate couch user, database and persist patient_fhir
        userdb = generate_user_db(patient_fhir)
        current_app.logger.info(f"New user db generated: {userdb}")
        return patient_fhir

    # Confirm existing db record is in sync
    if userdb not in couch:
        raise RuntimeError(f"Pre-existing user db not found {userdb}")
    current_app.logger.info(f"Pre-existing user db found: {userdb}")
    db = couch[userdb]
    if 'Patient' not in db:
        db['Patient'] = patient_fhir
        return patient_fhir

    # HAPI maintains last_updated (ISO 8601 format); replace if newer
    hapi_time = dt_or_none(patient_fhir.get('meta', {}).get('lastUpdated'))
    couch_time = dt_or_none(db['Patient'].get('meta', {}).get('lastUpdated'))
    if (couch_time and not hapi_time) or (couch_time > hapi_time):
        current_app.logger.debug(
            "found newer data in couch for Patient "
            f"{patient_fhir['id']}; push to HAPI")
        patient_fhir = HapiRequest.put_patient(db['Patient'])

    elif (hapi_time and not couch_time) or (hapi_time > couch_time):
        current_app.logger.debug(
            "found newer data in HAPI for Patient "
            f"{patient_fhir['id']}; push to couch")
        # Set couch id, revision to match current to avoid save conflict
        patient_fhir['_id'] = 'Patient'
        patient_fhir['_rev'] = db['Patient'].rev
        db['Patient'] = patient_fhir

    return patient_fhir

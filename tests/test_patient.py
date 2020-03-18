import json
from pytest import fixture, raises
import os

from map.couch.patient import (
    CouchPatientDB,
    COUCHDB_IDENTIFIER_SYSTEM,
    dbname_from_id,
    dbname_from_username,
)


@fixture
def pre_id_patient(request):
    data_dir, _ = os.path.splitext(request.module.__file__)
    with open(os.path.join(data_dir, "pre_id_patient.json"), 'r') as json_file:
        data = json.load(json_file)
    return CouchPatientDB(data)


def test_couch_patient_pre_id(pre_id_patient):
    assert pre_id_patient.username is None
    assert pre_id_patient.userdbname is None
    with raises(ValueError):
        pre_id_patient.couch_id()


def test_couch_patient_id_generate():
    patient = CouchPatientDB(None)
    patient.username = 'fakename'
    patient.userdbname = 'fakedbname'
    expect_id = {
        'system': COUCHDB_IDENTIFIER_SYSTEM,
        'value': ':'.join((patient.username, patient.userdbname))}
    assert expect_id == patient.couch_id()


def test_parse_identifier(pre_id_patient):
    identifier = {
        'system': 'couchdb-user:db',
        'value': 'ed2932436ea3444e95bed523275828cb:userdb-6564323933323433366561333434346539356265643532333237353832386362'}
    pre_id_patient.patient_fhir['identifier'].append(identifier)
    username, dbname = dbname_from_id(pre_id_patient.patient_fhir)
    assert username == 'ed2932436ea3444e95bed523275828cb'
    assert dbname == 'userdb-6564323933323433366561333434346539356265643532333237353832386362'


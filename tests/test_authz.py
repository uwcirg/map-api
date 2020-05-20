from datetime import datetime, timedelta
import json
import jwt
import os
from pytest import fixture

from .conftest import SECRET
from map.authz.authorizeduser import AuthorizedUser


def generate_claims(email, sub, roles):
    now = datetime.utcnow()
    in_five = now + timedelta(minutes=5)
    claims = {
        'iss': "https://keycloak-dev.cirg.washington.edu/auth/realms/Stayhome",
        'iat': now.timestamp(),
        'exp': in_five.timestamp(),
        'sub': sub,
        'realm_access': {'roles': roles if roles else []},
        'email': email}
    return claims


def generate_jwt(email='fake@testy.org', sub='fake-subject', roles=None):
    claims = generate_claims(email, sub, roles)
    encoded = jwt.encode(claims, SECRET, algorithm='HS256')
    return encoded.decode('utf-8')


@fixture
def admin_jwt():
    return generate_jwt(roles=('admin',))


@fixture
def org_staff_jwt():
    return generate_jwt(
        sub="6c9d2b3f-a674-4866-9b0c-da0020d36ca7", roles=('org_staff',))


@fixture
def prefix(app):
    return app.config.get('API_PREFIX')


@fixture
def consented_patient_bundle(request):
    data_dir, _ = os.path.splitext(request.module.__file__)
    with open(os.path.join(
            data_dir, "consented_patient.json"), 'r') as json_file:
        data = json.load(json_file)
    return data


@fixture
def patient_bundle(request):
    data_dir, _ = os.path.splitext(request.module.__file__)
    with open(os.path.join(data_dir, "patient.json"), 'r') as json_file:
        data = json.load(json_file)
    return data


@fixture
def patient_1415(request):
    data_dir, _ = os.path.splitext(request.module.__file__)
    with open(os.path.join(data_dir, "patient_1415.json"), 'r') as json_file:
        data = json.load(json_file)
    return data


def test_patient_noauth(client, mocker, prefix, patient_bundle):
    """without auth header, should see 401"""
    mock_hapi = mocker.patch('map.fhir.HapiRequest.find_bundle')
    mock_hapi.return_value = patient_bundle, 200

    results = client.get('/'.join((prefix, 'Patient')))
    assert results.status_code == 401


def test_patient_via_admin(
        admin_jwt, client, mocker, prefix, patient_bundle):
    """with mock admin header, should see all results"""
    mock_hapi = mocker.patch('map.fhir.HapiRequest.find_bundle')
    mock_hapi.return_value = patient_bundle, 200

    results = client.get('/'.join((prefix, 'Patient')), headers={
        'Authorization': 'Bearer {}'.format(admin_jwt)})
    assert results.status_code == 200


def test_patient_self(client, mocker, prefix, patient_1415):
    patient_jwt = generate_jwt(sub="6c9d2b3f-a674-4866-9b0c-da0020d36ca7")
    mock_hapi = mocker.patch('map.fhir.HapiRequest.find_by_id')
    mock_hapi.return_value = patient_1415, 200

    results = client.get('/'.join((prefix, 'Patient/1415')), headers={
        'Authorization': 'Bearer {}'.format(patient_jwt)})
    assert results.status_code == 200


def test_extract_internals(mocker, patient_1415):
    mock_hapi = mocker.patch('map.fhir.HapiRequest.find_one')
    mock_hapi.return_value = patient_1415, 200

    mock_payload = generate_claims(
        email='f@f', sub="6c9d2b3f-a674-4866-9b0c-da0020d36ca7", roles=[])
    test_user = AuthorizedUser(mock_payload)
    test_user.extract_internals(patient_1415)
    assert test_user._patient_id == "1415"
    assert test_user._org_id == "1465"


def test_consented_patients(mocker, consented_patient_bundle):
    """test loading consented patients within AuthorizedUser"""

    # mock results looking for consented patients
    mock_consented_patient_bundle = mocker.patch(
        'map.fhir.HapiRequest.find_bundle')
    mock_consented_patient_bundle.return_value = (
        consented_patient_bundle, 200)

    mock_payload = generate_claims(
        email='f@f', sub="6c9d2b3f-a674-4866-9b0c-da0020d36ca7", roles=[])
    test_user = AuthorizedUser(mock_payload)
    results = test_user.consented_users(org_id=1465)
    assert len(results) == 16
    assert "1791" in results


def test_consented_patients_query(
        org_staff_jwt, client, mocker, prefix, patient_1415, patient_bundle):
    """org_staff should get like org consented patients"""

    # mock results of generic patient search
    mock_patient_bundle = mocker.patch('map.fhir.HapiRequest.find_bundle')
    mock_patient_bundle.return_value = patient_bundle, 200

    # mock results when looking up acting user's internal ids
    mock_patient = mocker.patch('map.fhir.HapiRequest.find_one')
    mock_patient.return_value = patient_1415, 200

    # mock list of consented patients
    mock_consented = mocker.patch(
        "map.authz.authorizeduser.AuthorizedUser.consented_users")
    mock_consented.return_value = {'41', '1202', '1206', '1221', '1415'}

    # expect request to only include the one consented patient with common org
    results = client.get('/'.join((prefix, 'Patient')), headers={
        'Authorization': 'Bearer {}'.format(org_staff_jwt)})
    assert len(results.json['entry']) == 1
    assert results.json['entry'][0]['resource']['id'] == "41"

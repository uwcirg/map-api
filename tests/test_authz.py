from datetime import datetime, timedelta
import json
import jwt
import os
from pytest import fixture

from .conftest import SECRET


def generate_jwt(email='fake@testy.org', sub='fake-subject', roles=None):
    now = datetime.utcnow()
    in_five = now + timedelta(minutes=5)
    claims = {
        'iss': "https://keycloak-dev.cirg.washington.edu/auth/realms/Stayhome",
        'iat': now.timestamp(),
        'exp': in_five.timestamp(),
        'sub': sub,
        'realm_access': {'roles': roles},
        'email': email,
    }
    claims['realm_access'] = {'roles': roles if roles else []}
    encoded = jwt.encode(claims, SECRET, algorithm='HS256')
    return encoded.decode('utf-8')


@fixture
def admin_jwt():
    return generate_jwt(roles=('admin',))


@fixture
def prefix(app):
    return app.config.get('API_PREFIX')


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
    find_bundle = mocker.patch('map.fhir.HapiRequest.find_bundle')
    find_bundle.return_value = patient_bundle, 200

    results = client.get('/'.join((prefix, 'Patient')))
    assert results.status_code == 401


def test_patient_via_admin(
        admin_jwt, client, mocker, prefix, patient_bundle):
    """with mock admin header, should see all results"""
    find_bundle = mocker.patch('map.fhir.HapiRequest.find_bundle')
    find_bundle.return_value = patient_bundle, 200

    results = client.get('/'.join((prefix, 'Patient')), headers={
        'Authorization': 'Bearer {}'.format(admin_jwt)})
    assert results.status_code == 200


def test_patient_self(client, mocker, prefix, patient_1415):
    patient_jwt = generate_jwt(sub="6c9d2b3f-a674-4866-9b0c-da0020d36ca7")
    find_bundle = mocker.patch('map.fhir.HapiRequest.find_by_id')
    find_bundle.return_value = patient_1415, 200

    results = client.get('/'.join((prefix, 'Patient/1415')), headers={
        'Authorization': 'Bearer {}'.format(patient_jwt)})
    assert results.status_code == 200

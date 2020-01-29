import json
import os
from pytest import fixture
from map.fhir import Bundle


@fixture
def sample_bundle(request):
    data_dir, _ = os.path.splitext(request.module.__file__)
    with open(os.path.join(data_dir, "careplan.json"), 'r') as json_file:
        data = json.load(json_file)
    return Bundle(data)


def test_bundle_len(sample_bundle):
    assert len(sample_bundle) == 4


def test_bundle_gen(sample_bundle):
    expected = len(sample_bundle)
    for item in sample_bundle.resources():
        expected -= 1
        assert item['resourceType'] == 'CarePlan'
    assert expected == 0


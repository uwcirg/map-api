import json
import os
from pytest import fixture, raises
from map.fhir import Bundle


@fixture
def sample_bundle(request):
    data_dir, _ = os.path.splitext(request.module.__file__)
    with open(os.path.join(data_dir, "careplan.json"), 'r') as json_file:
        data = json.load(json_file)
    return Bundle(data)


@fixture
def sample_bundle_sans_total(request):
    data_dir, _ = os.path.splitext(request.module.__file__)
    with open(os.path.join(data_dir, "patient.json"), 'r') as json_file:
        data = json.load(json_file)
    return Bundle(data)


def test_bundle_len(sample_bundle):
    assert len(sample_bundle) == 4


def test_bundle_sans_total_len(sample_bundle_sans_total):
    assert len(sample_bundle_sans_total) == 20


def test_bundle_gen(sample_bundle):
    expected = len(sample_bundle)
    for item in sample_bundle.resources():
        expected -= 1
        assert item['resourceType'] == 'CarePlan'
    assert expected == 0


def test_remove_missing(sample_bundle):
    with raises(ValueError):
        sample_bundle.remove_entries(["12"])


def test_remove(sample_bundle):
    b4 = len(sample_bundle)
    sample_bundle.remove_entries(["155", "156"])
    assert len(sample_bundle) == b4 - 2
    for i in sample_bundle.resources():
        assert i['id'] != "155"


import json
from pytest import fixture
import os

from map.fhir import CarePlan


@fixture
def sample_careplan(request):
    data_dir, _ = os.path.splitext(request.module.__file__)
    with open(os.path.join(data_dir, "careplan.json"), 'r') as json_file:
        data = json.load(json_file)
    return data


def test_questionnaire_ids(sample_careplan):
    # Sample contains only Questionnaire/53
    assert ['53'] == [i for i in CarePlan.questionnaire_ids(sample_careplan)]

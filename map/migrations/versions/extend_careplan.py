"""Add additional Questionnaire to all appropriate CarePlans"""
from map.fhir import Bundle, HapiRequest, ResourceType

version = 1

missing_questionnaire = {
    "detail": {
      "instantiatesCanonical": [
        "Questionnaire/1376"
      ],
      "status": "scheduled",
      "doNotPerform": False,
      "description": "COVID-19 testing questionnaire"
    }
  }


def add_missing_questionnaire(cp):
    """adds missing if not already present"""
    dirty = False
    for q in cp['activity']:
        if (
                q['detail'].get('description', '') ==
                missing_questionnaire['detail']['description']):
            # already present; leave
            return cp, dirty

    cp['activity'].append(missing_questionnaire)
    dirty = True
    return cp, dirty


def upgrade():
    # ugly magic number from external config file:
    careplanTemplateId = 1058

    # Obtain all CarePlans based on the template, assigned to a Patient
    params = {'based-on': careplanTemplateId}
    results, _ = HapiRequest.find_bundle(
        resource_type=ResourceType.CarePlan.value, search_dict=params)
    care_plans = Bundle(results)
    for cp in care_plans.resources():
        if 'subject' not in cp:
            continue

        cp, changed = add_missing_questionnaire(cp)
        if changed:
            HapiRequest.put_resource(cp)

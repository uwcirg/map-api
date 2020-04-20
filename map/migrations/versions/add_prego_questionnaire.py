"""Add Pregnancy Questionnaire to all appropriate CarePlans"""
from flask import current_app
from map.fhir import Bundle, HapiRequest, ResourceType

version = 7

missing_questionnaire = {
    "detail": {
      "instantiatesCanonical": [
        "Questionnaire/1442"
      ],
      "status": "scheduled",
      "doNotPerform": False,
      "description": "Pregnancy questionnaire"
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
            print(
                "no change to CarePlan for %s" % cp['subject'])
            return cp, dirty

    cp['activity'].append(missing_questionnaire)
    dirty = True
    return cp, dirty


def upgrade():
    # ugly magic number from external config file:
    careplanTemplateId = 1058

    # Obtain all CarePlans based on the template, assigned to a Patient
    params = {'based-on': careplanTemplateId, '_count': 1000}
    results, _ = HapiRequest.find_bundle(
        resource_type=ResourceType.CarePlan.value, search_dict=params)
    care_plans = Bundle(results)
    for cp in care_plans.resources():
        if 'subject' not in cp:
            continue

        cp, changed = add_missing_questionnaire(cp)
        if changed:
            print(
                "Added missing Questionnaire to CarePlan %s for "
                "%s" % (cp['id'], str(cp['subject'])))
            result, status = HapiRequest.put_resource(cp)
            if status != 200:
                print(
                    "Failed with status %d: %s" % (status, result.text))

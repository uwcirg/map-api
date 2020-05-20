"""Purge obsolete consents and bogus patient accounts"""
from map.fhir import Bundle, HapiRequest, ResourceType

version = 8


def keep_best_per_tuple(consented_patient_bundle):
    by_patient_provision = dict()
    delete_consent_ids = []
    for con in consented_patient_bundle.resources():
        if con['resourceType'] != 'Consent':
            continue

        # As it's ordered by period, once a patient/provision is populated,
        # any additional matches are obsolete
        key = ':'.join((
            con['patient']['reference'],
            con['provision']['class'][0]['code']))
        if key in by_patient_provision:
            print(f"toss {con} \n keep {by_patient_provision[key]}")
            delete_consent_ids.append(con['id'])
        else:
            # record keeper, primarily for logging
            by_patient_provision[key] = con

    return delete_consent_ids


def upgrade():
    """Consents are now updated in place.  Delete obsolete"""
    # Consents are between a Patient and an Organization, then categorized
    # by a list of Code/Systems.  For each f(Patient, Org, Code) keep only
    # the one with the most recent `startDate`

    # working with our known Organizations, get the respective list of consents
    # for each
    consent_ids_to_delete = []
    for org_id in (1463, 1464, 1465, 1466, 1467, 1737):
        # query for patients with at least one consent on file
        consented_patients, status = HapiRequest.find_bundle("Consent", search_dict={
            'organization': '/'.join(("Organization", str(org_id))),
            '_include': "Consent.patient", '_count': 1000, '_sort': '-period'})
        assert status == 200
        consent_ids_to_delete.extend(keep_best_per_tuple(
            consented_patient_bundle=Bundle(consented_patients)))

    print("Purging %d obsolete Consents" % len(consent_ids_to_delete))
    for con_id in consent_ids_to_delete:
        HapiRequest.delete_by_id("Consent", con_id)

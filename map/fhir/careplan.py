from jmespath import search
from .bundle import Bundle
from .hapi import HapiRequest
from .resource_type import ResourceType


class CarePlan(object):
    """CarePlan FHIR resource API"""

    resource_type = ResourceType.CarePlan
    default_query_params = {'_id': '54'}

    @classmethod
    def default(cls):
        """Return the default CarePlan"""
        return HapiRequest.find_one(
            cls.resource_type.name, cls.default_query_params)

    @classmethod
    def subject_patient(cls, patient_id):
        """Returns bundle of CarePlans for which given patient is subject"""
        return HapiRequest.find_bundle(
            cls.resource_type.name,
            {"subject": f"Patient/{patient_id}"})

    @classmethod
    def documents(cls, patient_id):
        """Generator to yield all CarePlan documents for given patient"""
        # First the default, used as the basis for all patients
        yield cls.default()

        # Then, every CarePlan assigned to the patient
        patients_care_plans = cls.subject_patient(patient_id)
        for item in Bundle(patients_care_plans).resources():
            yield item

    @classmethod
    def questionnaire_ids(cls, document):
        """returns all Questionnaire id refs from CarePlan"""
        jsonpath = "activity[*].detail.instantiatesCanonical"
        for reflist in search(jsonpath, document):
            for ref in reflist:
                if not ref.startswith('Questionnaire/'):
                    continue
                yield ref[len('Questionnaire/'):]

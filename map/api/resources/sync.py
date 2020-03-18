from flask import request
from flask_restful import Resource
from werkzeug.exceptions import BadRequest, NotFound

from map.couch import CouchPatientDB
from map.fhir import HapiRequest, ResourceType


class Sync(Resource):
    """Trigger sync between HAPI and Couch stores
    """

    def get(self, resource_type):
        ResourceType.validate(resource_type)
        if resource_type != 'Patient':
            raise BadRequest("Only syncing Patient resources at this time")
        hapi_pat = HapiRequest.find_bundle(resource_type, request.args)

        # Search returns bundle - if one was found, extract and sync
        hapi_pat.raise_for_status()
        bundle = hapi_pat.json()
        assert bundle.get('resourceType') == 'Bundle'
        if bundle.get('total') == 1:
            patient_fhir = bundle['entry'][0]['resource']
            patient = CouchPatientDB(patient_fhir)
            return patient.sync()
        else:
            raise NotFound()

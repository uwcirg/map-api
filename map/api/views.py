from flask import Blueprint
from flask_restful import Api

from map.api.resources import (
    FhirResource,
    FhirSearch,
    UserResource,
    UserList,
)


# naming the supported FHIR version, r4
# see https://www.hl7.org/fhir/history.html
blueprint = Blueprint('api', __name__, url_prefix='/api/r4')
api = Api(blueprint)


api.add_resource(FhirResource, '/<string:resource_type>/<int:patient_id>')
api.add_resource(FhirSearch, '/<string:resource_type>')
api.add_resource(UserResource, '/users/<int:user_id>')
api.add_resource(UserList, '/users')

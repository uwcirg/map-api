from flask import Blueprint
from flask_restful import Api

from map.api.resources import (
    FhirResource,
    FhirSearch,
)
from map.config import API_PREFIX


blueprint = Blueprint('api', __name__, url_prefix=API_PREFIX)
api = Api(blueprint)


api.add_resource(FhirResource, '/<string:resource_type>/<int:resource_id>')
api.add_resource(FhirSearch, '/<string:resource_type>')

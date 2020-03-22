from flask import Blueprint
from flask_restful import Api

from map.api.resources import (
    FhirResource,
    FhirSearch,
    Sync,
    UserResource,
    UserList,
)
from map.config import API_PREFIX


blueprint = Blueprint('api', __name__, url_prefix=API_PREFIX)
api = Api(blueprint)


api.add_resource(FhirResource, '/<string:resource_type>/<int:resource_id>')
api.add_resource(FhirSearch, '/<string:resource_type>')

# Removing following views until adequately secured
#api.add_resource(Sync, '/sync/<string:resource_type>')
#api.add_resource(UserResource, '/users/<int:user_id>')
#api.add_resource(UserList, '/users')

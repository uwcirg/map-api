"""Default configuration

Use env var to override
"""
import os

# naming the supported FHIR version, r4
# see https://www.hl7.org/fhir/history.html
API_PREFIX = '/api/r4'

ENV = os.getenv("FLASK_ENV")
HAPI_URL = os.getenv("HAPI_URL")
AUTHZ_JWKS_JSON = os.getenv("AUTHZ_JWKS_JSON")
SERVER_NAME = os.getenv("SERVER_NAME")
DEBUG = ENV == "development"
SECRET_KEY = os.getenv("SECRET_KEY")

SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")
SQLALCHEMY_TRACK_MODIFICATIONS = False

JWT_BLACKLIST_ENABLED = True
JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']

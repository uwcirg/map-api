"""Default configuration

Use env var to override
"""
import os

ENV = os.getenv("FLASK_ENV")
HAPI_URL = os.getenv("HAPI_URL")
SERVER_NAME = os.getenv("SERVER_NAME")
DEBUG = ENV == "development"
SECRET_KEY = os.getenv("SECRET_KEY")

SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")
SQLALCHEMY_TRACK_MODIFICATIONS = False

JWT_BLACKLIST_ENABLED = True
JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']

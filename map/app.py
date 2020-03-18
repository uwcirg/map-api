from flask import Flask
from flask_cors import CORS
from io import StringIO
from os import getenv

from map import auth, api
from map.extensions import db, jwt, migrate


def create_app(testing=False, cli=False):
    """Application factory, used to create application
    """
    app = Flask('map')
    app.config.from_object('map.config')

    if testing is True:
        app.config['SECRET_KEY'] = 'nonsense-testing-key'
        app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////tmp/test-map.db"
        app.config['TESTING'] = True

    configure_extensions(app, cli)
    register_blueprints(app)

    if getenv("DUMP_CONFIG", None):
        buf = StringIO()
        for k, v in app.config.items():
            buf.write("{}: {}\n".format(str(k), str(v)))
        app.logger.info(buf.getvalue())

    # Enable CORS from localhost dev versions and prod hosts
    CORS(app, origins=[
        'http://127.0.0.1:8888',
        'http://lo.lo:8888',
        'http://localhost:8888',
        'https://stayhome.cirg.washington.edu'])

    return app


def configure_extensions(app, cli):
    """configure flask extensions
    """
    db.init_app(app)
    jwt.init_app(app)

    if cli is True:
        migrate.init_app(app, db)


def register_blueprints(app):
    """register all blueprints for application
    """
    app.register_blueprint(auth.views.blueprint)
    app.register_blueprint(api.views.blueprint)

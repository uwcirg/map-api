import couchdb
from os import getenv


def _couch_url():
    host = getenv('COUCHDB_HOST', '127.0.0.1')
    user = getenv('COUCHDB_USER')
    password = getenv('COUCHDB_PASSWORD')
    return f"http://{user}:{password}@{host}:5984"


couch = couchdb.Server(url=_couch_url())

# MAP API
API service for MAP (Mobile Assistance for Patients) application client use

## Deploy MAP API
Clone this repository, copy `default.env` to `.env` in the
root and apply the appropriate values.

Use `docker-compose` to build and deploy the service:
```console
$ docker-compose build web
$ docker-compose up -d
```

*WARNING*: `couch-db` must be initialized after installation.  See
[Single Node Setup](http://docs.couchdb.org/en/stable/setup/cluster.html#the-cluster-setup-wizard)

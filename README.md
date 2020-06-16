# MAP API
API service for MAP (Mobile Assistance for Patients) application client use.
As a proxy service to the underlying FHIR Resource store, typically 
[HAPI](https://hapifhir.io/), the MAP API can also serve as an authorization
proxy.

[![Docker Image Version (latest semver)](https://img.shields.io/docker/v/uwcirg/map-api?label=latest%20release&sort=semver)](https://hub.docker.com/repository/docker/uwcirg/map-api)

## Deploy MAP API
Clone this repository, copy `default.env` to `.env` in the
root and apply the appropriate values.

Use `docker-compose` to build and deploy the service:
```console
$ docker-compose build web
$ docker-compose up -d
```

*WARNING*: If using couch as an intermediate client store, `couch-db` must
be initialized after installation.  See
[Single Node Setup](http://docs.couchdb.org/en/stable/setup/cluster.html#the-cluster-setup-wizard)

## Authorization

See implementation in ``map-api/map/authz`` and use from
endpoints defined in ``map-api/map/api/resources``

Given a valid JWT in the ``authorization`` header, an instance
of ``AuthorizedUser`` is generated.  Read request (aka GET) include
an ``UnauthorizedUser`` fallback for evaluation when a request
does not include a valid JWT Bearer token.

A write (PUT/POST) request is then checked, using
``AuthorizedUser.check(resource)`` and only passed through to HAPI if
valid, 401 raised otherwise.

A read (GET) request is passed through to HAPI and then validated on
the way out (via ``AuthorizedUser.check(resource)`` or 
``UnauthorizedUser.check(resource)``), as the FHIR data
is needed to perform the authorization check.  The content may be modified
on the way out, specifically to filter out portions of a search bundle
for which the user is not authorized to view.

For all of the above, the ``check()`` method calls the 
``authz_check_resource`` *factory* which returns a context appropriate
``AuthzCheckResource`` instance.  To define resource type specific checks,
derive ``AuthzCheckResource`` and plug into the factory.

Configuration enables toggling checks within the ``AuthzCheckResource``
hierarchy::
 - ``SAME_ORG_CHECK``: default True.  If set False, users with role
  ``org_staff`` or ``org_admin`` can see all patients.  By default such
  users can only see patients consented with a matching organization.

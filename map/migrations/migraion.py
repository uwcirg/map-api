from contextlib import contextmanager
from flask import current_app
import importlib.util
import os
import sys

from map.fhir import Bundle, HapiRequest, ResourceType
MIGRATION_SYSTEM = 'https://stayhome.app/migrations'
MIGRATION_VALUE = 'track_version'
INITIAL_VERSION = 0

INITIAL_MIGRATION_MARKER = {
    'resourceType': ResourceType.Basic.value,
    'identifier': [
        {'system': MIGRATION_SYSTEM, 'value': MIGRATION_VALUE}],
    'code': {'coding': [{
        'system': MIGRATION_SYSTEM, 'code': INITIAL_VERSION}]},
}


@contextmanager
def add_to_path(p):
    """Context to temporarily extend sys.path for migration loading"""
    old_path = sys.path
    sys.path = sys.path[:]
    sys.path.insert(0, p)
    try:
        yield
    finally:
        sys.path = old_path


class Migration(object):

    def __init__(self):
        self.version_tracker = None
        self.init_migration()
        self.import_available()

    def init_migration(self):
        """Look for persisted migration version or add new and return"""
        basics, status = HapiRequest.find_bundle(
            ResourceType.Basic.value,
            search_dict={'identifier': f"{MIGRATION_SYSTEM}|{MIGRATION_VALUE}"})
        bundle = Bundle(basics)

        if len(bundle) > 1:
            raise ValueError(
                f"unexpected - found {len(bundle)} Basic FHIR Resources with "
                f"an identifier: {MIGRATION_SYSTEM}|{MIGRATION_VALUE}")

        if len(bundle) == 1:
            self.version_tracker = [b for b in bundle.resources()][0]
            return

        # Initialize with current settings
        response, status = HapiRequest.post_resource(
            resource=INITIAL_MIGRATION_MARKER)
        self.version_tracker = response

    def import_available(self):
        """Look up `available` upgrades, store in self keyed by version"""
        if hasattr(self, 'available_migrations'):
            # already done, bail
            return

        self.available_migrations = {}
        versions_dir = os.path.join(
            os.path.dirname(sys.modules[self.__module__].__file__),
            'versions')
        if not os.path.isdir(versions_dir):
            current_app.logger.warn(
                f"{versions_dir} directory not found; skipping migrations")
            return

        for f in os.listdir(versions_dir):
            if not f.endswith('.py'):
                continue
            mod_name = os.path.splitext(f)[0]
            file_path = os.path.join(versions_dir, f)
            with add_to_path(file_path):
                spec = importlib.util.spec_from_file_location(
                    mod_name, file_path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if mod.version in self.available_migrations:
                    raise ValueError(
                        "Conflict: multiple migrations for version "
                        f"{mod.version}")
                self.available_migrations[mod.version] = mod

    def current(self):
        """Returns current version, i.e. last migration run"""
        if len(self.version_tracker['code']['coding']) != 1:
            raise ValueError("Ill formed version code: {}".format(
                self.version_tracker['code']['coding']
            ))
        return int(self.version_tracker['code']['coding'][0]['code'])

    def mark_version(self, version_string):
        """record version_string as the last migration run"""
        self.version_tracker['code'] = {'coding': [{
            'system': MIGRATION_SYSTEM, 'code': version_string}]}
        response, status = HapiRequest.put_resource(self.version_tracker)
        self.version_tracker = response

    def run(self, step):
        """Run the given upgrade step"""
        mod = self.available_migrations[step]
        upgrade = getattr(mod, 'upgrade', None)
        if not callable(upgrade):
            raise ValueError(
                f"Migration '{mod.__file__}' missing `upgrade` def")

        # Run this step
        msg = mod.__doc__ or mod.__file__
        current_app.logger.warn("%s", msg)
        upgrade()

        # Having run said step, persist this fact
        self.mark_version(step)
        return step

    def upgrade(self):
        """Run all available migrations beyond current state"""
        max_available = INITIAL_VERSION
        if self.available_migrations:
            max_available = max(self.available_migrations.keys())

        last_run = self.current()
        while last_run < max_available:
            last_run += 1
            # skip over missing migrations
            if last_run not in self.available_migrations:
                continue
            self.run(last_run)

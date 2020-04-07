from map.fhir import Bundle, HapiRequest, ResourceType
MIGRATION_SYSTEM = 'https://stayhome.app/migrations'
MIGRATION_VALUE = 'track_version'
INITIAL_VERSION = '0'


class Migration(object):

    def __init__(self):
        self.version_tracker = None
        self.init_migration()

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
        version_tracker = {
            'resourceType': ResourceType.Basic.value,
            'identifier': [
                {'system': MIGRATION_SYSTEM, 'value': MIGRATION_VALUE}],
            'code': {'coding': [{
                'system': MIGRATION_SYSTEM, 'code': INITIAL_VERSION}]},
        }
        response, status = HapiRequest.post_resource(resource=version_tracker)
        self.version_tracker = response

    def current(self):
        """Returns current version, i.e. last migration run"""
        if len(self.version_tracker['code']['coding']) != 1:
            raise ValueError("Ill formed version code: {}".format(
                self.version_tracker['code']['coding']
            ))
        return self.version_tracker['code']['coding'][0]['code']

    def mark_version(self, version_string):
        """record version_string as the last migration run"""
        self.version_tracker['code'] = {'coding': [{
            'system': MIGRATION_SYSTEM, 'code': version_string}]}
        response, status = HapiRequest.put_resource(self.version_tracker)
        self.version_tracker = response

    def run(self, step):
        """Run the given upgrade step"""
        # TODO: obtain and run

        # Having run said step, persist this fact
        self.mark_version(step)
        return step

    def upgrade(self):
        """Run all available migrations beyond current state"""
        max_available = 1
        while int(self.current()) < max_available:
            self.run(int(self.current()) + 1)

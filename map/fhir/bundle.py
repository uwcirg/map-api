class Bundle(object):
    """API for easy iteration over FHIR bundles"""

    def __init__(self, bundle):
        self.bundle = bundle
        assert bundle["resourceType"] == "Bundle"

    def __len__(self):
        return self.bundle["total"]

    def resources(self):
        """generator to return each resource in the bundle"""
        for entry in self.bundle['entry']:
            yield entry["resource"]

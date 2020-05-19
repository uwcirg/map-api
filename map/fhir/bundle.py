class Bundle(object):
    """API for easy manipulation of FHIR bundles"""

    def __init__(self, bundle):
        self.bundle = bundle
        assert bundle["resourceType"] == "Bundle"

    def __len__(self):
        """Return len of entries or use `total` if bundle defined"""
        if 'total' in self.bundle:
            return self.bundle["total"]
        return len(self.bundle["entry"])

    def resources(self):
        """generator to return each resource in the bundle"""
        if 'entry' not in self.bundle:
            assert self.bundle['total'] == 0
            return
        for entry in self.bundle['entry']:
            yield entry["resource"]

    def remove_entries(self, ids):
        """remove given entries from the contained bundle

        :param ids: iterable of id values to remove from bundle
        :raises ValueError: if matching entries not found
        """
        count_b4 = self.__len__()
        keepers = []
        found_count = 0
        for i in self.bundle['entry']:
            if i['resource']['id'] not in ids:
                keepers.append(i)
            else:
                found_count += 1

        if found_count != len(ids):
            raise ValueError(f"unable to remove all {ids}; can't continue")

        if 'total' in self.bundle:
            self.bundle['total'] = count_b4 - found_count
        self.bundle['entry'] = keepers

IDENTIFIER = 'identifier'
SYSTEM = 'system'
VALUE = 'value'


def identifier_with_system(document, system):
    """Returns identifier if document contains one with matching system"""
    if IDENTIFIER not in document:
        return None

    match = [i for i in document[IDENTIFIER] if i[SYSTEM] == system]
    return match[0] if match else None


def update_identifier(document, identifier):
    """Update the value of the given identifier in the document

    Handles replacing or adding the given identifier, should
    identifiers be present or not

    :returns: updated document
    """
    if IDENTIFIER not in document:
        document[IDENTIFIER] = [identifier]
        return document

    # At least one identifier exists, determine if we can simply
    # append or must update
    updated = False
    for j, i in enumerate(document[IDENTIFIER]):
        if i[SYSTEM] == identifier[SYSTEM]:
            document[IDENTIFIER][j] = identifier
            updated = True
            break

    if not updated:
        document[IDENTIFIER].append(identifier)

    return document


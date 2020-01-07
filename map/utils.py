"""Utility functions with project scope"""
from dateutil import parser


def dt_or_none(value):
    """Given input generates datetime if valid

    :param value: string form to parse as datetime.  If None, return None.
    :return: datetime value if parsable, None if None passed.

    """
    if value is None or len(value) == 0:
        return None

    return parser.parse(value)

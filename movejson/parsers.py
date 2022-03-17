from datetime import datetime

from .exceptions import ParseError
from .ruleengine import BUSINESS_RULE_DATETIME_FORMAT


def parse_dict(value):
    if value is None:
        return None
    if type(value) == dict:
        return value
    raise ParseError("value must be a dict type.")


def parse_boolean(value):
    if value is None:
        return None
    if type(value) == bool:
        return value
    raise ParseError("value must be a bool type.")


def parse_numeric(value):
    if value is None:
        return None
    try:
        return float(str(value))
    except Exception as e:
        raise ParseError(e)


def parse_datetime(value):
    if value is None:
        return None
    try:
        if type(value) == int or type(value) == float:
            return datetime.utcfromtimestamp(value)
        return datetime.strptime(str(value), BUSINESS_RULE_DATETIME_FORMAT)
    except Exception as e:
        raise ParseError(e)


def parse_string(value):
    if value is None:
        return None
    if type(value) == datetime:
        return value.strftime(BUSINESS_RULE_DATETIME_FORMAT)
    if type(value) == int:
        value = float(value)
    return str(value)


def parse_numeric_list(value: list):
    if type(value) != list:
        raise ParseError("Value must be a list.")
    return list(map(lambda x: parse_numeric(x), value))


def parse_datetime_list(value: list):
    if type(value) != list:
        raise ParseError("Value must be a list.")
    return list(map(lambda x: parse_datetime(x), value))


def parse_string_list(value: list):
    if type(value) != list:
        raise ParseError("Value must be a list.")
    return list(map(lambda x: parse_string(x), value))


def parse_dict_list(value: list):
    if type(value) != list:
        raise ParseError("Value must be a list.")
    return list(map(lambda x: parse_dict(x), value))


def parse_boolean_list(value: list):
    if type(value) != list:
        raise ParseError("Value must be a list.")
    return list(map(lambda x: parse_boolean(x), value))

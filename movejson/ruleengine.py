import json
import os
import re
from inspect import signature, isclass

from .exceptions import DotNotationError, SubscriptionError, BusinessRuleEngineApiError

ALLOWED_TYPES = frozenset(("Dict", "Boolean", "String", "Numeric", "DateTime", "DictList", "BooleanList", "StringList",
                           "NumericList", "DateTimeList",))

ALLOWED_IMPLICIT_CONVERSIONS = frozenset((
    ("Boolean", "String"),
    ("Numeric", "String"),
    ("DateTime", "String"),
    ("BooleanList", "StringList"),
    ("NumericList", "StringList"),
    ("DateTimeList", "StringList")
))

BUSINESS_RULE_DATETIME_FORMAT = os.getenv("BUSINESS_RULE_DATETIME_FORMAT", "%Y-%m-%dT%H:%M:%S")

from . import parsers

TYPE_PARSERS = {
    "BooleanList": parsers.parse_boolean_list,
    "NumericList": parsers.parse_numeric_list,
    "DateTimeList": parsers.parse_datetime_list,
    "DictList": parsers.parse_dict_list,
    "StringList": parsers.parse_string_list,
    "Boolean": parsers.parse_boolean,
    "Numeric": parsers.parse_numeric,
    "DateTime": parsers.parse_datetime,
    "Dict": parsers.parse_dict,
    "String": parsers.parse_string,
}

# Inline test: all parsers have parser function
assert all([x in ALLOWED_TYPES for x in TYPE_PARSERS])


class BusinessRuleEngine(object):
    __instance__ = None

    def __init__(self):
        if BusinessRuleEngine.__instance__ is not None:
            raise AssertionError("this class is a singleton")
        self.__system_available_comparers = {}
        self.__system_available_filters = {}
        self.__system_available_json_reprs = {}
        self.__system_available_json_repr_bases = []

    @staticmethod
    def getInstance():
        """
        Business rule engine is globally available in application context. You can register actions, mutations and checkers.


        :return: Global business rule instance.
        :returntype: BusinessRuleEngine
        """
        if BusinessRuleEngine.__instance__ is None:
            BusinessRuleEngine.__instance__ = BusinessRuleEngine()
        return BusinessRuleEngine.__instance__

    def filter(self, pretty_name, description, key=None, manipulation_types=[], params=[], _builtin=False):
        """
        Adds filter to BusinessRuleEngine. Filters are ways to manipulate data on the fly.
        :param pretty_name: Pretty name of your filter.
        :param description: Description of your filter.
        :param key: Optional key for your filter. You can override builtin filters by overriding its key.
        :param manipulation_types: List of manipulation types as input output tuple.
        :param params: List of additional params as dict. Param dicts must have pretty_name, description, type attibutes.
        :return: A decorator object.
        """

        def w(method_def):
            nonlocal pretty_name
            nonlocal description
            nonlocal key
            nonlocal manipulation_types
            nonlocal params
            nonlocal _builtin
            assert type(manipulation_types) == list and all([type(a) == str and type(b) == str for a, b in
                                                             manipulation_types]) and len(manipulation_types) > 0 \
                , "manipulation_types must be list of tuples. Tuples must have two type names as string. There must be at least 1 manipulation types."
            type_inputs = [x for x, y in manipulation_types]
            assert len(set(type_inputs)) == len(
                type_inputs), "Manipulation types: One input cannot be mapped multiple outputs."
            assert type(params) == list and all(
                [type(param) == dict for param in params]), "params must be list of dicts."
            assert len(signature(method_def)._parameters) == 1 + len(
                params), f"Decorated filter should accept {1 + len(params)} parameters."
            assert len(manipulation_types) > 0, "There must be at least 1 manipulation input, output tuple."
            for x1, x2 in manipulation_types:
                if x1 not in ALLOWED_TYPES:
                    raise BusinessRuleEngineApiError(f"{x1} is not a known type for manipulation_types param.")
                if x2 not in ALLOWED_TYPES:
                    raise BusinessRuleEngineApiError(f"{x2} is not a known type for manipulation_types param.")
            key = str(key if key else ("f_" if not _builtin else "") + str(method_def.__name__))
            params_current = self.__prepare_params(params)
            manipulation_types = [(str(x1), str(x2)) for x1, x2 in manipulation_types]
            manipulation_types.sort(key=(lambda inp: 99999 if inp[0].startswith("String") else 0))
            self.__system_available_filters[key] = {
                "method": method_def,
                "manipulation_types": manipulation_types,
                "pretty_name": str(pretty_name),
                "description": str(description),
                "params": params_current,
                "builtin_method": _builtin
            }
            return method_def

        return w

    def comparer(self, pretty_name, description, key=None, collation_types=[], params=[],
                 value_classes=["Constant", "Attribute"], _builtin=False):
        """
        Adds comparer to BusinessRuleEngine. Comparers can be used to compare attributes and constants. First parameter of comparer must be attribute.
        Comparers does not check types in order not to get performance penalties. Type check is on your own control.
        :param pretty_name: Pretty name of your method.
        :param description: Description of your method.
        :param key: Optional key for your comparer. You can override builtin comparers by overriding key.
        :param collation_types: List of available types tuple. If empty no type check will be applied.
        :param params: List of additional params as dict. Param dicts must have pretty_name, description, type attibutes, and allow_constant, allow_attribute attributes are optional.
        :param value_classes: List of acceptable value classes for right side of function. For default "Constant" and "Attribute" is accepted.
        :return: A decorator object.
        """

        def w(method_def):
            nonlocal value_classes
            nonlocal params
            nonlocal collation_types
            nonlocal key
            nonlocal description
            nonlocal pretty_name
            nonlocal _builtin
            assert type(collation_types) == list and all(
                [type(a) == str and type(b) == str for a, b in collation_types]) and len(collation_types) > 0 \
                , "collation types must be list of tuples. Tuples must have two type names as string. There must be at least 1 collation type tuple."
            assert type(params) == list and all(
                [type(param) == dict for param in params]), "params must be list of dicts."
            assert len(signature(method_def)._parameters) == 2 + len(
                params), f"Decorated comparer should accept {2 + len(params)} parameters."
            assert type(value_classes) == list and len(value_classes) > 0 and all([type(x) == str for x in
                                                                                   value_classes]), "Value classes must be List of strings and there must be at least 1 value class"
            for x1, x2 in collation_types:
                if x1 not in ALLOWED_TYPES:
                    raise BusinessRuleEngineApiError(f"{x1} is not a known type for collation_types param.")
                if x2 not in ALLOWED_TYPES:
                    raise BusinessRuleEngineApiError(f"{x2} is not a known type for collation_types param.")
            if len(set([f"{x1}-{x2}" for x1, x2 in collation_types])) != len(collation_types):
                raise BusinessRuleEngineApiError("There are type duplications in collation_types.")
            key = str(key if key else ("c_" if not _builtin else "") + str(method_def.__name__))
            params_current = self.__prepare_params(params)

            self.__system_available_comparers[key] = {
                "method": method_def,
                "collation_types": [(str(x1), str(x2)) for x1, x2 in collation_types],
                "pretty_name": str(pretty_name),
                "description": str(description),
                "params": params_current,
                "value_classes": value_classes,
                "builtin_method": _builtin
            }
            return method_def

        return w

    def _register_base(self, current_base):
        if isclass(current_base):
            self.__system_available_json_repr_bases.append(current_base)
        else:
            raise TypeError("Parameter must be a type.")
        return current_base

    def register_for_json(self, current_class):
        if any([issubclass(current_class, x) for x in self.__system_available_json_repr_bases]):
            self.__system_available_json_reprs[current_class._key] = current_class
        return current_class

    def __prepare_params(self, params):
        params_current = []
        for param in params:
            p_pretty_name = param.get("pretty_name", None)
            p_type = param.get("type", None)
            p_description = param.get("description", None)
            p_value_classes = param.get("value_classes", [])
            p_options = param.get("meta_options", None)
            if p_pretty_name is None:
                raise BusinessRuleEngineApiError("All params should have pretty_name attribute.")
            if p_type is None:
                raise BusinessRuleEngineApiError("All params should have type attribute.")
            if p_description is None:
                raise BusinessRuleEngineApiError("All params should have description attribute.")
            if p_type not in ALLOWED_TYPES:
                raise BusinessRuleEngineApiError(f"{p_type} is not a known data type for argument.")
            if type(p_value_classes) != list:
                raise BusinessRuleEngineApiError(f"All params should have list of parameter value classes, ")
            if len(p_value_classes) == 0:
                raise BusinessRuleEngineApiError("value_classes should have at least one item.")
            try:
                json.dumps(p_options)
            except:
                raise BusinessRuleEngineApiError("Parameter meta_options must be json parsable.")
            p_value_classes = [str(x) for x in p_value_classes]
            # for value_type in p_value_types:
            #    if value_type not in self.__system_available_json_reprs:
            #        raise BusinessRuleEngineApiError(f"{value_type} is not a known value type.")

            params_current.append({
                "pretty_name": str(p_pretty_name),
                "type": str(p_type),
                "description": str(p_description),
                "value_classes": p_value_classes,
                "meta_options": p_options
            })
        return params_current

    def get_comparers(self):
        """
        Get all comparers as list.
        :return: Dict of comparers.
        """
        return self.__system_available_comparers

    def get_filters(self):
        """
        Get all filters as list.
        :return: Dict of filters
        """
        return self.__system_available_filters

    def get_json_reprs(self):
        """
        Get all json representations.
        :return: Dict of representations.
        """
        return self.__system_available_json_reprs


class DotNotation(object):
    __dot_notation_regex_dot__ = re.compile(r"(?<!\\)\.")
    __dot_notation_regex_index_specifier__ = re.compile(r"(?<!\\)\[[-,:\d\s]*(?<!\\)\]\s*$")
    __dot_notation_regex_index_specifier_set__ = re.compile(r"(?<!\\)\[[-:\d\s]*(?<!\\)\]\s*$")
    __dot_notation_regex_index_1__ = re.compile(r"^(-{0,1}\d+)$")
    __dot_notation_regex_index_2__ = re.compile(r"^(-{0,1}\d+)?\s*:\s*(-{0,1}\d+)?$")
    __dot_notation_regex_index_3__ = re.compile(r"^(-{0,1}\d+)?\s*:\s*(-{0,1}\d+)?\s*:\s*(-{0,1}\d+)?$")

    @classmethod
    def __get_dot_notation_recursive(cls, attribute, specifier: list):
        if len(specifier) == 0:
            return attribute
        matches_index_notation = cls.__dot_notation_regex_index_specifier__.finditer(specifier[0])
        last_match = None
        for m in matches_index_notation:
            last_match = m
        if last_match:
            sub_key = specifier[0][:last_match.span()[0]]
            if len(sub_key.strip()) > 0:
                if isinstance(attribute, dict):
                    attribute = attribute.get(sub_key, None)
                    match_str = last_match.group(0).strip()[1:-1]
                    subscription = list(map(lambda x: x.strip(), match_str.split(",")))
                    return cls.__get_dot_notation_recursive(
                        cls.__flatten(cls.__get_subscription_notation_recursive(attribute, subscription)),
                        specifier[1:])
                elif isinstance(attribute, list):
                    all_attributes = []
                    for attr in attribute:
                        attr = attr.get(sub_key, None)
                        match_str = last_match.group(0).strip()[1:-1]
                        subscription = list(map(lambda x: x.strip(), match_str.split(",")))
                        all_attributes.append(
                            cls.__flatten(cls.__get_subscription_notation_recursive(attr, subscription)))
                    return cls.__get_dot_notation_recursive(
                        cls.__flatten(all_attributes),
                        specifier[1:])
                else:
                    raise DotNotationError(f"You cannot access dot attribute of type {type(attribute)}")
            match_str = last_match.group(0).strip()[1:-1]
            subscription = list(map(lambda x: x.strip(), match_str.split(",")))
            return cls.__get_dot_notation_recursive(
                cls.__flatten(cls.__get_subscription_notation_recursive(attribute, subscription)),
                specifier[1:])
        elif isinstance(attribute, dict):
            return cls.__get_dot_notation_recursive(attribute.get(specifier[0]), specifier[1:])
        elif isinstance(attribute, list):
            return list(map(lambda x: cls.__get_dot_notation_recursive(x.get(specifier[0]), specifier[1:]), attribute))
        else:
            raise DotNotationError(f"You cannot access {specifier[0]} attribute of type {type(attribute)}")

    @classmethod
    def __get_subscription_notation_recursive(cls, attribute, subscription: list):
        if len(subscription) == 0:
            return attribute
        if not isinstance(attribute, list):
            raise SubscriptionError(f"Current depth type: {type(attribute)} is not subscriptable")
        cur_subs = subscription[0]
        sub_match_1 = cls.__dot_notation_regex_index_1__.match(cur_subs)
        if sub_match_1:
            index_1 = sub_match_1.group(1)
            return [cls.__get_subscription_notation_recursive(
                attribute[int(index_1)],
                subscription[1:]
            )]
        sub_match_2 = cls.__dot_notation_regex_index_2__.match(cur_subs)
        if sub_match_2:
            index_1 = sub_match_2.group(1)
            index_2 = sub_match_2.group(2)
            result_list = []
            result_list.append(cls.__get_subscription_notation_recursive(
                attribute[
                (int(index_1) if index_1 else None):
                (int(index_2) if index_2 else None)
                ], subscription[1:]
            ))
            return result_list
        sub_match_3 = cls.__dot_notation_regex_index_3__.match(cur_subs)
        if sub_match_3:
            index_1 = sub_match_3.group(1)
            index_2 = sub_match_3.group(2)
            index_3 = sub_match_3.group(3)
            result_list = []
            result_list.append(cls.__get_subscription_notation_recursive(
                attribute[
                (int(index_1) if index_1 else None):
                (int(index_2) if index_2 else None):
                (int(index_3) if index_3 else None)
                ], subscription[1:]
            ))
            return result_list
        raise SubscriptionError(f"Syntax error on statement {cur_subs}")

    @classmethod
    def __flatten(cls, obj, **kwargs):
        try:
            flatten_memory = kwargs.pop("flatten_memory")
        except KeyError:
            flatten_memory = []
        if isinstance(obj, list):
            for o in obj:
                cls.__flatten(o, flatten_memory=flatten_memory)
        else:
            flatten_memory.append(obj)
        return flatten_memory

    @classmethod
    def get_dot_notation(cls, obj, dot_specifier: str):
        """
        Access json serializable object elements with dot notation. To get value as constant append .$val at the end of your dot_specifier.
        :param obj: Any json serializable object.
        :param dot_specifier: Access specification written in dot notation. You can use list index such as  [3], [3,4], [3,4,1]
        :return: Result object
        """
        obj = json.dumps(obj)
        obj = json.loads(obj)
        dot_specifier = str(dot_specifier)
        assert len(dot_specifier) > 0, "dot_specifier cannot be empty"
        # split to keys
        keys = list(map(lambda x: x.replace("\\.", "."), cls.__dot_notation_regex_dot__.split(dot_specifier)))
        # Value parsing
        value_parse = False
        if keys[-1] == "$val":
            keys = keys[:-1]
            value_parse = True
        assert len(keys) >= 1, "Empty specifier."
        result = cls.__flatten(cls.__get_dot_notation_recursive(obj, keys))
        if value_parse:
            assert len(result) == 1, "In order to parse value to constant, stream should return single element."
            result = result[0]
        return result

    @classmethod
    def set_dot_notation(cls, obj, dot_specifier: str, value):
        """
        Set json serializable object elements with dot notation to a value.
        :param obj: Any json serializable object.
        :param dot_specifier: Access specification written in dot notation. This method is not supporting multi dimensional list subscription yet.
        :param value: Value to be set.
        :return: Result object
        """
        obj_dc = json.loads(json.dumps(obj))
        dot_specifier = str(dot_specifier)
        keys = list(map(lambda x: x.replace("\\.", "."), cls.__dot_notation_regex_dot__.split(dot_specifier)))
        cls.__set_dot_notation_recursive(obj_dc, keys, value)
        return obj_dc

    @classmethod
    def __set_dot_notation_recursive(cls, attribute, specifier: list, value):
        matches_index_notation = cls.__dot_notation_regex_index_specifier_set__.finditer(specifier[0])
        last_match = None
        for m in matches_index_notation:
            last_match = m
        if last_match:
            sub_key = specifier[0][:last_match.span()[0]]
            print(sub_key)
            if len(sub_key.strip()) > 0:
                attribute = attribute.get(sub_key, None)

            match_str = last_match.group(0).strip()[1:-1]
            cls.__set_subscription_notation(attribute, specifier, match_str, value)

        elif isinstance(attribute, dict):
            if len(specifier) == 1:
                attribute[specifier[0]] = json.loads(json.dumps(value))
                return
            cls.__set_dot_notation_recursive(attribute.get(specifier[0]), specifier[1:], value)
        elif isinstance(attribute, list):
            for x in attribute:
                cls.__set_dot_notation_recursive(x, specifier, value)
        else:
            raise DotNotationError(f"You cannot set {specifier[0]} attribute of type {type(attribute)}")

    @classmethod
    def __set_subscription_notation(cls, attribute, specifier, subscription, value):
        if not isinstance(attribute, list):
            raise SubscriptionError(f"Current depth type: {type(attribute)} is not subscriptable")
        cur_subs = subscription.strip()
        sub_match_1 = cls.__dot_notation_regex_index_1__.match(cur_subs)
        if sub_match_1:
            index_1 = sub_match_1.group(1)
            if len(specifier) > 1:
                cls.__set_dot_notation_recursive(attribute[int(index_1)], specifier[1:], value)
                return
            attribute[int(index_1)] = json.loads(json.dumps(value))
            return
        sub_match_2 = cls.__dot_notation_regex_index_2__.match(cur_subs)
        if sub_match_2:
            index_1 = sub_match_2.group(1)
            index_2 = sub_match_2.group(2)
            if len(specifier) > 1:
                for attr in attribute[
                            (int(index_1) if index_1 else None):
                            (int(index_2) if index_2 else None)
                            ]:
                    cls.__set_dot_notation_recursive(attr, specifier[1:], value)
                return
            if isinstance(value, list):
                attribute[
                (int(index_1) if index_1 else None):
                (int(index_2) if index_2 else None)
                ] = value
                return
            attribute[
            (int(index_1) if index_1 else None):
            (int(index_2) if index_2 else None)
            ] = [json.loads(json.dumps(value))] * len(attribute[
                                                      (int(index_1) if index_1 else None):
                                                      (int(index_2) if index_2 else None)
                                                      ])
            return
        sub_match_3 = cls.__dot_notation_regex_index_3__.match(cur_subs)
        if sub_match_3:
            index_1 = sub_match_3.group(1)
            index_2 = sub_match_3.group(2)
            index_3 = sub_match_3.group(3)
            if len(specifier) > 1:
                for attr in attribute[
                            (int(index_1) if index_1 else None):
                            (int(index_2) if index_2 else None):
                            (int(index_3) if index_3 else None)
                            ]:
                    cls.__set_dot_notation_recursive(attr, specifier[1:], value)
                return
            if isinstance(value, list):
                attribute[
                (int(index_1) if index_1 else None):
                (int(index_2) if index_2 else None):
                (int(index_3) if index_3 else None)
                ] = value
                return
            attribute[
            (int(index_1) if index_1 else None):
            (int(index_2) if index_2 else None):
            (int(index_3) if index_3 else None)
            ] = [json.loads(json.dumps(value))] * len(attribute[
                                                      (int(index_1) if index_1 else None):
                                                      (int(index_2) if index_2 else None):
                                                      (int(index_3) if index_3 else None)
                                                      ])
            return
        raise SubscriptionError(f"Syntax error on statement {cur_subs}")

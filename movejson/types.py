import abc
import copy
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum, unique

from .exceptions import RuleCreationError, ParseError, BusinessRuleEngineApiError, RunnerError
from .ruleengine import BusinessRuleEngine, DotNotation, ALLOWED_TYPES, TYPE_PARSERS, \
    ALLOWED_IMPLICIT_CONVERSIONS

bre_instance = BusinessRuleEngine.getInstance()


@bre_instance._register_base
class BaseValue(metaclass=abc.ABCMeta):
    _base_type = "BaseValue"

    @abc.abstractmethod
    def set_input(self, value) -> "BaseValue":
        """
        Sets stored input to the parameter.

        :param value: Value to be set.
        :returns: Self
        """
        pass

    @abc.abstractmethod
    def get_value(self, row: dict) -> object:
        """
        Gets stored value. All filtering operations applied to result object.

        :param row: Extracted value.
        :return: Value object.
        """
        pass

    @abc.abstractmethod
    def add_filter(self, filter_name: str, *args) -> "BaseValue":
        """
        Add filter to the value. Filters are the way of morphing data.

        :param filter_name: Name of filter.
        :param args: Additional arguments for filter.
        :returns: Self
        """
        pass

    @abc.abstractmethod
    def clear_filters(self) -> "BaseValue":
        """
        Clears all filters.

        :returns: Self
        """
        pass

    @abc.abstractmethod
    def get_filters(self):
        """
        Get all filters.

        :return: List of filters.
        """

    @abc.abstractmethod
    def fetch_addable_filters(self) -> list:
        """
        Fetches convenient filters for current value.

        :return: List of strings of filter names.
        """
        pass

    @abc.abstractmethod
    def set_input_type(self, type_name: str) -> "BaseValue":
        """
        Used for setting type of the input value. Types are not statically checked.

        :param type_name: Type name.
        :returns: Self
        """
        pass

    @abc.abstractmethod
    def get_type(self) -> str:
        """
        Get type of value.

        :return: Type name.
        """
        pass


@bre_instance._register_base
class BaseContainer(metaclass=abc.ABCMeta):
    _base_type = "BaseContainer"

    @abc.abstractmethod
    def evaluate(self, row: dict) -> bool:
        """
        Evaluates the container on given row.

        :param row: Row which Operator
        :return: Evaluation result.
        """
        pass

    @abc.abstractmethod
    def add_comparer(self, comparer_name: str, comparable1: BaseValue, comparable2: BaseValue, *args):
        """
        Adds comparer to container.

        :param comparer_name: Name of the container.
        :param comparable1: First comparable value.
        :param comparable2: Second comparable value.
        :param args: Additional arguments for camparer.
        """
        pass

    @abc.abstractmethod
    def add_sub_container(self, operator: "BaseContainer"):
        """
        Adds a sub container.

        :param operator: Sub container instance.
        """
        pass

    @abc.abstractmethod
    def get_all_objects(self) -> list:
        """
        Get all objects as a list. This function returns all containers and comparers.

        :return: List of containers and comparers.
        """
        pass

    @abc.abstractmethod
    def clear_objects(self):
        """
        Clears all of containers and comparers.
        """
        pass

    @property
    @abc.abstractmethod
    def not_operator(self):
        pass


@bre_instance._register_base
class DictSerializable(metaclass=abc.ABCMeta):
    _base_type = "DictSerializable"

    @property
    @abc.abstractmethod
    def _key(self):
        pass

    @classmethod
    @abc.abstractmethod
    def from_dict(cls, dict_obj) -> "DictSerializable":
        """
        Creates container object from dictionary.

        :param dict_obj: Input dictionary obj
        :return: Container object.
        """
        pass

    @abc.abstractmethod
    def to_dict(self) -> dict:
        """
        Returns dictionary representation of the container.

        :return: Result dictionary object.
        """
        pass

    @abc.abstractmethod
    def validate_with_environment(self, environment: "Environment") -> bool:
        """
        Validates with Environment object.

        :param environment: Environment object which will be validated on.
        :return: Boolean object.
        """


class TypesHelper:
    @staticmethod
    def extract_allowed_types(type_name: str):
        reslist = [type_name] if type_name in ALLOWED_TYPES else []
        reslist += [x for x, y in ALLOWED_IMPLICIT_CONVERSIONS if y == type_name]
        return reslist

    @staticmethod
    def implicit_parse(value: object, type_name: str):
        outp_type = type_name
        return TYPE_PARSERS[type_name](value)

    @classmethod
    def value_to_json_compatible(cls, value):
        if type(value) == list:
            return [cls._value_to_json_compatible_single(x) for x in value]
        return cls._value_to_json_compatible_single(value)

    @classmethod
    def _value_to_json_compatible_single(cls, value: datetime):
        if type(value) == datetime:
            return value.replace(tzinfo=timezone.utc).timestamp()
        return value

    @classmethod
    def from_dict_facade(cls, dict_obj):
        dict_obj_mappings = bre_instance.get_json_reprs()
        if dict_obj["key"] not in dict_obj_mappings:
            raise RuleCreationError(detail=[f"{dict_obj['key']} is not a known type for deserializing."])
        return dict_obj_mappings[dict_obj["key"]].from_dict(dict_obj)


@bre_instance.register_for_json
class Constant(BaseValue, DictSerializable):
    """
    Class for constant values.
    """

    def validate_with_environment(self, environment: "Environment") -> bool:
        for filter_obj in self._filters:
            for arg_obj in filter_obj["args"]:
                if not arg_obj.validate_with_environment(environment):
                    return False
        else:
            return True

    def get_filters(self):
        return self._filters

    def clear_filters(self):
        self._filters = []
        return self

    def _try_extract_type(self, value):
        for k in TYPE_PARSERS:
            try:
                return TYPE_PARSERS[k](value), k
            except ParseError as e:
                continue
        raise RuleCreationError(detail=["Constant cannot be parsed to a type."])

    def set_input(self, value, try_parse=False):
        if len(self._filters) > 0:
            raise RuleCreationError(
                detail=["Constant has filters, you cannot set input explicitly after setting up filters."])
        if self._type is None or try_parse:
            parsed_value, extracted_type = self._try_extract_type(value)
            self._type = extracted_type
            self._base_input = parsed_value
            self._base_input_raw = value
        else:
            try:
                self._base_input = TYPE_PARSERS[self._type](value)
                self._base_input_raw = value
            except ParseError as e:
                raise RuleCreationError(detail=[f"Constant cannot be parsed as {self._type}"])
        return self

    def get_value(self, row: dict) -> object:
        current_value = self._base_input
        current_type = self._type
        for filter in self._filters:
            acceptable_types = [x for x, y in filter["filter"]["manipulation_types"]]
            if current_type in acceptable_types:
                # directly acceptable
                current_value = filter["filter"]["method"](current_value,
                                                           *list([x.get_value(row) for x in filter["args"]]))
                current_type = list([y for x, y in filter["filter"]["manipulation_types"] if x == current_type])[0]
            else:
                # needs implicit conversion.
                _found = False
                for type_name, outp_type in filter["filter"]["manipulation_types"]:
                    if current_type in TypesHelper.extract_allowed_types(type_name):
                        _found = True
                        current_value = filter["filter"]["method"](TYPE_PARSERS[type_name](current_value),
                                                                   *list([x.get_value(row) for x in filter["args"]]))
                        current_type = outp_type
                        break
                if not _found:
                    raise RunnerError("There is no convenient propogation.")

        return current_value

    def add_filter(self, filter_name: str, *args):
        avail_filters = self.fetch_addable_filters()
        if filter_name not in avail_filters:
            raise RuleCreationError(detail=[f"{filter_name} cannot be found in addable filters."])
        all_filters = bre_instance.get_filters()
        cur_filter = all_filters[filter_name]
        if len(cur_filter["params"]) != len(args):
            raise RuleCreationError(detail=[
                f"Extra arguments are not convenient for filter signature. You must provide {len(cur_filter['params'])} extra parameters for filter."])
        _det = []
        for i, arg in enumerate(args):
            if not isinstance(arg, BaseValue):
                _det.append(f"Argument index {i}: is not BaseValue type.")
                continue
            if arg._key not in cur_filter["params"][i]["value_classes"]:
                _det.append(
                    f"Argument index {i}: cannot be accepted for current parameter. {', '.join(cur_filter['params'][i]['value_classes'])} values are acceptable.")
                continue
            if arg.get_type() not in TypesHelper.extract_allowed_types(cur_filter["params"][i]["type"]):
                _det.append(
                    f"Argument index {i}: with type {arg.get_type()} is not acceptable by parameter. {', '.join(TypesHelper.extract_allowed_types(cur_filter['params'][i]['type']))} types are allowed.")

        if len(_det) > 0:
            raise RuleCreationError(detail=_det)
        self._filters.append(dict(key=filter_name, filter=cur_filter, args=args))
        return self

    @classmethod
    def from_dict(cls, dict_obj) -> "BaseValue":
        assert dict_obj["key"] == cls._key, "Keys are inconsistent. Are you trying to deserialize different type?"
        result_obj = Constant(dict_obj["obj"]["value"], dict_obj["obj"]["type"])
        for filt in dict_obj["obj"]["filters"]:
            result_obj.add_filter(filt["filter_key"], *list([TypesHelper.from_dict_facade(x) for x in filt["args"]]))
        return result_obj

    def to_dict(self) -> dict:
        result_dict = {"value": TypesHelper.value_to_json_compatible(self._base_input), "type": self._type}
        filters = []
        for filt in self._filters:
            cur_obj = {"filter_key": filt["key"]}
            args = []
            for arg in filt["args"]:
                args.append(arg.to_dict())
            cur_obj["args"] = args
            filters.append(cur_obj)
        result_dict["filters"] = filters
        return {"key": self.__class__._key, "obj": result_dict}

    def fetch_addable_filters(self) -> list:
        all_filters = bre_instance.get_filters()
        cur_type = self.get_type()
        available_filters = []
        for filt in all_filters:
            available_inputs = list()
            for sub_avail_list in [TypesHelper.extract_allowed_types(x) for x, y in
                                   all_filters[filt]["manipulation_types"]]:
                available_inputs += sub_avail_list
            available_inputs = set(available_inputs)
            if cur_type in available_inputs:
                available_filters.append(filt)

        return available_filters

    def set_input_type(self, type_name: str):
        if len(self._filters) > 0:
            raise RuleCreationError(
                detail=["Constant has filters, you cannot set input type explicitly after setting up filters."])
        if type_name not in ALLOWED_TYPES:
            raise RuleCreationError(detail=[f"{type_name} is not a known type."])
        try:
            self._base_input = TYPE_PARSERS[type_name](self._base_input_raw)
            self._type = type_name
        except ParseError as e:
            raise RuleCreationError(detail=[str(e)])
        return self

    def get_type(self) -> str:
        if len(self._filters) == 0:
            return self._type
        else:
            cur_type = self._type
            for filter in self._filters:
                _found = False
                for inp, outp in filter["filter"]["manipulation_types"]:
                    if cur_type in TypesHelper.extract_allowed_types(inp):
                        _found = True
                        cur_type = outp
                        break
                if not _found:
                    raise BusinessRuleEngineApiError(
                        "There is an error while getting type. There cannot be type propogation.")
            return cur_type

    _key = "Constant"

    def __init__(self, value, value_type: str = None):
        if value_type is not None:
            if value_type not in ALLOWED_TYPES:
                raise RuleCreationError(detail=[f"Type: {value_type} is not allowed."])
            self._type = value_type
        else:
            self._type = None
        self._base_input = None
        self._base_input_raw = None
        self._filters = []
        self.set_input(value)


@bre_instance.register_for_json
class Attribute(BaseValue, DictSerializable):
    """
    Class for attribute values.
    """

    def validate_with_environment(self, environment: "Environment") -> bool:
        if len(environment.query(dot_specifier=self._base_input, attribute_type=JsonAttributeType.INPUT)) == 0:
            return False
        for filter_obj in self._filters:
            for arg_obj in filter_obj["args"]:
                if not arg_obj.validate_with_environment(environment):
                    return False

        return True

    def get_filters(self):
        return self._filters

    def clear_filters(self):
        self._filters = []
        return self

    def set_input(self, value_dot_notation):
        if len(self._filters) > 0:
            raise RuleCreationError(
                detail=["Attribute has filters, you cannot set input explicitly after setting up filters."])

        self._base_input = value_dot_notation
        return self

    def get_value(self, row: dict) -> object:
        current_value = TYPE_PARSERS[self._type](DotNotation.get_dot_notation(row, self._base_input))
        current_type = self._type
        for filter in self._filters:
            acceptable_types = [x for x, y in filter["filter"]["manipulation_types"]]
            if current_type in acceptable_types:
                # directly acceptable
                current_value = filter["filter"]["method"](current_value,
                                                           *list([x.get_value(row) for x in filter["args"]]))
                current_type = list([y for x, y in filter["filter"]["manipulation_types"] if x == current_type])[0]
            else:
                # needs implicit conversion.
                _found = False
                for type_name, outp_type in filter["filter"]["manipulation_types"]:
                    if current_type in TypesHelper.extract_allowed_types(type_name):
                        _found = True
                        current_value = filter["filter"]["method"](TYPE_PARSERS[type_name](current_value),
                                                                   *list([x.get_value(row) for x in filter["args"]]))
                        current_type = outp_type
                        break
                if not _found:
                    raise RunnerError("There is no convenient propogation.")

        return current_value

    def add_filter(self, filter_name: str, *args):
        avail_filters = self.fetch_addable_filters()
        if filter_name not in avail_filters:
            raise RuleCreationError(detail=[f"{filter_name} cannot be found in addable filters."])
        all_filters = bre_instance.get_filters()
        cur_filter = all_filters[filter_name]
        if len(cur_filter["params"]) != len(args):
            raise RuleCreationError(detail=[
                f"Extra arguments are not convenient for filter signature. You must provide {len(cur_filter['params'])} extra parameters for filter."])
        _det = []
        for i, arg in enumerate(args):
            if not isinstance(arg, BaseValue):
                _det.append(f"Argument index {i}: is not BaseValue type.")
                continue
            if arg._key not in cur_filter["params"][i]["value_classes"]:
                _det.append(
                    f"Argument index {i}: cannot be accepted for current parameter. {', '.join(cur_filter['params'][i]['value_classes'])} values are acceptable.")
                continue
            if arg.get_type() not in TypesHelper.extract_allowed_types(cur_filter["params"][i]["type"]):
                _det.append(
                    f"Argument index {i}: with type {arg.get_type()} is not acceptable by parameter. {', '.join(TypesHelper.extract_allowed_types(cur_filter['params'][i]['type']))} types are allowed.")

        if len(_det) > 0:
            raise RuleCreationError(detail=_det)
        self._filters.append(dict(key=filter_name, filter=cur_filter, args=args))
        return self

    @classmethod
    def from_dict(cls, dict_obj) -> "BaseValue":
        assert dict_obj["key"] == cls._key, "Keys are inconsistent. Are you trying to deserialize different type?"
        result_obj = Attribute(dict_obj["obj"]["value"], dict_obj["obj"]["type"])
        for filt in dict_obj["obj"]["filters"]:
            result_obj.add_filter(filt["filter_key"], *list([TypesHelper.from_dict_facade(x) for x in filt["args"]]))
        return result_obj

    def to_dict(self) -> dict:
        result_dict = {"value": TypesHelper.value_to_json_compatible(self._base_input), "type": self._type}
        filters = []
        for filt in self._filters:
            cur_obj = {"filter_key": filt["key"]}
            args = []
            for arg in filt["args"]:
                args.append(arg.to_dict())
            cur_obj["args"] = args
            filters.append(cur_obj)
        result_dict["filters"] = filters
        return {"key": self.__class__._key, "obj": result_dict}

    def fetch_addable_filters(self) -> list:
        all_filters = bre_instance.get_filters()
        cur_type = self.get_type()
        available_filters = []
        for filt in all_filters:
            available_inputs = list()
            for sub_avail_list in [TypesHelper.extract_allowed_types(x) for x, y in
                                   all_filters[filt]["manipulation_types"]]:
                available_inputs += sub_avail_list
            available_inputs = set(available_inputs)
            if cur_type in available_inputs:
                available_filters.append(filt)

        return available_filters

    def set_input_type(self, type_name: str):
        if len(self._filters) > 0:
            raise RuleCreationError(
                detail=["Attribute has filters, you cannot set input type explicitly after setting up filters."])
        if type_name not in ALLOWED_TYPES:
            raise RuleCreationError(detail=[f"{type_name} is not a known type."])
        self._type = type_name
        return self

    def get_type(self) -> str:
        if len(self._filters) == 0:
            return self._type
        else:
            cur_type = self._type
            for filter in self._filters:
                _found = False
                for inp, outp in filter["filter"]["manipulation_types"]:
                    if cur_type in TypesHelper.extract_allowed_types(inp):
                        _found = True
                        cur_type = outp
                        break
                if not _found:
                    raise BusinessRuleEngineApiError(
                        "There is an error while getting type. There cannot be type propogation.")
            return cur_type

    _key = "Attribute"

    def __init__(self, value_dot_notation: str, value_type: str):

        if value_type not in ALLOWED_TYPES:
            raise RuleCreationError(detail=[f"Type: {value_type} is not allowed."])
        self._type = value_type
        self._base_input = None
        self._filters = []
        self.set_input(value_dot_notation)


@bre_instance.register_for_json
class AndOperatorContainer(BaseContainer, DictSerializable):
    def validate_with_environment(self, environment: "Environment") -> bool:
        for compare_object in self._compare_objects:
            if isinstance(compare_object, BaseContainer):
                if not compare_object.validate_with_environment(environment):
                    return False
            else:
                if not compare_object["comparable1"].validate_with_environment(environment):
                    return False
                if not compare_object["comparable2"].validate_with_environment(environment):
                    return False
                for arg_obj in compare_object["args"]:
                    if not arg_obj.validate_with_environment(environment):
                        return False
        return True

    _key = "AndOperator"
    _not_operator = False

    @property
    def not_operator(self):
        return self._not_operator

    @not_operator.setter
    def not_operator(self, value):
        if not isinstance(value, bool):
            raise TypeError("Not operator must be bool type.")
        self._not_operator = value

    def __init__(self):
        self._compare_objects = []

    def _evaluate_comparable_obj(self, compare_obj, row: dict):
        comparer = compare_obj["comparer"]
        comparable1 = compare_obj["comparable1"]
        comparable2 = compare_obj["comparable2"]
        selected_collation = compare_obj["selected_collation"]
        args = compare_obj["args"]
        value1 = comparable1.get_value(row)
        value1 = TypesHelper.implicit_parse(value1, selected_collation[0])
        value2 = comparable2.get_value(row)
        value2 = TypesHelper.implicit_parse(value2, selected_collation[1])
        arg_values = []
        for i, arg in enumerate(args):
            current_target_type = comparer["params"][i]["type"]
            cur_value = arg.get_value(row)
            if current_target_type != arg.get_type():
                cur_value = TypesHelper.implicit_parse(cur_value, current_target_type)
            arg_values.append(cur_value)
        return comparer["method"](value1, value2, *arg_values)

    def evaluate(self, row: dict) -> bool:
        result = all(
            [(x.evaluate(row) if isinstance(x, BaseContainer) else self._evaluate_comparable_obj(x, row)) for x in
             self._compare_objects])
        if self.not_operator:
            return not (result)
        return result

    def add_comparer(self, comparer_name: str, comparable1: BaseValue, comparable2: BaseValue, collation_type=None,
                     *args):
        available_comparers = bre_instance.get_comparers()
        if comparer_name not in available_comparers:
            raise RuleCreationError(detail=["Comparer name is not in available comparers."])
        cur_comparer = available_comparers[comparer_name]
        # Validation of comparables
        if comparable1.__class__._key != "Attribute":
            raise RuleCreationError(detail=["Left parameter of the comparer only accepts Attribute class."])
        if comparable2.__class__._key not in cur_comparer["value_classes"]:
            raise RuleCreationError(detail=[
                f"Right side of the comparer only accepts {', '.join(cur_comparer['value_classes'])} parameters."])
        # Extracting convenient types.
        override_collation_type = collation_type
        selected_collation = None
        cmp1_type = comparable1.get_type()
        cmp2_type = comparable2.get_type()
        if override_collation_type is not None:
            if type(override_collation_type) not in [list, tuple] or len(override_collation_type) != 2 or not \
                (type(override_collation_type[0]) == str and type(override_collation_type[1]) == str):
                raise RuleCreationError(
                    detail=["Collation type parameter must be list or tuple with two string elements"])
            selected_collation = [(x, y) for x, y in cur_comparer["collation_types"] if
                                  x == override_collation_type[0] and y == override_collation_type[1]]
            if len(selected_collation) == 0:
                raise RuleCreationError(detail=["Provided collation type is not found in comparers collation types."])
            selected_collation = selected_collation[0]
            if not (cmp1_type in TypesHelper.extract_allowed_types(
                selected_collation[0]) and cmp2_type in TypesHelper.extract_allowed_types(selected_collation[1])):
                raise RuleCreationError(detail=["Provided collation type is not convenient for types of comparables."])

        else:
            # Search for exact match
            _found = False
            for x, y in cur_comparer["collation_types"]:
                if x == cmp1_type and y == cmp2_type:
                    _found = True
                    selected_collation = (x, y)
                    break
            if not _found:
                for x, y in cur_comparer["collation_types"]:
                    if cmp1_type in TypesHelper.extract_allowed_types(
                        x) and cmp2_type in TypesHelper.extract_allowed_types(y):
                        _found = True
                        selected_collation = (x, y)
                        break
            if not _found:
                raise RuleCreationError(
                    detail=[f"Types ({cmp1_type}, {cmp2_type}) is not convenient for this comparer."])
        ###
        if len(cur_comparer["params"]) != len(args):
            raise RuleCreationError(detail=[
                f"Extra arguments are not convenient for comparer signature. You must provide {len(cur_comparer['params'])} extra parameters for comparer."])
        _det = []
        for i, arg in enumerate(args):
            if not isinstance(arg, BaseValue):
                _det.append(f"Argument index {i}: is not BaseValue type.")
                continue
            if arg._key not in cur_comparer["params"][i]["value_classes"]:
                _det.append(
                    f"Argument index {i}: cannot be accepted for current parameter. {', '.join(cur_comparer['params'][i]['value_classes'])} values are acceptable.")
                continue
            if arg.get_type() not in TypesHelper.extract_allowed_types(cur_comparer["params"][i]["type"]):
                _det.append(
                    f"Argument index {i}: with type {arg.get_type()} is not acceptable by parameter. {', '.join(TypesHelper.extract_allowed_types(cur_comparer['params'][i]['type']))} types are allowed.")

        if len(_det) > 0:
            raise RuleCreationError(detail=_det)
        self._compare_objects.append(
            dict(key=comparer_name, comparer=cur_comparer, selected_collation=selected_collation,
                 comparable1=comparable1, comparable2=comparable2, args=args))
        return self

    def add_sub_container(self, container: BaseContainer):
        if not isinstance(container, BaseContainer):
            raise RuleCreationError(detail=["add_sub_container expects BaseContainer object."])
        self._compare_objects.append(container)
        return self

    def get_all_objects(self) -> list:
        return self._compare_objects

    def clear_objects(self):
        self._compare_objects = []
        return self

    @classmethod
    def from_dict(cls, dict_obj) -> BaseContainer:
        assert dict_obj["key"] == cls._key, "Keys are inconsistent. Are you trying to deserialize different type?"
        result_obj = AndOperatorContainer()
        for sub_container in dict_obj["obj"]["sub_containers"]:
            result_obj.add_sub_container(TypesHelper.from_dict_facade(sub_container))
        for comparer in dict_obj["obj"]["comparers"]:
            args = [TypesHelper.from_dict_facade(x) for x in comparer["args"]]
            result_obj.add_comparer(comparer["comparer_key"], TypesHelper.from_dict_facade(comparer["comparable1"]),
                                    TypesHelper.from_dict_facade(comparer["comparable2"]),
                                    tuple(comparer["selected_collation"]), *args)
        result_obj.not_operator = dict_obj["obj"]["not_operator"]
        return result_obj

    def to_dict(self) -> dict:
        result_dict = {}
        sub_containers = []
        comparers = []
        for cmp in self._compare_objects:
            if isinstance(cmp, BaseContainer):
                sub_containers.append(cmp.to_dict())
            else:
                current_comparer = {"comparer_key": cmp["key"], "comparable1": cmp["comparable1"].to_dict(),
                                    "comparable2": cmp["comparable2"].to_dict(),
                                    "selected_collation": list(cmp["selected_collation"])}
                args = [arg.to_dict() for arg in cmp["args"]]
                current_comparer["args"] = args
                comparers.append(current_comparer)
        result_dict["comparers"] = comparers
        result_dict["sub_containers"] = sub_containers
        result_dict["not_operator"] = self.not_operator
        return {"key": self.__class__._key, "obj": result_dict}


@bre_instance.register_for_json
class OrOperatorContainer(BaseContainer, DictSerializable):
    def validate_with_environment(self, environment: "Environment") -> bool:
        for compare_object in self._compare_objects:
            if isinstance(compare_object, BaseContainer):
                if not compare_object.validate_with_environment(environment):
                    return False
            else:
                if not compare_object["comparable1"].validate_with_environment(environment):
                    return False
                if not compare_object["comparable2"].validate_with_environment(environment):
                    return False
                for arg_obj in compare_object["args"]:
                    if not arg_obj.validate_with_environment(environment):
                        return False
        return True

    _key = "OrOperator"
    _not_operator = False

    @property
    def not_operator(self):
        return self._not_operator

    @not_operator.setter
    def not_operator(self, value):
        if not isinstance(value, bool):
            raise TypeError("Not operator must be bool type.")
        self._not_operator = value

    def __init__(self):
        self._compare_objects = []

    def _evaluate_comparable_obj(self, compare_obj, row: dict):
        comparer = compare_obj["comparer"]
        comparable1 = compare_obj["comparable1"]
        comparable2 = compare_obj["comparable2"]
        selected_collation = compare_obj["selected_collation"]
        args = compare_obj["args"]
        value1 = comparable1.get_value(row)
        value1 = TypesHelper.implicit_parse(value1, selected_collation[0])
        value2 = comparable2.get_value(row)
        value2 = TypesHelper.implicit_parse(value2, selected_collation[1])
        arg_values = []
        for i, arg in enumerate(args):
            current_target_type = comparer["params"][i]["type"]
            cur_value = arg.get_value(row)
            if current_target_type != arg.get_type():
                cur_value = TypesHelper.implicit_parse(cur_value, current_target_type)
            arg_values.append(cur_value)
        return comparer["method"](value1, value2, *arg_values)

    def evaluate(self, row: dict) -> bool:
        result = any(
            [(x.evaluate(row) if isinstance(x, BaseContainer) else self._evaluate_comparable_obj(x, row)) for x in
             self._compare_objects])
        if self.not_operator:
            return not (result)
        return result

    def add_comparer(self, comparer_name: str, comparable1: BaseValue, comparable2: BaseValue, collation_type=None,
                     *args):
        available_comparers = bre_instance.get_comparers()
        if comparer_name not in available_comparers:
            raise RuleCreationError(detail=["Comparer name is not in available comparers."])
        cur_comparer = available_comparers[comparer_name]
        # Validation of comparables
        if comparable1.__class__._key != "Attribute":
            raise RuleCreationError(detail=["Left parameter of the comparer only accepts Attribute class."])
        if comparable2.__class__._key not in cur_comparer["value_classes"]:
            raise RuleCreationError(detail=[
                f"Right side of the comparer only accepts {', '.join(cur_comparer['value_classes'])} parameters."])
        # Extracting convenient types.
        override_collation_type = collation_type
        selected_collation = None
        cmp1_type = comparable1.get_type()
        cmp2_type = comparable2.get_type()
        if override_collation_type is not None:
            if type(override_collation_type) not in [list, tuple] or len(override_collation_type) != 2 or not \
                (type(override_collation_type[0]) == str and type(override_collation_type[1]) == str):
                raise RuleCreationError(
                    detail=["Collation type parameter must be list or tuple with two string elements"])
            selected_collation = [(x, y) for x, y in cur_comparer["collation_types"] if
                                  x == override_collation_type[0] and y == override_collation_type[1]]
            if len(selected_collation) == 0:
                raise RuleCreationError(detail=["Provided collation type is not found in comparers collation types."])
            selected_collation = selected_collation[0]
            if not (cmp1_type in TypesHelper.extract_allowed_types(
                selected_collation[0]) and cmp2_type in TypesHelper.extract_allowed_types(selected_collation[1])):
                raise RuleCreationError(detail=["Provided collation type is not convenient for types of comparables."])

        else:
            # Search for exact match
            _found = False
            for x, y in cur_comparer["collation_types"]:
                if x == cmp1_type and y == cmp2_type:
                    _found = True
                    selected_collation = (x, y)
                    break
            if not _found:
                for x, y in cur_comparer["collation_types"]:
                    if cmp1_type in TypesHelper.extract_allowed_types(
                        x) and cmp2_type in TypesHelper.extract_allowed_types(y):
                        _found = True
                        selected_collation = (x, y)
                        break
            if not _found:
                raise RuleCreationError(
                    detail=[f"Types ({cmp1_type}, {cmp2_type}) is not convenient for this comparer."])
        ###
        if len(cur_comparer["params"]) != len(args):
            raise RuleCreationError(detail=[
                f"Extra arguments are not convenient for comparer signature. You must provide {len(cur_comparer['params'])} extra parameters for comparer."])
        _det = []
        for i, arg in enumerate(args):
            if not isinstance(arg, BaseValue):
                _det.append(f"Argument index {i}: is not BaseValue type.")
                continue
            if arg._key not in cur_comparer["params"][i]["value_classes"]:
                _det.append(
                    f"Argument index {i}: cannot be accepted for current parameter. {', '.join(cur_comparer['params'][i]['value_classes'])} values are acceptable.")
                continue
            if arg.get_type() not in TypesHelper.extract_allowed_types(cur_comparer["params"][i]["type"]):
                _det.append(
                    f"Argument index {i}: with type {arg.get_type()} is not acceptable by parameter. {', '.join(TypesHelper.extract_allowed_types(cur_comparer['params'][i]['type']))} types are allowed.")

        if len(_det) > 0:
            raise RuleCreationError(detail=_det)
        self._compare_objects.append(
            dict(key=comparer_name, comparer=cur_comparer, selected_collation=selected_collation,
                 comparable1=comparable1, comparable2=comparable2, args=args))
        return self

    def add_sub_container(self, container: BaseContainer):
        if not isinstance(container, BaseContainer):
            raise RuleCreationError(detail=["add_sub_container expects BaseContainer object."])
        self._compare_objects.append(container)
        return self

    def get_all_objects(self) -> list:
        return self._compare_objects

    def clear_objects(self):
        self._compare_objects = []
        return self

    @classmethod
    def from_dict(cls, dict_obj) -> BaseContainer:
        assert dict_obj["key"] == cls._key, "Keys are inconsistent. Are you trying to deserialize different type?"
        result_obj = OrOperatorContainer()
        for sub_container in dict_obj["obj"]["sub_containers"]:
            result_obj.add_sub_container(TypesHelper.from_dict_facade(sub_container))
        for comparer in dict_obj["obj"]["comparers"]:
            args = [TypesHelper.from_dict_facade(x) for x in comparer["args"]]
            result_obj.add_comparer(comparer["comparer_key"], TypesHelper.from_dict_facade(comparer["comparable1"]),
                                    TypesHelper.from_dict_facade(comparer["comparable2"]),
                                    tuple(comparer["selected_collation"]), *args)
        result_obj.not_operator = dict_obj["obj"]["not_operator"]
        return result_obj

    def to_dict(self) -> dict:
        result_dict = {}
        sub_containers = []
        comparers = []
        for cmp in self._compare_objects:
            if isinstance(cmp, BaseContainer):
                sub_containers.append(cmp.to_dict())
            else:
                current_comparer = {"comparer_key": cmp["key"], "comparable1": cmp["comparable1"].to_dict(),
                                    "comparable2": cmp["comparable2"].to_dict(),
                                    "selected_collation": list(cmp["selected_collation"])}
                args = [arg.to_dict() for arg in cmp["args"]]
                current_comparer["args"] = args
                comparers.append(current_comparer)
        result_dict["comparers"] = comparers
        result_dict["sub_containers"] = sub_containers
        result_dict["not_operator"] = self.not_operator
        return {"key": self.__class__._key, "obj": result_dict}


@unique
class JsonAttributeType(Enum):
    INPUT = "in"
    OUTPUT = "out"


@bre_instance.register_for_json
@dataclass(frozen=True)
class JsonAttribute(DictSerializable):

    def validate_with_environment(self, environment: "Environment") -> bool:
        return True

    _key = "JsonAttribute"
    dot_specifier: str
    attribute_type: JsonAttributeType
    attribute_data_type: str
    pretty_name: str
    description: str = ""
    read_only: bool = False
    max_length: int = None

    @classmethod
    def from_dict(cls, dict_obj) -> "DictSerializable":
        assert dict_obj["key"] == cls._key, "Keys are inconsistent. Are you trying to deserialize different type?"
        return JsonAttribute(dict_obj["obj"]["dot_specifier"], JsonAttributeType(dict_obj["obj"]["attribute_type"]),
                             dict_obj["obj"]["attribute_data_type"], dict_obj["obj"]["pretty_name"],
                             dict_obj["obj"]["description"], dict_obj["obj"]["read_only"],
                             dict_obj["obj"]["max_length"])

    def to_dict(self) -> dict:
        type_value = self.attribute_type.value
        result_obj = copy.deepcopy(self.__dict__)
        result_obj.update({"attribute_type": type_value})
        return dict(key=self.__class__._key, obj=result_obj)


@bre_instance.register_for_json
class Environment(DictSerializable):
    def validate_with_environment(self, environment: "Environment") -> bool:
        return True

    _key = "Environment"

    def query(self, dot_specifier: str = None, attribute_type: JsonAttributeType = None,
              attribute_data_type: str = None, pretty_name: str = None, description: str = None,
              read_only: bool = None, ):
        """
        Queries all attributes based attribute features.

        :param dot_specifier:
        :param attribute_type:
        :param attribute_data_type
        :param pretty_name:
        :param description:
        :param read_only:
        :return: List of attributes.
        """
        result_set = []
        for attr in self._attributes:
            if (dot_specifier == attr.dot_specifier or dot_specifier is None) and (
                attribute_type == attr.attribute_type or attribute_type is None) \
                and (pretty_name == attr.pretty_name or pretty_name is None) and (
                description == attr.description or description is None) and \
                (attribute_data_type == attr.attribute_data_type or attribute_data_type is None) and \
                (read_only == attr.read_only or read_only is None):
                result_set.append(attr)
        return result_set

    @classmethod
    def from_dict(cls, dict_obj) -> "DictSerializable":
        assert dict_obj["key"] == cls._key, "Keys are inconsistent. Are you trying to deserialize different type?"
        result_obj = Environment()
        for attribute_dict in dict_obj["obj"]["attributes"]:
            result_obj.add_attribute(TypesHelper.from_dict_facade(attribute_dict))
        for input_index, output_index in dict_obj["obj"]["default_mappings"]:
            result_obj.add_default_mapping_with_index(input_index, output_index)
        return result_obj

    def to_dict(self) -> dict:
        result_dict = {"default_mappings": [[x, y] for x, y in self._default_mappings],
                       "attributes": [x.to_dict() for x in self._attributes]}
        return {"key": self.__class__._key, "obj": result_dict}

    def __init__(self):
        self._attributes = list()
        self._default_mappings = list()

    def add_attribute(self, attr: JsonAttribute):
        """
        Adds an allowed Json attribute
        :param attr: JsonAttribute object
        :return: Self
        """
        assert isinstance(attr, JsonAttribute), "attr must be JsonAttribute type."
        if attr not in self._attributes:
            self._attributes.append(attr)
        return self

    def get_all_attributes(self) -> list:
        """
        Get all attributes.

        :return: Attribute list.
        """
        return self._attributes

    def get_all_default_mappings(self):
        """
        Get all mappings.

        :return: Mappings list
        """
        return [(self._attributes[x], self._attributes[y]) for x, y in self._default_mappings]

    def clear_attributes(self):
        """
        Clears all attributes and mappings.
        """
        self._attributes = []
        self._default_mappings = []

    def add_default_mapping(self, input_attribute: JsonAttribute, output_attribute: JsonAttribute):
        """
        Adds default mapping between attributes. When you add default mapping associated RuleRunner will declare output variable with input.
        :param input_attribute: Input attribute.
        :param output_attribute: Output attribute.
        :return: Self
        """
        if input_attribute.attribute_type != JsonAttributeType.INPUT:
            raise ValueError("input_attribute must be type of JsonAttribute.INPUT")
        elif output_attribute.attribute_type != JsonAttributeType.OUTPUT:
            raise ValueError("output_attribute must be type of JsonAttribute.OUTPUT")
        self.add_default_mapping_with_index(self._attributes.index(input_attribute),
                                            self._attributes.index(output_attribute))
        return self

    def add_default_mapping_with_index(self, input_index: int, output_index: int):
        """
        Adds default mapping between attribute indexes.
        :param input_index: Input attribute index.
        :param output_index: Output attribute index.
        :return: Self
        """
        assert type(input_index) == int, "input index must be int type."
        assert type(output_index) == int, "output index must be int type."
        if self.get_all_attributes()[input_index].attribute_type != JsonAttributeType.INPUT:
            raise ValueError("input_attribute must be type of JsonAttribute.INPUT")
        elif self.get_all_attributes()[output_index].attribute_type != JsonAttributeType.OUTPUT:
            raise ValueError("output_attribute must be type of JsonAttribute.OUTPUT")
        if (input_index, output_index) not in self._default_mappings:
            self._default_mappings.append((input_index, output_index))
        return self


@bre_instance.register_for_json
class RuleExpression(DictSerializable):
    """
    Single rule expression in RuleRunner
    """

    _key = "RuleExpression"

    def set_base_container(self, base_container: BaseContainer):
        if not isinstance(base_container, BaseContainer):
            raise RuleCreationError(detail=["base_container must be BaseContainer type."])
        self._base_container = base_container

    def get_base_container(self):
        return self._base_container

    def get_actions(self):
        return self._actions

    def add_action(self, action_key: str, value: BaseValue):
        if not isinstance(value, BaseValue):
            raise RuleCreationError(detail=["Value must be BaseValue type."])
        self._actions.append({"key": str(action_key), "value": value})
        return self

    def clear_actions(self):
        self._actions = []
        return self

    def __init__(self, base_container: BaseContainer):
        self._actions = []
        self.set_base_container(base_container)

    @classmethod
    def from_dict(cls, dict_obj) -> "DictSerializable":
        assert dict_obj["key"] == cls._key, "Keys are inconsistent. Are you trying to deserialize different type?"
        current_obj = dict_obj["obj"]
        base_container = TypesHelper.from_dict_facade(current_obj["base_container"])
        result_obj = RuleExpression(base_container)
        for action in current_obj["actions"]:
            result_obj.add_action(action["param_key"], TypesHelper.from_dict_facade(action["value"]))
        return result_obj

    def to_dict(self) -> dict:
        result_dict = {"base_container": self._base_container.to_dict(), "actions": \
            [{"param_key": el["key"], "value": el["value"].to_dict()} for el in self._actions]}
        return {"key": self.__class__._key, "obj": result_dict}

    def validate_with_environment(self, environment: "Environment") -> bool:
        if not self._base_container.validate_with_environment(environment):
            return False
        for action in self._actions:
            if len(environment.query(dot_specifier=action["key"], attribute_type=JsonAttributeType.OUTPUT,
                                     read_only=False)) == 0:
                return False
            if not action["value"].validate_with_environment(environment):
                return False

        return True

    def run_on_dict(self, row):
        """
        Runs expression on dict object.

        :param row: Current row
        :return: manipulated row and change_set as tuple.
        """
        change_set = set()
        if self._base_container.evaluate(row):
            for action in self._actions:
                row = DotNotation.set_dot_notation(row, action["key"], action["value"].get_value(row))
                change_set.add(action["key"])
        return row, change_set


from collections.abc import Iterable


@bre_instance.register_for_json
class RuleRunner(DictSerializable):
    """
    RuleRunner object.
    """
    _key = "RuleRunner"

    @classmethod
    def from_dict(cls, dict_obj) -> "DictSerializable":
        assert dict_obj["key"] == cls._key, "Keys are inconsistent. Are you trying to deserialize different type?"
        result_obj = RuleRunner()
        for expr in dict_obj["obj"]["expressions"]:
            result_obj.add_expression(TypesHelper.from_dict_facade(expr))
        return result_obj

    def to_dict(self) -> dict:
        result_dict = {"expressions": [exp.to_dict() for exp in self._expressions]}
        return {"key": self.__class__._key, "obj": result_dict}

    def validate_with_environment(self, environment: "Environment" = None) -> bool:
        for exp in self._expressions:
            if not exp.validate_with_environment(environment):
                return False
        return True

    def __init__(self):
        self._expressions = []

    def add_expression(self, expression: RuleExpression):
        """
        Adds an expression to runner.

        :param expression: expression to be added.
        :return: Self
        """
        if not isinstance(expression, RuleExpression):
            raise RuleCreationError(detail=["expression must be type of RuleExpression"])
        self._expressions.append(expression)
        return self

    def get_expressions(self):
        """
        Gets expressions.

        :return: expressions.
        """
        return self._expressions

    def clear_expressions(self):
        """
        Clears all expressions.

        :return: Self
        """
        self._expressions = []
        return self

    def run_on_iterable(self, iter_object: Iterable, environment: Environment):
        assert isinstance(iter_object, Iterable) and isinstance(environment, Environment), \
            "iterator must be type of types.GeneratorType and environment must be Environment type."
        for current_row in iter_object:
            global_change_set = set()
            for expression in self._expressions:
                current_row, change_set = expression.run_on_dict(current_row)
                global_change_set.update(change_set)
            # Set to defaults where there is no assignment
            mappings = environment.get_all_default_mappings()
            for input_attribute, output_attribute in mappings:
                if output_attribute.dot_specifier not in global_change_set:
                    current_row = DotNotation.set_dot_notation(current_row, output_attribute.dot_specifier,
                                                               TYPE_PARSERS[output_attribute.attribute_data_type](
                                                                   DotNotation.get_dot_notation(current_row,
                                                                                                input_attribute.dot_specifier)))

            yield current_row

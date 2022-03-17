import re
from datetime import datetime
from .ruleengine import BusinessRuleEngine, DotNotation, TYPE_PARSERS

instance = BusinessRuleEngine.getInstance()

# Comparers

@instance.comparer("Equals", "Checks values are whether equals or not.",
                   collation_types=[
                       ("Boolean", "Boolean"),
                        ("String", "String"),
                        ("Numeric", "Numeric"),
                        ("DateTime", "DateTime"),
                        ],
                   #params=[{"pretty_name": "param1", "description": "def", "type": "String", "value_classes": ["Constant"]}],
                   _builtin=True
                   )
def equals(value, constant):
    if value is None or constant is None:
        return False
    return value==constant


@instance.comparer("Includes", "Checks first parameter includes second.",
                   collation_types=[
                        ("StringList", "String"),
                        ("NumericList", "Numeric"),
                        ("DateTimeList", "DateTime"),
                        ],
                   _builtin=True,              )
def includes(valuelist:list, constant):
    if valuelist is None or constant is None:
        return False
    return constant in valuelist



@instance.comparer("String Includes - Ignore Case", "Checks whether first parameter includes second.",
                   collation_types=[
                        ("String", "String"),
                        ],
                   _builtin=True)
def string_includes_ignorecase(value:str, constant:str):
    if value is None or constant is None:
        return False
    return  str(constant).lower() in str(value).lower()

#Start of filters

@instance.filter(pretty_name="String to Numeric", description="Convert string to numeric data.",
                 manipulation_types=[("String", "Numeric")], _builtin=True)
def string_to_numeric(param1:str):
    if param1 is None:
        return None
    return float(param1)


@instance.filter(pretty_name="Multiple Filter by Subvalue(Include) - Ignore case", description="Filters values of dictionary list by dot specified value. If dictionary object extracted value includes specified string (ignoring case) then will be returned back.",
                 manipulation_types=[("DictList", "DictList")],
                 params=[dict(pretty_name="Dot specifier", description="Dot specifier of extracted value.",
                              type="String", value_classes=["Constant"]),
                         dict(pretty_name="Value", description="Constant which will be tested whether in extracted value.",
                              type="String", value_classes=["Constant"]),
                         ]
                 , _builtin=True)
def multiple_filter_by_subvalue_include(dict_list_obj:list, dot_specifier:str, value:str):
    if dict_list_obj is None:
        return None
    try:
        result_set = []
        for row in dict_list_obj:
            if value.lower() in DotNotation.get_dot_notation(row, dot_specifier).lower():
                result_set.append(row)
        return result_set
    except Exception as e:
        return []


@instance.filter(pretty_name="Filter by Subvalue(Include) - Ignore case", description="Filters values of dictionary list by dot specified value. First occurence will be returned back.",
                 manipulation_types=[("DictList", "Dict")],
                 params=[dict(pretty_name="Dot specifier", description="Dot specifier of extracted value.",
                              type="String", value_classes=["Constant"], _builtin=True),
                         dict(pretty_name="Value", description="Constant which will be tested whether in extracted value.",
                              type="String", value_classes=["Constant"], _builtin=True),
                         ], _builtin=True)
def filter_by_subvalue_include(dict_list_obj:list, dot_specifier:str, value:str):
    if dict_list_obj is None:
        return None
    try:
        for row in dict_list_obj:
            if value.lower() in DotNotation.get_dot_notation(row, dot_specifier).lower():
                return row
        return None
    except Exception as e:
        return None



@instance.filter(pretty_name="Multiple Filter by Subvalue(Exact) - Ignore case", description="Filters values of dictionary list by dot specified value. If dictionary object extracted value equals specified string (ignoring case) then will be returned back.",
                 manipulation_types=[("DictList", "DictList")],
                 params=[dict(pretty_name="Dot specifier", description="Dot specifier of extracted value.",
                              type="String", value_classes=["Constant"]),
                         dict(pretty_name="Value", description="Constant which will be tested whether equals to extracted value.",
                              type="String", value_classes=["Constant"]),
                         ]
                 , _builtin=True)
def multiple_filter_by_subvalue(dict_list_obj:list, dot_specifier:str, value:str):
    if dict_list_obj is None:
        return None
    try:
        result_set = []
        for row in dict_list_obj:
            if value.lower() == DotNotation.get_dot_notation(row, dot_specifier).lower():
                result_set.append(row)
        return result_set
    except Exception as e:
        return []


@instance.filter(pretty_name="Filter by Subvalue(Exact) - Ignore case", description="Filters values of dictionary list by dot specified value. First occurence will be returned back.",
                 manipulation_types=[("DictList", "Dict")],
                 params=[dict(pretty_name="Dot specifier", description="Dot specifier of extracted value.",
                              type="String", value_classes=["Constant"], _builtin=True),
                         dict(pretty_name="Value", description="Constant which will be tested whether equals to extracted value.",
                              type="String", value_classes=["Constant"], _builtin=True),
                         ], _builtin=True)
def filter_by_subvalue(dict_list_obj:list, dot_specifier:str, value:str):
    if dict_list_obj is None:
        return None
    try:
        for row in dict_list_obj:
            if value.lower() == DotNotation.get_dot_notation(row, dot_specifier).lower():
                return row
        return None
    except Exception as e:
        return None


@instance.filter(pretty_name="Extract String from a dictionary object.", description="Extract string value from a single dictionary object.",
                 manipulation_types=[("Dict", "String")],
                 params=[dict(pretty_name="Dot specifier", description="Dot specifier of which will be extracted.",
                              type="String", value_classes=["Constant"], _builtin=True),
                         ], _builtin=True)
def extract_with_dot_specifier_to_string(dict_obj:dict, dot_specifier:str):
    if dict_obj is None:
        return None
    value = DotNotation.get_dot_notation(dict_obj, dot_specifier)
    if value is None:
        return None
    return TYPE_PARSERS["String"](value)


@instance.filter(pretty_name="Extract String from a dictionary object.", description="Extract numeric value from a single dictionary object.",
                 manipulation_types=[("Dict", "Numeric")],
                 params=[dict(pretty_name="Dot specifier", description="Dot specifier of which will be extracted.",
                              type="String", value_classes=["Constant"], _builtin=True),
                         ], _builtin=True)
def extract_with_dot_specifier_to_numeric(dict_obj:dict, dot_specifier:str):
    if dict_obj is None:
        return None
    value = DotNotation.get_dot_notation(dict_obj, dot_specifier)
    if value is None:
        return None
    return TYPE_PARSERS["Numeric"](value)


@instance.filter(pretty_name="Numeric to String", description="Convert Numeric to String data.",
                 manipulation_types=[("Numeric", "String")], _builtin=True)
def numeric_to_string(numeric:str):
    if numeric is None:
        return None
    return f"{numeric}"


@instance.filter(pretty_name="UTC Epoch to DateTime", description="Convert unix utc epoch to DateTime",
                 manipulation_types=[("Numeric", "DateTime")], _builtin=True)
def unixepoch_to_datetime(numeric:str):
    if numeric is None:
        return None
    return datetime.utcfromtimestamp(numeric)


#TODO: filter_has_key_regex
#TODO: extract_value_from_dictlist
#TODO: filter_list




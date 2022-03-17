import unittest
import json

from movejson.types import Environment, JsonAttributeType, JsonAttribute, TypesHelper, Attribute, Constant, \
    RuleExpression, AndOperatorContainer, OrOperatorContainer, RuleRunner, bre_instance
from movejson.helpers import Helper
from tests import TEST_OUTPUT_DIR


class TestRuleRunner(unittest.TestCase):
    def test_environment(self):
        env = self._fetch_sample_environment()
        expression = RuleRunner().\
            add_expression(
                RuleExpression(
                    AndOperatorContainer().add_comparer("equals", Attribute("a.$val", "String"), Constant(5))
                )
        )
        self.assertTrue(expression.validate_with_environment(env))
        self.assertTrue(AndOperatorContainer().add_comparer("equals", Attribute("a.$val", "String"), Constant(5)).validate_with_environment(env))
        self.assertTrue(RuleExpression(
                    AndOperatorContainer().add_comparer("equals", Attribute("a.$val", "String"), Constant(5))
                ).validate_with_environment(env))
        expression = RuleExpression(
            AndOperatorContainer().add_comparer("equals", Attribute("a.$val", "String"), Constant(5)))
        self.assertTrue(expression.validate_with_environment(env))
        expression = RuleExpression(
            AndOperatorContainer().add_comparer("equals", Attribute("a.$val", "String"), Constant(5))).add_action("cd",
                                                                                                                  Constant(
                                                                                                                      18))
        self.assertFalse(expression.validate_with_environment(env))

        expression = RuleExpression(
            AndOperatorContainer().add_comparer("equals", Attribute("a.$val", "String"), Constant(5))).add_action("c",
                                                                                                                  Constant(
                                                                                                                      18))
        self.assertTrue(expression.validate_with_environment(env))

    def _fetch_sample_environment(self):
        return Environment().\
            add_attribute(JsonAttribute("a.$val", JsonAttributeType.INPUT, "String", "A")).\
            add_attribute(JsonAttribute("b", JsonAttributeType.OUTPUT, "Numeric", "B")). \
            add_attribute(JsonAttribute("c", JsonAttributeType.OUTPUT, "Numeric", "C")). \
            add_attribute(JsonAttribute("d", JsonAttributeType.INPUT, "Numeric", "C")). \
            add_default_mapping_with_index(0, 1)

    def test_on_row(self):
        env = self._fetch_sample_environment()

        self.assertTrue(AndOperatorContainer().evaluate({}))

        runner = RuleRunner().\
            add_expression(
                RuleExpression(AndOperatorContainer()
                               .add_comparer("equals", Attribute("a.$val", "String"), Constant(5))
                               .add_comparer("equals", Attribute("a.$val", "String"), Constant(30)))
                    .add_action("c", Constant(35))
            )
        self.assertTrue(runner.validate_with_environment(env))

        result = next(runner.run_on_iterable([{"a": "5"}], env))

        self.assertNotIn("c", result)

        runner = RuleRunner(). \
            add_expression(
            RuleExpression(OrOperatorContainer()
                           .add_comparer("equals", Attribute("a.$val", "String"), Constant(5))
                           .add_comparer("equals", Attribute("a.$val", "String"), Constant(30)))
                .add_action("c", Constant(35))
        )
        self.assertTrue(runner.validate_with_environment(env))

        result = next(runner.run_on_iterable([{"a": "5.0"}], env))
        self.assertIn("c", result)
        self.assertIn("b", result)

        self.assertEqual(result["c"], 35.0)

    def test_jsonattribute(self):
        self.assertEqual(JsonAttribute("ab", JsonAttributeType.INPUT, "String", "Ab", "Desc"),
                         TypesHelper.from_dict_facade(JsonAttribute("ab", JsonAttributeType.INPUT, "String", "Ab", "Desc").to_dict()))

    def test_env(self):
        env = Environment() \
            .add_attribute(JsonAttribute("$out_transaction_id", JsonAttributeType.OUTPUT, "Numeric", "Transaction Id",
                                         "Transaction id of respecting item", True)) \
            .add_attribute(
            JsonAttribute("$out_title", JsonAttributeType.OUTPUT, "String", "Title", "Title of item.", False, 200)) \
            .add_attribute(
            JsonAttribute("$out_description", JsonAttributeType.OUTPUT, "String", "Description", "Description of item.",
                          False, 4000)) \
            .add_attribute(JsonAttribute("$out_seller_user_id", JsonAttributeType.OUTPUT, "Numeric", "Seller User Id",
                                         "Numeric seller user id from Etsy source.", False)) \
            .add_attribute(JsonAttribute("$out_buyer_user_id", JsonAttributeType.OUTPUT, "Numeric", "Buyer User Id",
                                         "Numeric buyer user id from Etsy source.", False)) \
            .add_attribute(JsonAttribute("$out_listing_id", JsonAttributeType.OUTPUT, "Numeric", "Listing Id",
                                         "Listing id from Etsy source.", False)) \
            .add_attribute(
            JsonAttribute("$out_creation_tsz", JsonAttributeType.OUTPUT, "DateTime", "Creation Timestamp",
                          "Date and time of item.", False)) \
            .add_attribute(
            JsonAttribute("$out_price", JsonAttributeType.OUTPUT, "Numeric", "Price", "Price of respective item.",
                          False)) \
            .add_attribute(JsonAttribute("$out_shipping_cost", JsonAttributeType.OUTPUT, "Numeric", "Shipping Cost",
                                         "Ship cost of respective item.", False)) \
            .add_attribute(JsonAttribute("$out_quantity", JsonAttributeType.OUTPUT, "Numeric", "Quantity",
                                         "Quantity of respective item.", False)) \
            .add_attribute(
            JsonAttribute("$out_product_data_param_type", JsonAttributeType.OUTPUT, "String", "Product Type",
                          "Free text specification of product type.", False, 100)) \
            .add_attribute(JsonAttribute("$out_product_data_length", JsonAttributeType.OUTPUT, "Numeric", "Length",
                                         "Length of product.", False)) \
            .add_attribute(
            JsonAttribute("$out_product_data_color", JsonAttributeType.OUTPUT, "String", "Color", "Color of product.",
                          False, 80)) \
            .add_attribute(
            JsonAttribute("$out_product_data_personalization", JsonAttributeType.OUTPUT, "String", "Personalization",
                          "Personalization notes.", False, 1000)) \
            .add_attribute(
            JsonAttribute("$out_product_data_thickness", JsonAttributeType.OUTPUT, "Numeric", "Thickness",
                          "Thickness of product.", False)) \
            .add_attribute(
            JsonAttribute("$out_product_data_start", JsonAttributeType.OUTPUT, "String", "Start", "Start of accessory.",
                          False, 100)) \
            .add_attribute(
            JsonAttribute("$out_product_data_space", JsonAttributeType.OUTPUT, "String", "Space", "Space definition.",
                          False, 100)) \
            .add_attribute(
            JsonAttribute("receipt_id.$val", JsonAttributeType.INPUT, "Numeric", "Receipt Id", "Receipt id of order",
                          True))

    def test_emre(self):
        env = Environment()\
            .add_attribute(JsonAttribute("$transaction_title.$val", JsonAttributeType.INPUT, "String", "Title", "Title Desc"))\
            .add_attribute(JsonAttribute("$transaction_variations", JsonAttributeType.INPUT, "DictList", "Variations", "Variations Desc")) \
            .add_attribute(JsonAttribute("$out_type", JsonAttributeType.OUTPUT, "String", "Type",
                                         "Type Desc")) \
            .add_attribute(JsonAttribute("$out_size", JsonAttributeType.OUTPUT, "Numeric", "Size",
                                         "Size Desc")) \
            .add_attribute(JsonAttribute("$out_color", JsonAttributeType.OUTPUT, "String", "Color",
                                         "Color Desc")) \
            .add_attribute(JsonAttribute("$out_length", JsonAttributeType.OUTPUT, "Numeric", "Length",
                                         "Length Desc")) \
            .add_attribute(JsonAttribute("$out_start", JsonAttributeType.OUTPUT, "String", "Start",
                                         "Start Desc"))
        with open(TEST_OUTPUT_DIR.joinpath("environment_spec.json"), "w", encoding="utf8") as f:
            f.write(json.dumps(env.to_dict(), indent=4))

        filters = bre_instance.get_filters()
        comparers = bre_instance.get_comparers()
        with open(TEST_OUTPUT_DIR.joinpath("all_filters_spec.json"), "w", encoding="utf8") as f:
            f.write(json.dumps({filter_cur:Helper.exclude_keys(filters[filter_cur], ["method"]) for filter_cur in filters}, indent=4))
        with open(TEST_OUTPUT_DIR.joinpath("all_comparers_spec.json"), "w", encoding="utf8") as f:
            f.write(json.dumps({comparer_cur:Helper.exclude_keys(comparers[comparer_cur], ["method"]) for comparer_cur in comparers}, indent=4))

        rule_runner = RuleRunner() \
            .add_expression(
                RuleExpression(
                    AndOperatorContainer() \
                        .add_comparer("string_includes_ignorecase",
                                      Attribute("$transaction_variations", "DictList")\
                                            .add_filter("filter_by_subvalue_include", Constant("formatted_name.$val"), Constant("Color"))\
                                            .add_filter("extract_with_dot_specifier_to_string", Constant("formatted_value.$val"))
                                      ,
                                      Constant("Gold"))
                ).add_action("$out_color", Constant("Gold"))
            ) \
            .add_expression(
                RuleExpression(
                    AndOperatorContainer() \
                        .add_comparer("string_includes_ignorecase",
                                      Attribute("$transaction_variations", "DictList") \
                                      .add_filter("filter_by_subvalue_include", Constant("formatted_name.$val"), Constant("Color")) \
                                      .add_filter("extract_with_dot_specifier_to_string", Constant("formatted_value.$val"))
                                      ,
                                      Constant("Rose"))
                ).add_action("$out_color", Constant("Rose"))
            ) \
            .add_expression(
                RuleExpression(
                    AndOperatorContainer() \
                        .add_comparer("string_includes_ignorecase",
                                      Attribute("$transaction_variations", "DictList") \
                                      .add_filter("filter_by_subvalue_include", Constant("formatted_name.$val"), Constant("Color")) \
                                      .add_filter("extract_with_dot_specifier_to_string", Constant("formatted_value.$val"))
                                      ,
                                      Constant("Silver"))
                ).add_action("$out_color", Constant("Silver"))
            ) \
            .add_expression(
                RuleExpression(
                    AndOperatorContainer() \
                        .add_comparer("string_includes_ignorecase",
                                      Attribute("$transaction_variations", "DictList") \
                                      .add_filter("filter_by_subvalue_include", Constant("formatted_name.$val"), Constant("Length")) \
                                      .add_filter("extract_with_dot_specifier_to_string", Constant("formatted_value.$val"))
                                      ,
                                      Constant("18", "String"))
                ).add_action("$out_length", Constant(45))
            ) \
            .add_expression(
                RuleExpression(
                    AndOperatorContainer() \
                        .add_comparer("string_includes_ignorecase",
                                      Attribute("$transaction_variations", "DictList") \
                                      .add_filter("filter_by_subvalue_include", Constant("formatted_name.$val"), Constant("Length")) \
                                      .add_filter("extract_with_dot_specifier_to_string", Constant("formatted_value.$val"))
                                      ,
                                      Constant("14", "String"))
                ).add_action("$out_length", Constant(45))
            ) \
            .add_expression(
                RuleExpression(
                    AndOperatorContainer() \
                        .add_comparer("string_includes_ignorecase",
                                      Attribute("$transaction_variations", "DictList") \
                                      .add_filter("filter_by_subvalue_include", Constant("formatted_name.$val"), Constant("Length")) \
                                      .add_filter("extract_with_dot_specifier_to_string", Constant("formatted_value.$val"))
                                      ,
                                      Constant("16", "String"))
                ).add_action("$out_length", Constant(40))
            ) \
            .add_expression(
                RuleExpression(
                    AndOperatorContainer() \
                        .add_comparer("string_includes_ignorecase",
                                      Attribute("$transaction_variations", "DictList") \
                                      .add_filter("filter_by_subvalue_include", Constant("formatted_name.$val"), Constant("Length")) \
                                      .add_filter("extract_with_dot_specifier_to_string", Constant("formatted_value.$val"))
                                      ,
                                      Constant("20", "String"))
                ).add_action("$out_length", Constant(50))
            ) \
            .add_expression(
                RuleExpression(
                    AndOperatorContainer() \
                        .add_comparer("string_includes_ignorecase",
                                      Attribute("$transaction_variations", "DictList") \
                                      .add_filter("filter_by_subvalue_include", Constant("formatted_name.$val"), Constant("Length")) \
                                      .add_filter("extract_with_dot_specifier_to_string", Constant("formatted_value.$val"))
                                      ,
                                      Constant("22", "String"))
                ).add_action("$out_length", Constant(55))
            ) \
            .add_expression(
                RuleExpression(
                    AndOperatorContainer() \
                        .add_comparer("string_includes_ignorecase",
                                      Attribute("$transaction_title.$val", "String")
                                      ,
                                      Constant("Personalized Letter"))
                )\
                    .add_action("$out_type", Constant("Kolye ortada harf")) \
                    .add_action("$out_size", Constant(5)) \
                    .add_action("$out_start", Constant("Ortada"))
            )

        self.assertTrue(rule_runner.validate_with_environment(env))
        with open(TEST_OUTPUT_DIR.joinpath("rule_runner.json"), "w", encoding="utf8") as f:
            f.write(json.dumps(rule_runner.to_dict(), indent=4))

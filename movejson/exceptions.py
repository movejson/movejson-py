class DotNotationError(Exception):
    pass


class SubscriptionError(Exception):
    pass


class BusinessRuleEngineApiError(Exception):
    pass


class BusinessRuleEngineAssertionError(Exception):
    def __init__(self, *args, **kwargs):
        detail = kwargs.pop("detail", None)
        super(BusinessRuleEngineAssertionError, self).__init__(*args, **kwargs)
        assert detail is None or type(detail) == dict, "detail must be dict type"
        self.detail = detail


class RuleCreationError(Exception):
    def __init__(self, *args, **kwargs):
        detail = kwargs.pop("detail", [])
        msg = "detail must be list of strings"
        assert detail is None or type(detail) == list, msg
        if detail:
            assert all([type(x) == str for x in detail]), msg
            super(RuleCreationError, self).__init__(
                *list([(str(args[0]) + "\n" if len(args) > 0 else "") + str(detail)]), **kwargs)
        else:
            super(RuleCreationError, self).__init__(*args, **kwargs)
        self.detail = detail


class RunnerError(Exception):
    pass


class ParseError(Exception):
    pass


class ValidationError(Exception):
    pass

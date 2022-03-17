from collections.abc import Iterable


class Helper:
    @staticmethod
    def prefix_filter(iterable: Iterable, prefix: str):
        for row in iterable:
            yield {k: row[k] for k in row if k.startswith(str(prefix))}

    @staticmethod
    def exclude_keys(dict_obj: dict, keys: list):
        return {k: dict_obj[k] for k in dict_obj if k not in keys}

    @staticmethod
    def include_keys(dict_obj: dict, keys: list):
        return {k: dict_obj[k] for k in dict_obj if k in keys}

    @staticmethod
    def base_copy(dict_obj: dict):
        return {k: dict_obj[k] for k in dict_obj}


class DetailDataNormalizer:
    _detail_key = None
    _normalized_prefix = None

    @property
    def detail_key(self):
        return self._detail_key

    @detail_key.setter
    def detail_key(self, value):
        self._detail_key = str(value)

    @property
    def normalized_prefix(self):
        return self._normalized_prefix

    @normalized_prefix.setter
    def normalized_prefix(self, value):
        self._normalized_prefix = value

    def __init__(self, detail_key: str, normalized_prefix: str):
        self.detail_key = detail_key
        self.normalized_prefix = normalized_prefix

    def iterate_on(self, iterable: Iterable):
        detail_key = self._detail_key
        prefix = self._normalized_prefix
        for outer_row in iterable:
            for inner_row in outer_row[detail_key]:
                current_row = Helper.base_copy(outer_row)
                for inner_key in inner_row:
                    current_row[prefix + inner_key] = inner_row[inner_key]
                yield current_row

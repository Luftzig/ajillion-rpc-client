import collections
from enum import Enum
import inspect

__author__ = 'yoav.luft@ajillionmax.com'


class DictDeserializer(object):
    """
    DictDeserializer is an object that given a callable that construct an object and a dictionary of mapping rules will
    convert dictionary into the object constructed by the function.

    The mapping rules define how the raw dictionary values should be passed to the creating function. Each key in the
    mapping rules will be matched to a key in the raw data and the rule's value will be used for mapping according to:

    * If rule is integer, the raw data value will be passed as a positional argument in the rule as ordering.
    * If rule is a string, the raw data value will be used as keyword argument with the rule as a key.
    * If rule is a callable it will be invoked with (key, raw[key]) and should return a (keyword, value) tuple that
      will be passed as a keyword argument.

    Examples::

      # Calls `Thing('something')`
      DictDeserializer(Thing, {'argument': 0}).
        create_from({'argument': 'something'})

      # Calls `Thing(key1='something')`
      DictDeserializer(Thing, {'arg': 'key1'}).
        create_from({'arg': 'something'})

      another_deserializer = DictDeserializer(AnotherThing, {...})
      thing_deserializer = DictDeserializer(Thing,
                                            {'arg': lambda k, v: ('another', another_deserializer.create_from(v))})
      # Calls `Thing(another=another_deserializer.create_from({'a': 1, 'b': 2}))`
      thing_deserializer.create_from({'arg': {'a': 1, 'b': 2}})

    """

    class UnmappedBehaviour(Enum):
        """
        Defines how the deserializer should handle input dictionary fields without mapping rules.
        IGNORE: just ignore them. Default behaviour.
        TO_KWARGS: Pass them to creating function without any mapping.
        FAIL: Fail and raise DeserializerError
        """
        IGNORE = 0
        TO_KWARGS = 1
        FAIL = 2

    class DeserializerError(TypeError):
        pass

    def __init__(self, creator, mapping_rules=None, **kwargs):
        """
        Instantiate new deserializer that will use the creator callable and the mapping rules to create new objects.
        :param creator: A callable that will be used for creating new objects. Usually the class itself.
        :param mapping_rules: A dictionary of raw data keys and rules to how they should be used when calling the
         creator callable
        :param unmapped_behaviour:
        :return:
        """
        if not mapping_rules:
            mapping_rules = {}
        if not (inspect.isclass(creator) or inspect.isfunction(creator)):
            raise TypeError("creator must be a callable or class")
        self.target_class = creator
        self.rules = mapping_rules
        self.unmapped_behaviour = kwargs.pop('unmapped_behaviour', DictDeserializer.UnmappedBehaviour.IGNORE)

    def _map_value(self, key, raw):
        rule = self.rules[key]
        keyword = value = index = None
        if callable(rule):
            keyword, value = rule(key, raw[key])
        elif isinstance(rule, str):
            keyword, value = rule, raw[key]
        elif isinstance(rule, int):
            index, value = rule, raw[key]
        return index, keyword, value

    def _map_arguments(self, raw):
        arguments = []
        keywords = {}
        raw_keys_set = set(raw.keys())
        rules_keys_set = set(self.rules.keys())
        unmapped = self._handle_unmapped_values(rules_keys_set, raw_keys_set, raw)
        for key in raw_keys_set.intersection(rules_keys_set):
            index, keyword, value = self._map_value(key, raw)
            if index is not None:
                arguments.insert(index, value)
            else:
                keywords[keyword] = value
        keywords.update(unmapped)
        return arguments, keywords

    def _handle_unmapped_values(self, rules_set, raw_set, raw_data):
        if self.unmapped_behaviour == DictDeserializer.UnmappedBehaviour.IGNORE:
            return {}
        unmapped_keys = raw_set - rules_set
        if self.unmapped_behaviour == DictDeserializer.UnmappedBehaviour.FAIL and len(unmapped_keys) > 0:
            raise DictDeserializer.DeserializerError("The following keys do no have mapping rules: %s"
                                                     % str(unmapped_keys))
        return {k: raw_data[k] for k in unmapped_keys}

    def create_from(self, raw: dict) -> 'object':
        if not isinstance(raw, dict):
            raise DictDeserializer.DeserializerError("Deserialized object must be a dictionary object")
        arguments, keywords = self._map_arguments(raw)
        try:
            return self.target_class(*arguments, **keywords)
        except (AttributeError, TypeError) as e:
            raise DictDeserializer.DeserializerError("Failed to create object") from e


class IterableDictDeserializer(DictDeserializer):
    """
    The same as :class:`DictDeserializer` only that it accepts an iterable and return an iterable of deserialized objects
    """
    def __init__(self, creator, mapping_rules=None, **kwargs):
        super(IterableDictDeserializer, self).__init__(creator, mapping_rules, **kwargs)

    def create_from(self, raw: collections.Iterable) -> collections.Iterable:
        return map(super(IterableDictDeserializer, self).create_from, raw)


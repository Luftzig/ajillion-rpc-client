import collections
from unittest.case import TestCase

from rpcclient.deserialize import DictDeserializer, IterableDictDeserializer


__author__ = 'yoav.luft@ajillionmax.com'


class DeserializerTests(TestCase):

    def test_ignore_with_args(self):
        class Thing(object):
            def __init__(self, arg1, arg2):
                self.arg2 = arg2
                self.arg1 = arg1

        deserializer = DictDeserializer(Thing, mapping_rules={'a1': 0, 'a2': 1})
        thing = deserializer.create_from({'a2': 'arg2', 'a1': 'arg1', 'ignored': 'Ignored'})
        self.assertIsInstance(thing, Thing)
        self.assertEqual(thing.arg1, 'arg1')
        self.assertEqual(thing.arg2, 'arg2')

    def test_ignore_with_kwargs(self):
        class Thing(object):
            def __init__(self, arg1, arg2):
                self.arg2 = arg2
                self.arg1 = arg1

        deserializer = DictDeserializer(Thing, mapping_rules={'a1': 'arg1', 'a2': 'arg2'})
        thing = deserializer.create_from({'a2': 'arg2', 'a1': 'arg1', 'ignored': 'Ignored'})
        self.assertIsInstance(thing, Thing)
        self.assertEqual(thing.arg1, 'arg1')
        self.assertEqual(thing.arg2, 'arg2')

    def test_ignore_with_mixed(self):
        class Thing(object):
            def __init__(self, arg1, arg2, **kwargs):
                self.arg2 = arg2
                self.arg1 = arg1
                self.kwarg1 = kwargs.pop('key1')

        deserializer = DictDeserializer(Thing, mapping_rules={'a1': 0, 'a2': 1, 'key_arg': 'key1'})
        thing = deserializer.create_from({'a2': 'arg2', 'a1': 'arg1', 'ignored': 'Ignored', 'key_arg': 'keyword arg'})
        self.assertIsInstance(thing, Thing)
        self.assertEqual(thing.arg1, 'arg1')
        self.assertEqual(thing.arg2, 'arg2')
        self.assertEqual(thing.kwarg1, 'keyword arg')

    def test_transforming_rule(self):
        class Thing(object):
            def __init__(self, arg1, arg2):
                self.arg2 = arg2
                self.arg1 = arg1

        deserializer = DictDeserializer(Thing, mapping_rules={'a1': 0, 'a2': lambda k, v: ('arg2', v * 2)})
        thing = deserializer.create_from({'a2': 'arg2', 'a1': 'arg1'})
        self.assertIsInstance(thing, Thing)
        self.assertEqual(thing.arg1, 'arg1')
        self.assertEqual(thing.arg2, 'arg2arg2')

    def test_fail_on_missing_args(self):
        class Thing(object):
            def __init__(self, arg1, arg2):
                self.arg2 = arg2
                self.arg1 = arg1

        deserializer = DictDeserializer(Thing, mapping_rules={'a1': 0, 'a2': lambda k, v: ('arg2', v * 2)})
        self.assertRaises(DictDeserializer.DeserializerError, deserializer.create_from, {'a2': 'arg2'})

    def test_fail_on_extra_keywords(self):
        class Thing(object):
            def __init__(self, arg1, arg2):
                self.arg2 = arg2
                self.arg1 = arg1

        deserializer = DictDeserializer(Thing,
                                    mapping_rules={'a1': 0, 'a2': lambda k, v: ('arg2', v * 2)},
                                    unmapped_behaviour=DictDeserializer.UnmappedBehaviour.FAIL)
        self.assertRaises(DictDeserializer.DeserializerError, deserializer.create_from, {'a2': 'arg2', 'a1': 'arg1', 'extra': 3})

    def test_pass_unmapped(self):
        class Thing(object):
            def __init__(self, arg1, arg2, **kwargs):
                self.arg2 = arg2
                self.arg1 = arg1
                self.kwarg1 = kwargs.pop('key1')

        deserializer = DictDeserializer(Thing,
                                    mapping_rules={'a1': 0, 'key_arg': 'key1'},
                                    unmapped_behaviour=DictDeserializer.UnmappedBehaviour.TO_KWARGS)
        thing = deserializer.create_from({'arg2': 'arg2', 'a1': 'arg1', 'ignored': 'Ignored', 'key_arg': 'keyword arg'})
        self.assertIsInstance(thing, Thing)
        self.assertEqual(thing.arg1, 'arg1')
        self.assertEqual(thing.arg2, 'arg2')
        self.assertEqual(thing.kwarg1, 'keyword arg')


class TestIterableDeserializer(TestCase):

    def test_deserialize_from_iterable(self):
        class Thing(object):
            def __init__(self, arg1, **kwargs):
                self.arg1 = arg1
                self.kwarg1 = kwargs.pop('key1')

        data = [{'a1': 'obj1', 'key_arg': 'Something'}, {'a1': 'obj2', 'key_arg': 'something else'}]
        deserializer = IterableDictDeserializer(Thing, mapping_rules={'a1': 0, 'key_arg': 'key1'})
        things = deserializer.create_from(data)
        self.assertIsInstance(things, collections.Iterable)
        things_list = list(things)
        self.assertEqual(len(things_list), len(data))
        self.assertEqual(things_list[0].arg1, 'obj1')
        self.assertEqual(things_list[0].kwarg1, 'Something')
        self.assertEqual(things_list[1].arg1, 'obj2')

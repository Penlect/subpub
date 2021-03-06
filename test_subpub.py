"""Unittests for subpub module"""

# Built-in
import asyncio
import doctest
import queue
import re
import threading
import unittest

# Module
import subpub
from subpub import (SubPub, MqttTopic, ExceptionAwareQueue,
                    AsyncSubPub, AsyncExceptionAwareQueue)


class TestSubPub(unittest.TestCase):
    """Test SubPub"""

    def test_repr(self):
        r = 'SubPub(queue_factory=ExceptionAwareQueue, timeout=10)'
        self.assertEqual(repr(eval(r, globals())), r)

    def test_default_queue_factory(self):
        self.assertIs(SubPub().queue_factory, queue.SimpleQueue)

    def test_custom_queue_factory(self):
        self.assertIs(SubPub(ExceptionAwareQueue).queue_factory,
                      ExceptionAwareQueue)

    def test_queue_type(self):
        sp = SubPub(ExceptionAwareQueue)
        q = sp.subscribe('MelodiesOfLife')
        self.assertIsInstance(q, ExceptionAwareQueue)

    def test_subscribe_twice(self):
        sp = SubPub()
        q1 = sp.subscribe('EyesOnMe')
        q2 = sp.subscribe('EyesOnMe')
        self.assertIsNot(q1, q2)

    def test_subscribe_simple(self):
        sp = SubPub()
        q = sp.subscribe("Aerith/Theme")
        recv = sp.publish("Aerith/Theme", 81611)
        self.assertTrue(recv)
        match, data = q.get()
        self.assertTrue(match)
        self.assertEqual(data, 81611)

    def test_unsubscribe(self):
        sp = SubPub()
        topic = "Olofsbäcks Gård"
        q = sp.subscribe(topic)
        sp.publish(topic, 81611)
        self.assertTrue(q.get_nowait())
        ok = sp.unsubscribe(topic)
        self.assertTrue(ok)
        with self.assertRaises(queue.Empty):
            q.get_nowait()

    def test_unsubscribe_not_subscribed(self):
        sp = SubPub()
        self.assertFalse(sp.unsubscribe("Happiness"))

    def test_unsubscribe_all(self):
        sp = SubPub()
        self.assertEqual(sp.unsubscribe_all(), 0)
        sp.subscribe("Chalmers")
        sp.subscribe("GU")
        self.assertEqual(sp.unsubscribe_all(), 0)
        # Keep references
        q1 = sp.subscribe("Chalmers")
        q2 = sp.subscribe("GU")
        self.assertEqual(sp.unsubscribe_all(), 2)

    def test_unsubscribe_gc(self):
        sp = SubPub()
        def f():
            q = sp.subscribe('Trädgårdsgatan/23')
            recv = sp.publish('Trädgårdsgatan/23', 404)
            self.assertTrue(recv)
        f()
        recv = sp.publish('Trädgårdsgatan/23', 404)
        # q garbage collected => automatic unsubscribe
        self.assertFalse(recv)

    def test_subscribe_custom_queue(self):
        sp = SubPub()
        q = queue.PriorityQueue()
        q_out = sp.subscribe('', queue=q)
        self.assertIs(q_out, q)
        q_out = sp.subscribe('', queue=q)
        self.assertIs(q_out, q)
        q_out = sp.subscribe('')
        self.assertIsInstance(q_out, queue.SimpleQueue)
        q_out = sp.subscribe('', queue=queue.LifoQueue())
        self.assertIsInstance(q_out, queue.LifoQueue)

    def test_publish_no_one_cares(self):
        sp = SubPub()
        recv = sp.publish('Hans Andersson', 'Water')
        self.assertFalse(recv)

    def test_publish_retained(self):
        sp = SubPub()
        topic = 'Sober'
        data_in = 'Nope'
        recv = sp.publish(topic, data_in, retain=True)
        self.assertFalse(recv)
        q = sp.subscribe(topic)
        match, data_out = q.get_nowait()
        self.assertEqual(match.re.pattern, topic)
        self.assertIs(data_out, data_in)

    def test_publish_remove_retained(self):
        sp = SubPub()
        topic = 'JudgmentDay'
        sp.publish(topic, 'anything but None', retain=True)
        sp.subscribe(topic).get_nowait()
        sp.publish(topic, None, retain=True)
        with self.assertRaises(queue.Empty):
            sp.subscribe(topic).get_nowait()

    def test_publish_block_and_timeout(self):
        sp = SubPub()
        topic = 'Saturn'
        q = sp.subscribe(topic, queue=queue.Queue(1))
        sp.publish(topic, 'Pollux')
        with self.assertRaises(queue.Full):
            sp.publish(topic, 'Castor', timeout=0.001)

    def test_mqtt_style(self):
        sp = SubPub()
        topic = MqttTopic('Daniel/+/+/+/#')
        q = sp.subscribe(topic)
        sp.publish('Daniel/2005/12/18/02:45:00', 'So help me God')
        match, data = q.get(timeout=1)
        self.assertEqual(match.groups(), ('2005', '12', '18', '02:45:00'))
        self.assertEqual(data, 'So help me God')
        self.assertTrue(sp.unsubscribe(topic))

    def test_with_threads(self):
        sp = SubPub()
        q = sp.subscribe(r'\d+')
        for i in range(10):
            t = threading.Thread(target=sp.publish, args=(str(i), i))
            t.start()
        self.assertEqual([q.get()[1] for _ in range(10)], list(range(10)))


class TestMqttTopic(unittest.TestCase):

    def test_single_level_wildcard(self):
        t = MqttTopic('/+/')
        regex = re.compile('/([^/]*)/')
        self.assertEqual(t.as_regexp(), regex)

    def test_multi_level_wildcard(self):
        t = MqttTopic('#')
        regex = re.compile('(.*)$')
        self.assertEqual(t.as_regexp(), regex)

    def test_plus_wildcard(self):
        t = MqttTopic('room/3/sensor/+/temperature/#')
        regex = re.compile('room/3/sensor/([^/]*)/temperature/(.*)$')
        self.assertEqual(t.as_regexp(), regex)


class TestExceptionAwareQueue(unittest.TestCase):

    def test_exception_instance(self):
        with self.assertRaises(Exception):
            q = ExceptionAwareQueue()
            q.put((None, Exception('Olofsbäcks Gård')))
            q.get()

    def test_exception_class(self):
        q = ExceptionAwareQueue()
        q.put((None, Exception))
        q.get()


class TestAsyncSubPub(unittest.IsolatedAsyncioTestCase):
    """Test AsyncSubPub"""

    def test_repr(self):
        r = 'AsyncSubPub(queue_factory=AsyncExceptionAwareQueue, timeout=10)'
        self.assertEqual(repr(eval(r, globals())), r)

    def test_default_queue_factory(self):
        self.assertIs(AsyncSubPub().queue_factory, asyncio.Queue)

    def test_custom_queue_factory(self):
        self.assertIs(AsyncSubPub(AsyncExceptionAwareQueue).queue_factory,
                      AsyncExceptionAwareQueue)

    async def test_queue_type(self):
        sp = AsyncSubPub(AsyncExceptionAwareQueue)
        q = await sp.subscribe('MelodiesOfLife')
        self.assertIsInstance(q, AsyncExceptionAwareQueue)

    async def test_subscribe_twice(self):
        sp = AsyncSubPub()
        q1 = await sp.subscribe('EyesOnMe')
        q2 = await sp.subscribe('EyesOnMe')
        self.assertIsNot(q1, q2)

    async def test_subscribe_simple(self):
        sp = AsyncSubPub()
        q = await sp.subscribe("Aerith/Theme")
        recv = await sp.publish("Aerith/Theme", 81611)
        self.assertTrue(recv)
        match, data = await q.get()
        self.assertTrue(match)
        self.assertEqual(data, 81611)

    async def test_unsubscribe(self):
        sp = AsyncSubPub()
        topic = "Olofsbäcks Gård"
        q = await sp.subscribe(topic)
        await sp.publish(topic, 81611)
        self.assertTrue(q.get_nowait())
        ok = await sp.unsubscribe(topic)
        self.assertTrue(ok)
        with self.assertRaises(asyncio.QueueEmpty):
            q.get_nowait()

    async def test_unsubscribe_not_subscribed(self):
        sp = AsyncSubPub()
        self.assertFalse(await sp.unsubscribe("Happiness"))

    async def test_unsubscribe_all(self):
        sp = AsyncSubPub()
        self.assertEqual(await sp.unsubscribe_all(), 0)
        await sp.subscribe("Chalmers")
        await sp.subscribe("GU")
        self.assertEqual(await sp.unsubscribe_all(), 0)
        # Keep references
        q1 = await sp.subscribe("Chalmers")
        q2 = await sp.subscribe("GU")
        self.assertEqual(await sp.unsubscribe_all(), 2)

    async def test_unsubscribe_gc(self):
        sp = AsyncSubPub()
        async def f():
            q = await sp.subscribe('Trädgårdsgatan/23')
            recv = await sp.publish('Trädgårdsgatan/23', 404)
            self.assertTrue(recv)
        await f()
        recv = await sp.publish('Trädgårdsgatan/23', 404)
        # q garbage collected => automatic unsubscribe
        self.assertFalse(recv)

    async def test_subscribe_custom_queue(self):
        sp = AsyncSubPub()
        q = asyncio.PriorityQueue()
        q_out = await sp.subscribe('', queue=q)
        self.assertIs(q_out, q)
        q_out = await sp.subscribe('', queue=q)
        self.assertIs(q_out, q)
        q_out = await sp.subscribe('')
        self.assertIsInstance(q_out, asyncio.Queue)
        q_out = await sp.subscribe('', queue=asyncio.LifoQueue())
        self.assertIsInstance(q_out, asyncio.LifoQueue)

    async def test_publish_no_one_cares(self):
        sp = AsyncSubPub()
        recv = await sp.publish('Hans Andersson', 'Water')
        self.assertFalse(recv)

    async def test_publish_retained(self):
        sp = AsyncSubPub()
        topic = 'Sober'
        data_in = 'Nope'
        recv = await sp.publish(topic, data_in, retain=True)
        self.assertFalse(recv)
        q = await sp.subscribe(topic)
        match, data_out = q.get_nowait()
        self.assertEqual(match.re.pattern, topic)
        self.assertIs(data_out, data_in)

    async def test_publish_remove_retained(self):
        sp = AsyncSubPub()
        topic = 'JudgmentDay'
        await sp.publish(topic, 'anything but None', retain=True)
        (await sp.subscribe(topic)).get_nowait()
        await sp.publish(topic, None, retain=True)
        with self.assertRaises(asyncio.QueueEmpty):
            (await sp.subscribe(topic)).get_nowait()

    async def test_publish_block_and_timeout(self):
        sp = AsyncSubPub()
        topic = 'Saturn'
        q = await sp.subscribe(topic, queue=asyncio.Queue(1))
        await sp.publish(topic, 'Pollux')
        with self.assertRaises(asyncio.QueueFull):
            await sp.publish(topic, 'Castor', timeout=0.001)

    async def test_mqtt_style(self):
        sp = AsyncSubPub()
        topic = MqttTopic('Daniel/+/+/+/#')
        q = await sp.subscribe(topic)
        await sp.publish('Daniel/2005/12/18/02:45:00', 'So help me God')
        match, data = await q.get()
        self.assertEqual(match.groups(), ('2005', '12', '18', '02:45:00'))
        self.assertEqual(data, 'So help me God')
        self.assertTrue(await sp.unsubscribe(topic))

    async def test_with_coroutines(self):
        sp = AsyncSubPub()
        q = await sp.subscribe(r'\d+')
        for i in range(10):
            asyncio.create_task(sp.publish(str(i), i))
        self.assertEqual([(await q.get())[1] for _ in range(10)], list(range(10)))


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(subpub))
    return tests

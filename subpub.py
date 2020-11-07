r"""Minimalistic, thread-safe, publish-subscribe API for Python

Welcome to subpub
=================

|PyPI-Versions| |PyPI-Wheel| |PyPI-Downloads| |Read-the-Docs| |License|

**subpub** provides a minimalistic, thread-safe, publish-subscribe API
for single-process Python applications.

* The latest documentation is available on `Read the Docs`_.
* The source code is available on `GitHub`_.

Example
=======

The example below demonstrates basic usage.

..  code-block:: python

    # Create an instance of the message broker
    >>> from subpub import SubPub
    >>> sp = SubPub()

    # Subscribe to a topic (= any string or regular expression).
    # The returned queue `q` is used to retrieve published data:
    >>> q = sp.subscribe(r'/food/(\w+)/order-(\d+)')

    # Publish any data to topic:
    >>> sp.publish('/food/pizza/order-66', "beef pepperoni")
    True

    # Get the published data from the queue:
    >>> match, data = q.get()
    >>> data
    'beef pepperoni'

    # The queue always receives the regexp `match` object as well.
    # It can be used to see how the topic matched and get groups:
    >>> match.groups()
    ('pizza', '66')

    # Get the published topic:
    >>> match.string
    '/food/pizza/order-66'

See test cases in ``test_subpub.py`` for more examples.

Key features
============

- SubPub's methods ``subscribe``, ``unsubscribe``, ``unsubscribe_all`` and
  ``publish`` are **thread-safe**.

- Subscribers use **regular experssions** to filter on topic.

- Subscribers receive published data through **queues**.  (There is no
  built-in mechanism to register callbacks.)

- When an queue is garbage collected, ``unsubscribe`` is executed
  **automatically** (because SubPub only keeps a weak reference to the
  subscribers' queues).

- Publishers can post any **Python object** as message.

- Publishers can use ``retain=True`` to **store** a message (as in MQTT).

Installation
============

From PyPI:

..  code-block:: bash

    $ python3 -m pip install subpub

Reference
=========

See module reference at `Read the Docs`_.

.. _Read the Docs: https://subpub.readthedocs.io/en/latest/
.. _GitHub: https://github.com/Penlect/subpub


.. |PyPI-Versions| image:: https://img.shields.io/pypi/pyversions/subpub.svg
   :target: https://pypi.org/project/subpub

.. |PyPI-Wheel| image:: https://img.shields.io/pypi/wheel/subpub.svg
   :target: https://pypi.org/project/subpub

.. |PyPI-Downloads| image:: https://img.shields.io/pypi/dm/subpub.svg
   :target: https://pypi.org/project/subpub

.. |Read-the-Docs| image:: https://img.shields.io/readthedocs/subpub.svg
   :target: https://subpub.readthedocs.io/en/latest

.. |License| image:: https://img.shields.io/github/license/Penlect/subpub.svg
   :target: https://github.com/Penlect/subpub
"""

# Module metadata
__author__ = 'Daniel Andersson'
__maintainer__ = __author__
__email__ = 'daniel.4ndersson@gmail.com'
__contact__ = __email__
__copyright__ = 'Copyright (c) 2020 Daniel Andersson'
__license__ = 'MIT'
__url__ = 'https://github.com/Penlect/subpub'
__version__ = '0.9.0'

# Built-in
import collections
import queue
import re
import threading
import weakref

Msg = collections.namedtuple('Msg', 'match data')
Msg.__doc__ = """\
Msg is the item sent/received in subscriber's queues.

It carries the regular experssion ``re.Match`` object and the
published ``data`` (data can be any Python object).
"""

class SubPub:
    """A threadsafe message broker with publish/subscribe API.

    This class implements four methods:

    1. ``subscribe`` - listen to topic and retrieve data throuh a queue.
    2. ``unsubscribe`` - stop listening on topic.
    3. ``unsubscribe_all`` - stop listening on all topics.
    4. ``publish`` - post data to subscribers' queues.

    Example::

        >>> sp = SubPub()
        >>> q = sp.subscribe('helloworld')

        >>> sp.publish('helloworld', 123)
        True

        >>> match, data = q.get()
        >>> print(data)
        123

        >>> print(match.string)
        helloworld
    """

    def __init__(self, queue_factory=queue.SimpleQueue, *, timeout=None):
        """Initialization of SubPub instance.

        Example::

            >>> sp = SubPub()
            >>> print(sp)
            SubPub(queue_factory=SimpleQueue, timeout=None)

        :param queue: Default queue factory.  If used, this parameter
            must be a callable which returns an instance of a
            queue-like object (implements get/put with timeout keyword
            argument).  Used whenever a client subscribes unless the
            client provides its own queue.  Defaults to
            ``queue.SimpleQueue``.
        :type queue: Callable

        :param timeout: Default timeout used for subscribe/publish
            when not specified.  Used when putting data in client's
            queues.
        :type timeout: float
        """
        self.timeout = timeout
        self.queue_factory = queue_factory
        self._lock = threading.Lock()
        self._subscriptions = collections.defaultdict(
            weakref.WeakValueDictionary)
        self._retained = dict()

    def __repr__(self):
        return f'{self.__class__.__name__}('\
            f'queue_factory={self.queue_factory.__name__}, '\
            f'timeout={self.timeout!r})'

    def subscribe(self, topic: str, *, queue=None, timeout=None, **args):
        r"""Subscribe to topic and receive published data in queue.

        If topic is a string, it will be compiled to a regular
        expression using ``topic = re.compile(topic)``.

        A custom receiver ``queue`` can be provided.  If not, a new
        one will be created by ``self.queue_factory`` with the
        optional ``**args`` arguments.

        When data is published to a topic which matches the this
        topic, the queue will receive an instance of ``Msg`` which
        contains the regex-match object and the data.

        Subscribe to plain string::

            >>> sp = SubPub()
            >>> q1 = sp.subscribe('helloworld')

        Subscribe to regex::

            >>> q2 = sp.subscribe(r'sensor/\d+/temperature')

        Subscribe to regex with named groups::

            >>> q3 = sp.subscribe(r'worker/(?P<id>\d+)/(?P<status>done|error)')

        The ``MqttTopic`` class can be used to build topics using MQTT
        syntax for wildcards::

            >>> t = MqttTopic('sensor/+/temperature/#')
            >>> t.as_regexp()
            re.compile('sensor/([^/]*)/temperature/(.*)$')
            >>> q4 = sp.subscribe(t)

        :param topic: Regular expression that match topics of
            interest.  If a string, the topic will be compiled to a
            regular expression with ``topic = re.compile(topic)``.
        :type topic: str or ``re.Pattern``

        :param queue: An instance of a queue-like object (implements
            get/put with timeout keyword argument).  Will be used as
            receiver queue for published data.  If used not, a new one
            will be created by ``self.queue_factory`` with the
            optional ``**args`` arguments.
        :type queue: Queue like object.

        :param timeout: Timeout when putting retained data in
            subscriber's queue.  The behavior is client specific and
            depends what type of queue the client uses.  If timeout is
            a positive number, and the default queue
            ``queue.SimpleQueue`` is used, the publish blocks at most
            timeout seconds and raises the ``queue.Full`` exception if
            no free slot was available within that time.  If timeout
            is ``None``, block if necessary until a free slot is
            available.  Defaults to ``self.timeout``.
        :type timeout: float

        :return: Queue instance which will receive published data
                 whenever the published topic matches the subscribers
                 regex-topic.  The data is wrapped together with the
                 ``re.Match`` object in an instance of ``Msg``.
        :rtype: Queue-like object.
        """
        if timeout is None:
            timeout = self.timeout
        if isinstance(topic, str):
            topic = re.compile(topic)
        elif isinstance(topic, MqttTopic):
            topic = topic.as_regexp()
        t = threading.current_thread()
        with self._lock:
            q = queue or self.queue_factory(**args)
            self._subscriptions[t][topic] = q
            for retained_topic, retained_data in self._retained.items():
                match = topic.match(retained_topic)
                if match:
                    q.put(Msg(match, retained_data), timeout=timeout)
            return q

    def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe to topic.

        :param topic: Same as for ``subscribe``.
        :type topic: str or ``re.Pattern``

        :return: Returns False if the caller wasn't actually
                 subscribed, otherwise True.
        :rtype: int
        """
        if isinstance(topic, str):
            topic = re.compile(topic)
        elif isinstance(topic, MqttTopic):
            topic = topic.as_regexp()
        t = threading.current_thread()
        with self._lock:
            try:
                del self._subscriptions[t][topic]
            except KeyError:
                return False
            return True

    def unsubscribe_all(self) -> int:
        """Unsubscribe to all clients

        :return: Returns the number of topics that got unsubscribed.
        :rtype: int
        """
        t = threading.current_thread()
        with self._lock:
            try:
                return len(self._subscriptions.pop(t, list()))
            except KeyError:
                return 0

    def publish(self, topic: str, data=None, *, retain=False, timeout=None):
        """Publish data to topic.

        This method loops through the clients subscribed regex-topics
        and searches for a match on ``topic``.  If there is a match,
        the ``re.Match`` and ``data`` objects will be wrapped in a
        ``Msg``, which then will be put in the client's subscription
        queue.

        Examples::

            >>> sp = SubPub()
            >>> sp.publish('helloworld', data='Hi, there!')
            False
            >>> sp.publish('helloworld', 'Hi, new client', retain=True)
            False

        The boolean returned, in this case ``False``, indicates if it
        existed at least one client that received the data.

        :param topic: Topic string the data will be published to.
        :type topic: str

        :param data: Data to be published.
        :type data: any Python object

        :param retain: If true, the published data will be remembered.
            Each client that subscribes to a regex-topic matching this
            topic, will immediately receive the retained data when
            they subscribe.  To stop this behavior, make a publish to
            the same topic with data ``None`` and retain ``True``.
        :type retain: bool

        :param timeout: Timeout when putting published data in
            subscribers' queues.  The behavior is client specific and
            depends what type of queue the client uses.  If timeout is
            a positive number, and the default queue
            ``queue.SimpleQueue`` is used, the publish blocks at most
            timeout seconds and raises the ``queue.Full`` exception if
            no free slot was available within that time.  If timeout
            is ``None``, block if necessary until a free slot is
            available.  Defaults to ``self.timeout``.
        :type timeout: float

        :return: Returns ``True`` if a subscribed client queue existed
                 and the data was successfully put in that queue.  If
                 no receiver was found, return ``False``.
        :rtype: bool
        """
        if timeout is None:
            timeout = self.timeout
        with self._lock:
            if retain:
                if data is None:
                    try:
                        del self._retained[topic]
                    except KeyError:
                        pass
                else:
                    self._retained[topic] = data
            remove_us = set()
            did_put = False
            for t, sub in self._subscriptions.items():
                if not sub:
                    # All references are gone.
                    remove_us.add(t)
                    continue
                for topic_regex, q in sub.items():
                    match = topic_regex.match(topic)
                    if match:
                        q.put(Msg(match, data), timeout=timeout)
                        did_put = True
            for t in remove_us:
                del self._subscriptions[t]
            return did_put


class MqttTopic(collections.UserString):
    """String which represents a topic in MQTT format.

    Instead of normal Python regex, the MQTT wildcards, '+' and '#',
    can be used instead.

    An instance of MqttTopic can be used as topic argument to the
    SubPub methods.  It will be converted to a regular expression
    automatically::

        >>> MqttTopic('room/3/sensor/+/temperature/#').as_regexp()
        re.compile('room/3/sensor/([^/]*)/temperature/(.*)$')
    """
    def as_regexp(self, flags=0):
        """Replace MQTT wildcards and return regular expression."""
        pattern = self.data.strip()
        pattern = re.sub(r'(?<=/)\+(?=/)', '([^/]*)', pattern)
        pattern = re.sub(r'#$', '(.*)$', pattern)
        return re.compile(pattern, flags)


class ExceptionAwareQueue(queue.SimpleQueue):
    """Raise exception instances when received in queue.

    This is useful if you want to publish an exception instance to a
    client and have it raised automatically when the client receives
    it by calling ``.get()``.
    """

    def get(self, block=True, timeout=None):
        """If item retrived is an Exception instance - raise it."""
        match, data = super().get(block, timeout)
        # Prepend the match object to exception args.
        # Note: Exception *classes* won't be catched here,
        #       only instances.
        if isinstance(data, Exception):
            data.args = (match, *data.args)
            raise data
        return match, data

    def get_nowait(self):
        """Same as ``get()`` but with ``block=False``."""
        self.get(block=False)

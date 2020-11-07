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
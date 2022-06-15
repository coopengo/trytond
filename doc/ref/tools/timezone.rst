.. _ref-tools-timezone:
.. module:: trytond.tools.timezone

timezone
========

.. class:: ZoneInfo(key)

   A class representing a IANA time zone specified by the string ``key``.

.. function:: available_timezones()

   Get a sorted list of all the valid IANA keys available.

.. attribute:: UTC

   The UTC ZoneInfo instance.

.. attribute:: SERVER

   A ZoneInfo instance based on the server timezone.

   Tryton tests the environment variables ``TRYTOND_TZ`` and ``TZ`` in this
   order to select to IANA key used.
   If they are both empty, it defaults to ``UTC``.

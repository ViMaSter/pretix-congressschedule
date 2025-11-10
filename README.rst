pretix-congressschedule
=======================

This is a plugin for `pretix`_. It generates a `c3voc-schema`_ compatible `schedule.xml` endpoint for events.

Accessing schedule.xml
----------------------

1. Create an `event-series`_ in pretix; a singular event or non-event shop will not work, as products won't have required start and end times associated with them

2. Visit `/api/v1/event/{organizationSlug}/{eventSlug}/schedule.xml` and replace `{organizationSlug}` and `{eventSlug}` with the respective slugs

3. Receive either a 200 status code with an XML document adhering to `schedule.xml.xsd`_ or a 400 error code with additional information inside `<error>`

   
Development setup
^^^^^^^^^^^^^^^^^

1. Make sure that you have a working `pretix development setup`_.

2. Clone this repository, eg to ``local/pretix-congressschedule``.

3. Activate the virtual environment you use for pretix development.

4. Execute ``pip install -e .`` within this directory to register this application with pretix's plugin registry.

5. Execute ``make`` within this directory to compile translations.

6. Restart your local pretix server. You can now use the plugin from this repository for your events by enabling it in
   the 'plugins' tab in the settings.


License
-------

Copyright 2025 Vincent 'ViMaSter' Mahnke

Released under the terms of the Apache License 2.0



.. _pretix: https://github.com/pretix/pretix
.. _pretix development setup: https://docs.pretix.eu/en/latest/development/setup.html
.. _c3voc-schema: https://c3voc.de/wiki/schedule#schedule_xml
.. _schedule.xml.xsd: https://c3voc.de/schedule/schema.xsd
.. _event-series: https://docs.pretix.eu/guides/event-series/?h=dates#how-to-create-an-event-series

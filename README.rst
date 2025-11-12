pretix-congressschedule
=======================

This is a plugin for `pretix`_. It generates a `c3voc-schema`_ compatible `schedule.xml` endpoint and hackertours-compatible markdown table for event-series.
To access the endpoints without logging in, generate an `API token`_ first.

Subevent language field
-----------------------

To determine a subevent's language, this plugin adds a language dropdown selector.
Default: `deen` (multi-lingual of German and English)

Accessing schedule.xml
----------------------

1. Create an `event-series`_ in pretix; a singular event or non-event shop will not work, as products won't have required start and end times associated with them

2. Visit `/api/v1/event/{organizationSlug}/{eventSlug}/schedule.xml` and replace `{organizationSlug}` and `{eventSlug}` with the respective slugs

3. Receive either a 200 status code with an XML document adhering to `schedule.xml.xsd`_ or a 400 error code with additional information inside `<error>`


Using schedule.md
----------------------

1. Create an `event-series`_ in pretix; a singular event or non-event shop will not work, as products won't have required start and end times associated with them

2. Visit `/api/v1/event/{organizationSlug}/{eventSlug}/schedule.md` and replace `{organizationSlug}` and `{eventSlug}` with the respective slugs

3. Receive either a 200 status code with a Markdown document containing a table used for hackertours.hamburg.ccc.de or a 400 error code with additional information inside `<error>`

4. To embed this into Hugo, use the following syntax:

```hugo
{{ $url := "https://{prefixInstanceRoot}/api/v1/event/{organizationSlug}/{eventSlug}/schedule.md" }}
{{ $opts := dict
   "headers" (dict "Authorization" "Token 6r5waszrj1qbdwqbewbmmk7h46ilocmyfh3e2gxqa9oj52vijmzo1dppk39t3hkl")
}}
{{ with try (resources.GetRemote $url $opts) }}
   {{ with .Err }}
      {{ errorf "%s" . }}
   {{ else with .Value }}
      {{ .Content | safeHTML }}
   {{ end }}
{{ end }}
```

   
Development setup
^^^^^^^^^^^^^^^^^

1. Make sure that you have a working `pretix development setup`_.

2. Clone this repository, eg to ``local/pretix-congressschedule``.

3. Activate the virtual environment you use for pretix development.

4. Execute ``pip install -e .`` within this directory to register this application with pretix's plugin registry.

5. Execute ``make`` within this directory to compile translations.

6. Restart your local pretix server. You can now use the plugin from this repository for your events by enabling it in
   the 'plugins' tab in the settings.


Changelog
---------

1.1.0
~~~~~

- Add subevent-level "Language" field and use it to emit ``<language>`` per subevent (defaults to ``none``).

1.0.0
~~~~~

- Initial release


License
-------

Copyright 2025 Vincent 'ViMaSter' Mahnke

Released under the terms of the Apache License 2.0



.. _pretix: https://github.com/pretix/pretix
.. _pretix development setup: https://docs.pretix.eu/en/latest/development/setup.html
.. _API token: https://docs.pretix.eu/dev/api/tokenauth.html#obtaining-an-api-token
.. _c3voc-schema: https://c3voc.de/wiki/schedule#schedule_xml
.. _schedule.xml.xsd: https://c3voc.de/schedule/schema.xsd
.. _event-series: https://docs.pretix.eu/guides/event-series/?h=dates#how-to-create-an-event-series

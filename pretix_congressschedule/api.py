from django.http import HttpResponse
from rest_framework import views
from pretix.base.models import Event, SubEvent
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import timedelta
import uuid
import re

from . import __version__

class CongressScheduleView(views.APIView):
    def get(self, request, organizer, event, *args, **kwargs):
        try:
            ev = Event.objects.get(organizer__slug=organizer, slug=event)
        except Event.DoesNotExist:
            return HttpResponse(b'<?xml version="1.0"?><error>Event not found</error>', status=404, content_type='application/xml')

        if not ev.has_subevents:
            return HttpResponse(
                b'<?xml version="1.0"?><error>Event is not an event-series: https://docs.pretix.eu/guides/event-series/?h=dates#how-to-create-an-event-series</error>',
                status=400,
                content_type='application/xml'
            )

        subs = SubEvent.objects.filter(event=ev).order_by('date_from')

        root = ET.Element('schedule')

        gen = ET.SubElement(root, 'generator')
        gen.set('name', 'pretix-congressschedule')
        gen.set('version', __version__)

        try:
            feed_url = request.build_absolute_uri()
            ET.SubElement(root, 'url').text = feed_url
        except Exception:
            pass

        # Version string – keep simple and stable per event
        ET.SubElement(root, 'version').text = f"{ev.slug}-v1"

        conf = ET.SubElement(root, 'conference')
        conf_title = ev.name.localize(ev.settings.locale) if hasattr(ev.name, 'localize') else str(ev.name)
        ET.SubElement(conf, 'title').text = conf_title or str(ev.slug)
        acronym = f"{organizer}_{event}".lower()
        ET.SubElement(conf, 'acronym').text = acronym

        # start/end/days based on subevents if available, else fall back to event
        all_starts = [se.date_from for se in subs if se.date_from]
        all_ends = [se.date_to for se in subs if se.date_to]

        if all_starts:
            ET.SubElement(conf, 'start').text = min(all_starts).isoformat()
        if all_ends:
            ET.SubElement(conf, 'end').text = max(all_ends).isoformat()

        # days count – unique calendar days from subevents
        unique_days = sorted({(se.date_from.date() if se.date_from else None) for se in subs} - {None})
        if unique_days:
            ET.SubElement(conf, 'days').text = str(len(unique_days))

        # time zone name – try Event.timezone or settings
        tz_name = getattr(ev, 'timezone', None) or getattr(ev.settings, 'timezone', None)
        if tz_name:
            tz_text = tz_name if isinstance(tz_name, str) else str(tz_name)
            ET.SubElement(conf, 'time_zone_name').text = tz_text

        # Group subevents into days and rooms
        # days: {date -> {room_name -> [subevents]}}
        days: dict = defaultdict(lambda: defaultdict(list))

        def get_room_name(se):
            # Try SubEvent.location if present, else fallback to `Main`
            loc = getattr(se, 'location', None)
            if hasattr(loc, 'localize'):
                try:
                    txt = loc.localize(ev.settings.locale)
                except Exception:
                    txt = str(loc)
            else:
                txt = str(loc) if loc else ''
            return (txt or 'Main').strip() or 'Main'

        for se in subs:
            if not se.date_from:
                # Skip entries without a start
                continue
            day_key = se.date_from.date()
            room = get_room_name(se)
            days[day_key][room].append(se)

        # Emit <day> elements in chronological order
        for day_index, (day_date, rooms) in enumerate(sorted(days.items()), start=1):
            # Compute day start/end from all events this day
            starts = [se.date_from for r in rooms.values() for se in r if se.date_from]
            ends = [se.date_to for r in rooms.values() for se in r if se.date_to]
            day_start = min(starts) if starts else None
            # If end is missing for any, approximate using +0 duration => start
            if ends:
                day_end = max(ends)
            else:
                day_end = (day_start + timedelta(minutes=0)) if day_start else None

            day_el = ET.SubElement(root, 'day')
            if day_date:
                day_el.set('date', day_date.isoformat())
            if day_start:
                day_el.set('start', day_start.isoformat())
            if day_end:
                day_el.set('end', day_end.isoformat())
            day_el.set('index', str(day_index))

            # Emit <room> containers
            for room_name, events_in_room in sorted(rooms.items(), key=lambda x: x[0].lower()):
                room_el = ET.SubElement(day_el, 'room')
                room_el.set('name', room_name)
                # Optional guid on room – stable UUID5 based on names
                room_el.set('guid', str(uuid.uuid5(uuid.NAMESPACE_DNS, f"room:{organizer}:{event}:{room_name}")))

                # Emit each <event> in chronological order within the room
                for se in sorted(events_in_room, key=lambda s: s.date_from or 0):
                    ev_el = ET.SubElement(room_el, 'event')
                    ev_el.set('id', str(se.pk))
                    ev_el.set('guid', str(uuid.uuid5(uuid.NAMESPACE_DNS, f"subevent:{ev.pk}:{se.pk}")))

                    # Helper: localize strings
                    def _localize(val):
                        if hasattr(val, 'localize'):
                            try:
                                return val.localize(ev.settings.locale)
                            except Exception:
                                return str(val)
                        return str(val) if val is not None else ''

                    # Required children according to schema
                    ET.SubElement(ev_el, 'room').text = room_name
                    title = _localize(se.name)
                    ET.SubElement(ev_el, 'title').text = title
                    ET.SubElement(ev_el, 'subtitle').text = ''
                    ET.SubElement(ev_el, 'type').text = 'subevent'

                    # date (full datetime with TZ)
                    if se.date_from:
                        ET.SubElement(ev_el, 'date').text = se.date_from.isoformat()

                    # start (HH:MM or HH:MM:SS)
                    if se.date_from:
                        ET.SubElement(ev_el, 'start').text = se.date_from.strftime('%H:%M')

                    # duration from date_to - date_from
                    dur_txt = '00:00'
                    if se.date_from and se.date_to and se.date_to >= se.date_from:
                        delta: timedelta = se.date_to - se.date_from
                        total_seconds = int(delta.total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        # prefer HH:MM if no seconds, else HH:MM:SS
                        if seconds == 0:
                            dur_txt = f"{hours:02d}:{minutes:02d}"
                        else:
                            dur_txt = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    ET.SubElement(ev_el, 'duration').text = dur_txt

                    ET.SubElement(ev_el, 'abstract').text = ''

                    # slug (pattern: "[a-z0-9_]{4,}-[a-z0-9\-_]{4,}")
                    def slugify(text: str) -> str:
                        text = (text or '').lower()
                        text = re.sub(r'\s+', '-', text)
                        text = re.sub(r'[^a-z0-9\-_]', '', text)
                        text = text.strip('-_')
                        return text or 'item'

                    base = f"{organizer}_{event}".lower()
                    second = slugify(title)
                    if len(second) < 4:
                        second = f"{second}-{se.pk}"
                    ET.SubElement(ev_el, 'slug').text = f"{base}-{second}"

                    # track – use room name as a simple track assignment
                    ET.SubElement(ev_el, 'track').text = slugify(room_name) or 'general'

                    # Optional elements: keep minimal but include language if available
                    lang = getattr(ev.settings, 'locale', None)
                    if lang:
                        ET.SubElement(ev_el, 'language').text = str(lang)

                    # Leave optional complex children (persons, recording, links, attachments) empty for now

        xml_bytes = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        return HttpResponse(xml_bytes, content_type='application/xml')
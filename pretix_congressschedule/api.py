from django.http import HttpResponse
from rest_framework import views
from pretix.base.models import Event, SubEvent
try:
    from pretix.base.models import SubEventMetaValue
except Exception:  # pragma: no cover
    SubEventMetaValue = None
from collections import defaultdict
import uuid
import re

from . import __version__
import json

class CongressScheduleJSONView(views.APIView):
    def get(self, request, organizer, event):

        try:
            ev = Event.objects.get(organizer__slug=organizer, slug=event)
        except Event.DoesNotExist:
            return HttpResponse(
                json.dumps({"error": "Event not found"}),
                status=404,
                content_type='application/json; charset=utf-8'
            )

        if not ev.has_subevents:
            return HttpResponse(
                json.dumps({"error": "Event is not an event-series: https://docs.pretix.eu/guides/event-series/?h=dates#how-to-create-an-event-series"}),
                status=400,
                content_type='application/json; charset=utf-8'
            )

        subs = SubEvent.objects.filter(event=ev).order_by('date_from')

        schedule = {
            "$schema": "https://c3voc.de/schedule/schema.json",
            "schedule": {
                "generator": {"name": "voc/schedule/hackertours", "version": __version__},
                "version": f"{ev.slug}-v1",
                "conference": {
                    "acronym": f"{organizer}_{event}".lower(),
                    "title": (ev.name.localize(ev.settings.locale) if hasattr(ev.name, 'localize') else str(ev.name)) or str(ev.slug),
                    "start": None,
                    "end": None,
                    "daysCount": None,
                    "timeslot_duration": "00:15",
                    "time_zone_name": "Europe/Berlin",
                    "rooms": [
                        {
                        "name": "Hackertours",
                        "guid": "aa56c6c6-7dbc-4f73-b189-b8ee2245b0c3"
                        }
                    ],
                    "days": []
                }
            }
        }

        all_starts = [se.date_from for se in subs if se.date_from]
        all_ends = [se.date_to for se in subs if se.date_to]
        if all_starts:
            schedule["schedule"]["conference"]["start"] = min(all_starts).isoformat()
        if all_ends:
            schedule["schedule"]["conference"]["end"] = max(all_ends).isoformat()

        unique_days = sorted({(se.date_from.date() if se.date_from else None) for se in subs} - {None})
        if unique_days:
            schedule["schedule"]["conference"]["daysCount"] = len(unique_days)

        tz_name = getattr(ev, 'timezone', None) or getattr(ev.settings, 'timezone', None)
        if tz_name:
            schedule["schedule"]["conference"]["time_zone_name"] = tz_name if isinstance(tz_name, str) else str(tz_name)

        days = defaultdict(lambda: defaultdict(list))

        def get_room_name(se):
            loc = getattr(se, 'location', None)
            if hasattr(loc, 'localize'):
                try:
                    txt = loc.localize(ev.settings.locale)
                except Exception:
                    txt = str(loc)
            else:
                txt = str(loc) if loc else ''
            return (txt or 'Hackertours').strip() or 'Hackertours'

        for se in subs:
            if not se.date_from:
                continue
            day_key = se.date_from.date()
            room = get_room_name(se)
            days[day_key][room].append(se)

        def _localize(val):
            if hasattr(val, 'localize'):
                try:
                    return val.localize(ev.settings.locale)
                except Exception:
                    return str(val)
            return str(val) if val is not None else ''

        def slugify(text: str) -> str:
            text = (text or '').lower()
            text = re.sub(r'\s+', '-', text)
            text = re.sub(r'[^a-z0-9\-_]', '', text)
            text = text.strip('-_')
            return text or 'item'

        def _get_language(subevent: SubEvent) -> str:
            if SubEventMetaValue is not None:
                try:
                    v = (
                        SubEventMetaValue.objects
                        .filter(subevent=subevent, key='congressschedule_language')
                        .values_list('value', flat=True)
                        .first()
                    )
                    return (v or 'deen').strip() or 'deen'
                except Exception:
                    pass
            md = getattr(subevent, 'meta_data', None) or {}
            if isinstance(md, dict) and 'congressschedule_language' in md:
                return (md.get('congressschedule_language') or 'deen')
            se_settings = getattr(subevent, 'settings', None)
            try:
                return se_settings.get('congressschedule_language', 'deen') if se_settings is not None else 'deen'
            except Exception:
                return 'deen'
            
        def _get_websiteDE(subevent: SubEvent) -> str:
            if SubEventMetaValue is not None:
                try:
                    v = (
                        SubEventMetaValue.objects
                        .filter(subevent=subevent, key='congressschedule_website_de')
                        .values_list('value', flat=True)
                        .first()
                    )
                    return (v or '').strip()
                except Exception:
                    pass
            md = getattr(subevent, 'meta_data', None) or {}
            if isinstance(md, dict) and 'congressschedule_website_de' in md:
                return (md.get('congressschedule_website_de') or '').strip()
            se_settings = getattr(subevent, 'settings', None)
            try:
                return se_settings.get('congressschedule_website_de', '') if se_settings is not None else ''
            except Exception:
                return ''
            
        def _get_websiteEN(subevent: SubEvent) -> str:
            if SubEventMetaValue is not None:
                try:
                    v = (
                        SubEventMetaValue.objects
                        .filter(subevent=subevent, key='congressschedule_website_en')
                        .values_list('value', flat=True)
                        .first()
                    )
                    return (v or '').strip()
                except Exception:
                    pass
            md = getattr(subevent, 'meta_data', None) or {}
            if isinstance(md, dict) and 'congressschedule_website_en' in md:
                return (md.get('congressschedule_website_en') or '').strip()
            se_settings = getattr(subevent, 'settings', None)
            try:
                return se_settings.get('congressschedule_website_en', '') if se_settings is not None else ''
            except Exception:
                return ''

        for day_index, (day_date, rooms) in enumerate(sorted(days.items()), start=1):
            starts = [se.date_from for r in rooms.values() for se in r if se.date_from]
            ends = [se.date_to for r in rooms.values() for se in r if se.date_to]
            day_start = min(starts).isoformat() if starts else None
            day_end = (max(ends).isoformat() if ends else (min(starts).isoformat() if starts else None))

            day_obj = {
                "index": day_index,
                "date": day_date.isoformat() if day_date else None,
                "day_start": day_start,
                "day_end": day_end,
                "rooms": []
            }

            day_obj["rooms"] = {}

            for room_name, events_in_room in sorted(rooms.items(), key=lambda x: x[0].lower()):
                room_events = []

                for se in sorted(events_in_room, key=lambda s: s.date_from or 0):
                    dur_txt = '00:00'
                    if se.date_from and se.date_to and se.date_to >= se.date_from:
                        delta = se.date_to - se.date_from
                        total_seconds = int(delta.total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        dur_txt = f"{hours:02d}:{minutes:02d}" if seconds == 0 else f"{hours:02d}:{minutes:02d}:{seconds:02d}"

                    title = _localize(se.name)
                    base = f"{organizer}_{event}".lower()
                    second = slugify(title)
                    if len(second) < 4:
                        second = f"{second}-{se.pk}"

                    language = _get_language(se)
                    websiteDE = _get_websiteDE(se)
                    websiteEN = _get_websiteEN(se)

                    ev_obj = {
                        "id": se.pk,
                        "guid": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"subevent:{ev.pk}:{se.pk}")),
                        "date": se.date_from.isoformat() if se.date_from else None,
                        "start": se.date_from.strftime('%H:%M') if se.date_from else None,
                        "duration": dur_txt,
                        "room": room_name,
                        "slug": f"{base}-{second}",
                        "url": websiteDE if language == "de" else websiteEN,
                        "title": title,
                        "subtitle": "",
                        "track": "Hackertours",
                        "type": "Tour",
                        "language": str(language or "de, en"),
                        "abstract": se.frontpage_text.localize(ev.settings.locale) if hasattr(se.frontpage_text, 'localize') else str(se.frontpage_text) if se.frontpage_text else "",
                        "persons": [],
                        "links": []
                    }

                    if websiteDE:
                        ev_obj["links"].append({
                            "url": str(websiteDE),
                            "title": title + " (DE)",
                        })

                    if websiteEN:
                        ev_obj["links"].append({
                            "url": str(websiteEN),
                            "title": title + " (EN)",
                        })
                        
                    room_events.append(ev_obj)

                day_obj["rooms"][room_name] = room_events

            schedule["schedule"]["conference"]["days"].append(day_obj)

        return HttpResponse(
            json.dumps(schedule, ensure_ascii=False),
            content_type='application/json; charset=utf-8'
        )

class HackertoursMarkdownView(views.APIView):
    def get(self, request, organizer, event, *args, **kwargs):
        try:
            ev = Event.objects.get(organizer__slug=organizer, slug=event)
        except Event.DoesNotExist:
            return HttpResponse("Event not found", status=404, content_type='text/plain; charset=utf-8')

        if not ev.has_subevents:
            return HttpResponse(
                'Event is not an event-series: https://docs.pretix.eu/guides/event-series/?h=dates#how-to-create-an-event-series',
                status=400,
                content_type='text/plain; charset=utf-8'
            )

        subs = SubEvent.objects.filter(event=ev).order_by('date_from')

        # Helper: localize strings
        def _localize(val):
            if hasattr(val, 'localize'):
                try:
                    return val.localize(ev.settings.locale)
                except Exception:
                    return str(val)
            return str(val) if val is not None else ''

        # Slugify for links
        def slugify(text: str) -> str:
            text = (text or '').lower()
            text = re.sub(r'\s+', '-', text)
            text = re.sub(r'[^a-z0-9\-_]', '', text)
            text = text.strip('-_')
            return text or 'item'

        # Build day -> events map and gather all start times
        days = defaultdict(list)  # {date -> [SubEvent]}
        start_dts = []
        for se in subs:
            if not se.date_from:
                continue
            days[se.date_from.date()].append(se)
            start_dts.append(se.date_from)

        if not start_dts:
            return HttpResponse("No subevents found", content_type='text/plain; charset=utf-8')

        unique_days = sorted(days.keys())

        # Build time slots (minutes since midnight)
        def to_minutes(dt):
            return dt.hour * 60 + dt.minute

        event_minutes = {to_minutes(dt) for dt in start_dts}
        min_hour = min(dt.hour for dt in start_dts)
        max_hour = max(dt.hour for dt in start_dts)
        hour_minutes = {h * 60 for h in range(min_hour, max_hour + 1)}
        all_minutes = sorted(event_minutes | hour_minutes)

        # For each day, map minute -> list of markdown items
        day_slots = {d: defaultdict(list) for d in unique_days}
        for d in unique_days:
            for se in days[d]:
                title = _localize(se.name)
                tmin = to_minutes(se.date_from)
                hhmm = se.date_from.strftime('%H:%M')
                v = (
                    SubEventMetaValue.objects
                    .filter(subevent=se, property__name='congressschedule_language')
                    .values_list('value', flat=True)
                    .first()
                )
                lang = (v or 'deen').strip() or 'deen'
                link = f"./{slugify(title)}/"
                md_item = f"{hhmm} [{title}]({link}) {{< lang {lang} >}}"
                day_slots[d][tmin].append(md_item)

        # Build markdown table
        lines = []
        # Header
        header = ["Zeit"] + [f"Tag {i} ({d.strftime('%d.%m.')})" for i, d in enumerate(unique_days, start=1)]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * len(header)) + "|")

        # Rows
        for m in all_minutes:
            is_full_hour = (m % 60) == 0
            zeit_label = f"{m // 60:02d}:{m % 60:02d}" if is_full_hour else ""
            row = [zeit_label]
            for d in unique_days:
                items = day_slots[d].get(m, [])
                if items:
                    cell = "  ".join(items)
                else:
                    cell = "-" if is_full_hour else ""
                row.append(cell)
            lines.append("| " + " | ".join(row) + " |")

        md = "\n".join(lines) + "\n"
        return HttpResponse(md.encode('utf-8'), content_type='text/markdown; charset=utf-8')

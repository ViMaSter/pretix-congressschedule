from django import forms
from django.utils.translation import gettext_lazy as _
try:
	# Available in pretix runtime
	from pretix.base.models import SubEventMetaValue
except Exception:  # pragma: no cover - during docs build or without pretix
	SubEventMetaValue = None


class SubEventHackertoursForm(forms.Form):
	contactAtVenueName = forms.CharField(
		label=_("Name of contact at Venue (internal)"),
		required=False,
		help_text=_("Prefered name of the contact person at the venue, not the Hackertours-internal team member organizing the tour. (This is never shown publicly.)"),
	)
	contactAtVenuePhoneNumber = forms.CharField(
		label=_("Phone Number of contact at Venue (internal)"),
		required=False,
		help_text=_("Phone number of the contact person at the venue. Prefer mobile numbers over landlines. (This is never shown publicly.)"),
	)
	language = forms.ChoiceField(
		label=_("Language"),
		required=False,
		help_text=_("Select the language for this tour."),
		choices=[
			('deen', _("Bilingual")),
			('de', _("German")),
			('en', _("English")),
		],
	)
	website_en = forms.URLField(
		label=_("Website (English)"),
		required=False,
		help_text=_("Link to the English tour details on https://hackertours.hamburg.ccc.de/en/"),
	)
	website_de = forms.URLField(
		label=_("Website (German)"),
		required=False,
		help_text=_("Link to the German tour details on https://hackertours.hamburg.ccc.de/de/"),
	)

	def __init__(self, *args, **kwargs):
		self.event = kwargs.pop('event')
		self.subevent = kwargs.pop('subevent', None)
		super().__init__(*args, **kwargs)
		# Pre-fill from subevent meta if available
		if self.subevent:
			contactAtVenueNameValue = (
				SubEventMetaValue.objects
				.filter(subevent=self.subevent, property__name='congressschedule_contact_at_venue_name')
				.values_list('value', flat=True)
				.first()
			)
			self.fields['contactAtVenueName'].initial = contactAtVenueNameValue or ''
			contactAtVenuePhoneNumberValue = (
				SubEventMetaValue.objects
				.filter(subevent=self.subevent, property__name='congressschedule_contact_at_venue_phone_number')
				.values_list('value', flat=True)
				.first()
			)
			self.fields['contactAtVenuePhoneNumber'].initial = contactAtVenuePhoneNumberValue or ''

			languageValue = (
				SubEventMetaValue.objects
				.filter(subevent=self.subevent, property__name='congressschedule_language')
				.values_list('value', flat=True)
				.first()
			)
			self.fields['language'].initial = languageValue or ''

			websiteENValue = (
				SubEventMetaValue.objects
				.filter(subevent=self.subevent, property__name='congressschedule_website_en')
				.values_list('value', flat=True)
				.first()
			)
			self.fields['website_en'].initial = websiteENValue or ''
			
			websiteDEValue = (
				SubEventMetaValue.objects
				.filter(subevent=self.subevent, property__name='congressschedule_website_de')
				.values_list('value', flat=True)
				.first()
			)
			self.fields['website_de'].initial = websiteDEValue or ''
		elif self.subevent and hasattr(self.subevent, 'settings'):
			# Fallback (older pretix): might be event-wide, keep as last resort
			self.fields['contact_at_venue_name'].initial = self.subevent.settings.get('congressschedule_contact_at_venue_name', '')
			self.fields['contact_at_venue_phone_number'].initial = self.subevent.settings.get('congressschedule_contact_at_venue_phone_number', '')
			self.fields['language'].initial = "deen"
			self.fields['website_en'].initial = ""
			self.fields['website_de'].initial = ""

	@property
	def title(self):
		return _("Hackertours Settings")

	def save(self):
		if not self.subevent:
			return	
		# Persist as real subevent meta value so it's scoped per subevent
		from pretix.base.models import EventMetaProperty

		contactAtVenueNameValue = (self.cleaned_data.get('contactAtVenueName') or '').strip()
		contactAtVenueNamePropertyObj, _ = EventMetaProperty.objects.get_or_create(
			name='congressschedule_contact_at_venue_name',
			defaults={'default': '', 'organizer': self.event.organizer}
		)
		SubEventMetaValue.objects.update_or_create(
			subevent=self.subevent,
			property=contactAtVenueNamePropertyObj,
			defaults={'value': contactAtVenueNameValue},
		)

		contactAtVenuePhoneNumberValue = (self.cleaned_data.get('contactAtVenuePhoneNumber') or '').strip()
		contactAtVenuePhoneNumberPropertyObj, _ = EventMetaProperty.objects.get_or_create(
			name='congressschedule_contact_at_venue_phone_number',
			defaults={'default': '', 'organizer': self.event.organizer}
		)
		SubEventMetaValue.objects.update_or_create(
			subevent=self.subevent,
			property=contactAtVenuePhoneNumberPropertyObj,
			defaults={'value': contactAtVenuePhoneNumberValue},
		)

		languageValue = (self.cleaned_data.get('language') or '').strip() or 'deen'
		language_property_obj, _ = EventMetaProperty.objects.get_or_create(
			name='congressschedule_language',
			defaults={'default': '', 'organizer': self.event.organizer}
		)
		SubEventMetaValue.objects.update_or_create(
			subevent=self.subevent,
			property=language_property_obj,
			defaults={'value': languageValue},
		)

		websiteENValue = (self.cleaned_data.get('website_en') or '').strip()
		website_en_property_obj, _ = EventMetaProperty.objects.get_or_create(
			name='congressschedule_website_en',
			defaults={'default': '', 'organizer': self.event.organizer}
		)
		SubEventMetaValue.objects.update_or_create(
			subevent=self.subevent,
			property=website_en_property_obj,
			defaults={'value': websiteENValue},
		)

		websiteDEValue = (self.cleaned_data.get('website_de') or '').strip()	
		website_de_property_obj, _ = EventMetaProperty.objects.get_or_create(
			name='congressschedule_website_de',
			defaults={'default': '', 'organizer': self.event.organizer}
		)
		SubEventMetaValue.objects.update_or_create(
			subevent=self.subevent,
			property=website_de_property_obj,
			defaults={'value': websiteDEValue},
		)


def subevent_hackertours_forms(sender, request, subevent, **kwargs):
	# Provide our additional subevent form
	import logging
	logger = logging.getLogger(__name__)
	logger.debug("Providing congressschedule subevent form for event %s, subevent %s", sender.slug, getattr(subevent, 'name', 'no-subevent'))
	form = SubEventHackertoursForm(
		data=request.POST if request.method == 'POST' else None,
		event=sender,
		subevent=subevent,
		prefix='congressschedule',
	)
	return form


def connect_signals():
	try:
		from pretix.control import signals as control_signals

		control_signals.subevent_forms.connect(subevent_hackertours_forms, dispatch_uid='pretix_congressschedule_subevent_hackertours')
	except Exception:
		# Pretix not fully loaded in some contexts (e.g., docs build)
		pass


# Connect immediately when module is imported via AppConfig.ready()
connect_signals()

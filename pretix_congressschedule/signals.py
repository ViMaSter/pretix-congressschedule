from django import forms
from django.utils.translation import gettext_lazy as _
try:
	# Available in pretix runtime
	from pretix.base.models import SubEventMetaValue
except Exception:  # pragma: no cover - during docs build or without pretix
	SubEventMetaValue = None


class SubEventLanguageForm(forms.Form):
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

	def __init__(self, *args, **kwargs):
		self.event = kwargs.pop('event')
		self.subevent = kwargs.pop('subevent', None)
		super().__init__(*args, **kwargs)
		# Pre-fill from subevent meta if available
		if self.subevent:
			val = (
				SubEventMetaValue.objects
				.filter(subevent=self.subevent, property__name='congressschedule_language')
				.values_list('value', flat=True)
				.first()
			)
			self.fields['language'].initial = val or ''
		elif self.subevent and hasattr(self.subevent, 'settings'):
			# Fallback (older pretix): might be event-wide, keep as last resort
			self.fields['language'].initial = "deen"

	@property
	def title(self):
		return _("Language")

	def save(self):
		if not self.subevent:
			return
		val = (self.cleaned_data.get('language') or '').strip() or 'none'
		# Persist as real subevent meta value so it's scoped per subevent
		from pretix.base.models import EventMetaProperty

		property_obj, _ = EventMetaProperty.objects.get_or_create(
			name='congressschedule_language',
			defaults={'default': '', 'organizer': self.event.organizer}
		)
		SubEventMetaValue.objects.update_or_create(
			subevent=self.subevent,
			property=property_obj,
			defaults={'value': val},
		)


def subevent_forms(sender, request, subevent, **kwargs):
	# Provide our additional subevent form
	import logging
	logger = logging.getLogger(__name__)
	logger.debug("Providing congressschedule subevent form for event %s, subevent %s", sender.slug, getattr(subevent, 'name', 'no-subevent'))
	form = SubEventLanguageForm(
		data=request.POST if request.method == 'POST' else None,
		event=sender,
		subevent=subevent,
		prefix='congressschedule',
	)
	return form


def connect_signals():
	# Connect to pretix.control.signals.subevent_forms at import time
	try:
		from pretix.control import signals as control_signals

		control_signals.subevent_forms.connect(subevent_forms, dispatch_uid='pretix_congressschedule_subevent_language')
	except Exception:
		# Pretix not fully loaded in some contexts (e.g., docs build)
		pass


# Connect immediately when module is imported via AppConfig.ready()
connect_signals()

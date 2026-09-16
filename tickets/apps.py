from django.apps import AppConfig
from django.db.models.signals import post_migrate

import sys

def auto_seed_workflow(sender, **kwargs):
    if 'test' in sys.argv:
        return
    try:
        from tickets.models import IssueFormField
        if not IssueFormField.objects.exists():
            from django.core.management import call_command
            call_command('seed_glpi_workflow')
    except Exception:
        pass

class TicketsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tickets'

    def ready(self):
        post_migrate.connect(auto_seed_workflow, sender=self)


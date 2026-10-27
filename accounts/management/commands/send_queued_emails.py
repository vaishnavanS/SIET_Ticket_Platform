import sys
from django.core.management.base import BaseCommand
from accounts.utils import process_email_queue

class Command(BaseCommand):
    help = "Dispatches pending queued emails from the EmailQueue table via SMTP/configured backend."

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help="Maximum number of queued emails to process in one execution (default: 50)."
        )
        parser.add_argument(
            '--retry-failed',
            action='store_true',
            help="Retry failed emails whose attempts are below max_attempts."
        )

    def handle(self, *args, **options):
        limit = options['limit']
        retry_failed = options['retry_failed']

        self.stdout.write(f"Checking email queue (limit={limit}, retry_failed={retry_failed})...")
        stats = process_email_queue(limit=limit, retry_failed=retry_failed)

        if stats['processed'] == 0:
            self.stdout.write(self.style.SUCCESS("Email queue is clean: 0 pending messages to send."))
        else:
            msg = f"Processed {stats['processed']} queued emails: {stats['sent']} sent successfully, {stats['failed']} failed."
            if stats['failed'] > 0:
                self.stdout.write(self.style.WARNING(msg))
            else:
                self.stdout.write(self.style.SUCCESS(msg))

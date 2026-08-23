import os
import sys
import socket
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.conf import settings

def get_all_lan_ips():
    ips = set()
    # Strategy 1: UDP routing probe (no actual packet sent)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        primary_ip = s.getsockname()[0]
        if not primary_ip.startswith('127.'):
            ips.add(primary_ip)
        s.close()
    except Exception:
        pass

    # Strategy 2: Hostname lookup
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith('127.'):
                ips.add(ip)
    except Exception:
        pass

    return sorted(list(ips))

class Command(BaseCommand):
    help = 'Runs the Django development server accessible across LAN with dynamic IP detection'

    def add_arguments(self, parser):
        parser.add_argument(
            'port',
            nargs='?',
            default='8000',
            help='Port number to run the server on (default: 8000)'
        )
        parser.add_argument(
            '--noreload',
            action='store_true',
            help='Tells Django to NOT use the auto-reloader.'
        )

    def handle(self, *args, **options):
        port = options['port']
        lan_ips = get_all_lan_ips()

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 68))
        self.stdout.write(self.style.SUCCESS('  🚀 SIET HELPDESK — LAN ACCESSIBLE SERVER RUNNING'))
        self.stdout.write(self.style.SUCCESS('=' * 68))
        self.stdout.write(f'  💻 Localhost Access:       http://127.0.0.1:{port}/')
        self.stdout.write(f'  💻 Localhost Named:        http://localhost:{port}/')
        
        if lan_ips:
            self.stdout.write('\n  🌐 LAN / Wi-Fi Access (for Phones, Tablets & other PCs):')
            for ip in lan_ips:
                self.stdout.write(self.style.MIGRATE_HEADING(f'     👉 http://{ip}:{port}/'))
        else:
            self.stdout.write(self.style.WARNING('  ⚠️  No active LAN IP detected. Ensure you are connected to Wi-Fi/Ethernet.'))

        self.stdout.write('\n  📌 Note: Any device connected to the same Wi-Fi or LAN can')
        self.stdout.write('     open the link above to submit and track support tickets.')
        self.stdout.write(self.style.SUCCESS('=' * 68 + '\n'))

        # Prepare arguments for runserver
        addrport = f'0.0.0.0:{port}'
        runserver_args = [addrport]
        runserver_kwargs = {}
        if options.get('noreload'):
            runserver_kwargs['use_reloader'] = False

        try:
            call_command('runserver', *runserver_args, **runserver_kwargs)
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('\nServer stopped.'))

"""
Management command para aguardar o banco de dados estar disponível.
"""
import time
from django.db import connections
from django.db.utils import OperationalError
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Django command para pausar a execução até o banco de dados estar disponível."""

    def handle(self, *args, **options):
        """Handle the command"""
        self.stdout.write('Aguardando pelo banco de dados...')
        db_conn = None
        while not db_conn:
            try:
                db_conn = connections['default']
            except OperationalError:
                self.stdout.write('Banco de dados indisponível, aguardando 1 segundo...')
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS('Banco de dados disponível!'))
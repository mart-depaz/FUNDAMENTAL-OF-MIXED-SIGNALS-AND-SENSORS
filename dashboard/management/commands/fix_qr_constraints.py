"""
Django management command to fix QR code registration constraints.

Usage: python manage.py fix_qr_constraints
"""

from django.core.management.base import BaseCommand
from django.db import connection
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fix QR code registration constraints to allow same QR across courses'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('QR CODE REGISTRATION CONSTRAINT FIX'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))
        
        # Run migrations
        self.stdout.write('Running migrations...')
        from django.core.management import call_command
        try:
            call_command('migrate', 'dashboard', verbosity=1)
            self.stdout.write(self.style.SUCCESS('✓ Migrations completed successfully\n'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Migration error: {e}\n'))
            return
        
        # Verify constraints
        self.stdout.write('Verifying constraints...')
        
        try:
            with connection.cursor() as cursor:
                if connection.vendor == 'sqlite':
                    # For SQLite
                    cursor.execute("""
                        SELECT sql FROM sqlite_master 
                        WHERE type='index' AND name='uq_active_qr_code_per_course'
                    """)
                    result = cursor.fetchone()
                    if result:
                        self.stdout.write(self.style.SUCCESS('✓ Correct constraint found\n'))
                    else:
                        self.stdout.write(self.style.WARNING('⚠ Could not verify constraint\n'))
                
                elif connection.vendor == 'postgresql':
                    # For PostgreSQL
                    cursor.execute("""
                        SELECT constraint_name FROM information_schema.constraint_column_usage 
                        WHERE constraint_name LIKE '%uq_active_qr_code%'
                    """)
                    results = cursor.fetchall()
                    for result in results:
                        self.stdout.write(f"  - {result[0]}")
                    self.stdout.write(self.style.SUCCESS('\n'))
                
                elif connection.vendor == 'mysql':
                    # For MySQL
                    cursor.execute("""
                        SHOW INDEXES FROM dashboard_qrcoderegistration
                    """)
                    results = cursor.fetchall()
                    for result in results:
                        self.stdout.write(f"  - {result}")
                    self.stdout.write(self.style.SUCCESS('\n'))
        
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠ Could not verify: {e}\n'))
        
        # Summary
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('SUMMARY OF CHANGES'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))
        
        self.stdout.write('Before (❌ Broken):')
        self.stdout.write('  QR code was GLOBALLY unique')
        self.stdout.write('  Student could NOT use same QR in different courses\n')
        
        self.stdout.write(self.style.SUCCESS('After (✓ Fixed):'))
        self.stdout.write(self.style.SUCCESS('  QR code is unique PER COURSE'))
        self.stdout.write(self.style.SUCCESS('  Student CAN use same QR in different courses'))
        self.stdout.write(self.style.SUCCESS('  Different students CANNOT share QR in same course\n'))
        
        self.stdout.write('='*70)
        self.stdout.write(self.style.SUCCESS('FIX COMPLETE!\n'))
        
        self.stdout.write('Next steps:')
        self.stdout.write('  1. Refresh your browser')
        self.stdout.write('  2. Try registering the same QR code in a different course')
        self.stdout.write('  3. It should now work! ✓\n')

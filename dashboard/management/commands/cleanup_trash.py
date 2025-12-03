# dashboard/management/commands/cleanup_trash.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from dashboard.models import Department, Program
from accounts.models import CustomUser


class Command(BaseCommand):
    help = 'Permanently delete items from trash that have been deleted for more than 30 days'

    def handle(self, *args, **options):
        now = timezone.now()
        cutoff_date = now - timedelta(days=30)
        
        # Find items deleted more than 30 days ago
        old_departments = Department.objects.filter(
            deleted_at__isnull=False,
            deleted_at__lt=cutoff_date
        )
        
        old_programs = Program.objects.filter(
            deleted_at__isnull=False,
            deleted_at__lt=cutoff_date
        )
        
        old_users = CustomUser.objects.filter(
            deleted_at__isnull=False,
            deleted_at__lt=cutoff_date
        )
        
        # Count items to be deleted
        dept_count = old_departments.count()
        prog_count = old_programs.count()
        user_count = old_users.count()
        total_count = dept_count + prog_count + user_count
        
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('No items found to permanently delete.'))
            return
        
        # Permanently delete items
        dept_deleted = 0
        prog_deleted = 0
        user_deleted = 0
        
        for dept in old_departments:
            try:
                dept.delete()  # Hard delete
                dept_deleted += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error deleting department {dept.id}: {str(e)}'))
        
        for prog in old_programs:
            try:
                prog.delete()  # Hard delete
                prog_deleted += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error deleting program {prog.id}: {str(e)}'))
        
        for user in old_users:
            try:
                user.delete()  # Hard delete
                user_deleted += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error deleting user {user.id}: {str(e)}'))
        
        # Output results
        self.stdout.write(self.style.SUCCESS(
            f'Successfully permanently deleted:\n'
            f'  - {dept_deleted} department(s)\n'
            f'  - {prog_deleted} program(s)\n'
            f'  - {user_deleted} user(s)\n'
            f'Total: {dept_deleted + prog_deleted + user_deleted} item(s)'
        ))


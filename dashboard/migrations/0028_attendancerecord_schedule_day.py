# Generated migration for adding schedule_day to AttendanceRecord

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0027_courseschedule_attendance_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendancerecord',
            name='schedule_day',
            field=models.CharField(blank=True, help_text='Day of the week for this attendance (Mon, Tue, Wed, etc.) - allows multiple attendance records per day for different schedules', max_length=10, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='attendancerecord',
            unique_together={('course', 'student', 'attendance_date', 'schedule_day')},
        ),
    ]


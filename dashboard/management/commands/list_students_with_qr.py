from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import CustomUser
from dashboard.models import CourseEnrollment, QRCodeRegistration


class Command(BaseCommand):
    help = 'List all students with their enrollments, sections, courses, and QR registrations'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 100))
        self.stdout.write(self.style.SUCCESS('ALL STUDENTS WITH ENROLLMENTS AND QR REGISTRATIONS'))
        self.stdout.write(self.style.SUCCESS('=' * 100))

        students = CustomUser.objects.filter(is_student=True).order_by('full_name')

        if not students.exists():
            self.stdout.write(self.style.WARNING('\nNo students found in database!\n'))
            return

        total_students = students.count()
        total_enrollments = 0
        total_qr_registrations = 0

        for idx, student in enumerate(students, 1):
            self.stdout.write(f"\n{idx}. STUDENT: {student.full_name}")
            self.stdout.write(f"   Username: {student.username}")
            self.stdout.write(f"   School ID: {student.school_id}")
            self.stdout.write(f"   Email: {student.email}")
            self.stdout.write(f"   Year Level: {student.year_level}")
            self.stdout.write(f"   Section: {student.section}")
            self.stdout.write(f"   Program: {student.program.code if student.program else 'N/A'}")

            # Get enrollments
            enrollments = CourseEnrollment.objects.filter(
                student=student,
                is_active=True,
                deleted_at__isnull=True
            ).select_related('course', 'course__program').order_by('course__code')

            if enrollments.exists():
                self.stdout.write(f"\n   COURSES ENROLLED ({enrollments.count()}):")
                for enrollment in enrollments:
                    course = enrollment.course
                    self.stdout.write(
                        f"      • {course.code} - {course.name} "
                        f"(Section {course.section}, {course.semester}, SY {course.school_year})"
                    )
                total_enrollments += enrollments.count()
            else:
                self.stdout.write(f"\n   COURSES ENROLLED: None")

            # Get QR registrations
            qr_regs = QRCodeRegistration.objects.filter(
                student=student,
                is_active=True
            ).select_related('course').order_by('course__code')

            if qr_regs.exists():
                self.stdout.write(f"\n   QR REGISTRATIONS ({qr_regs.count()}):")
                for qr_reg in qr_regs:
                    self.stdout.write(
                        f"      • Course: {qr_reg.course.code}"
                    )
                    self.stdout.write(
                        f"        QR Code: {qr_reg.qr_code}"
                    )
                    self.stdout.write(
                        f"        Registered: {qr_reg.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                total_qr_registrations += qr_regs.count()
            else:
                self.stdout.write(f"\n   QR REGISTRATIONS: None")

            self.stdout.write(f"\n   {'-' * 96}")

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 100))
        self.stdout.write(self.style.SUCCESS(f'SUMMARY'))
        self.stdout.write(self.style.SUCCESS('=' * 100))
        self.stdout.write(f"Total Students: {total_students}")
        self.stdout.write(f"Total Enrollments: {total_enrollments}")
        self.stdout.write(f"Total QR Registrations: {total_qr_registrations}")
        self.stdout.write(self.style.SUCCESS('=' * 100 + '\n'))

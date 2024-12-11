from django.db import models

class Student(models.Model):
    student_email = models.EmailField(primary_key=True)
    student_id = models.IntegerField()
    student_name = models.CharField(max_length=255)
    student_program_id = models.CharField(max_length=255, null=True, blank=True)
    batch_name = models.CharField(max_length=255, null=True, blank=True)


class Subject(models.Model):
    subject_id = models.IntegerField(primary_key=True)
    subject_name = models.CharField(max_length=255)
    cluster_name = models.CharField(max_length=255)
    cluster_id = models.CharField(max_length=255, unique=True)

class Attendance(models.Model):
    attendance_id = models.AutoField(primary_key=True)
    student_email = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField()
    subject_id = models.ForeignKey(Subject, on_delete=models.CASCADE)
    from_time = models.TimeField()
    to_time = models.TimeField()
    hour = models.IntegerField()
    is_present = models.BooleanField()
    staff_id = models.IntegerField(null=True, blank=True)
    staff_name = models.CharField(max_length=255, null=True, blank=True)
    staff_email = models.EmailField(null=True, blank=True)
    time_table_id = models.CharField(max_length=255, null=True, blank=True)

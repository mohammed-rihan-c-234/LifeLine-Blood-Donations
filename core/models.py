from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('donor', 'Donor'),
        ('hospital', 'Hospital'),
        ('admin', 'Admin'),
    )
    BLOOD_GROUP_CHOICES = (
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
    )
    DONOR_AVAILABILITY_CHOICES = (
        ('available', 'Available'),
        ('pending', 'Pending'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='donor')
    latitude = models.FloatField(default=28.6139)
    longitude = models.FloatField(default=77.2090)
    address = models.CharField(max_length=255, blank=True, null=True)
    email_verified = models.BooleanField(default=False)
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES, blank=True, null=True)
    donor_availability = models.CharField(max_length=10, choices=DONOR_AVAILABILITY_CHOICES, default='available')
    last_donation_date = models.DateField(blank=True, null=True)

class BloodInventory(models.Model):
    hospital = models.OneToOneField(User, on_delete=models.CASCADE, related_name='inventory')
    a_positive = models.IntegerField(default=0)
    a_negative = models.IntegerField(default=0)
    b_positive = models.IntegerField(default=0)
    b_negative = models.IntegerField(default=0)
    ab_positive = models.IntegerField(default=0)
    ab_negative = models.IntegerField(default=0)
    o_positive = models.IntegerField(default=0)
    o_negative = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

class SOSAlert(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    )
    DONOR_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    )
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requests')
    patient_name = models.CharField(max_length=100, default="Unknown") # New Field
    blood_type = models.CharField(max_length=5)
    note = models.TextField(blank=True) # Used for "Condition"
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(default=timezone.now)
    responder = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='responses')
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    preferred_hospital = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='preferred_alerts',
    )
    preferred_hospital_name = models.CharField(max_length=255, blank=True, default="")
    donor_responder = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donor_responses',
    )
    donor_status = models.CharField(max_length=10, choices=DONOR_STATUS_CHOICES, default='pending')
    feedback = models.TextField(blank=True, default="")

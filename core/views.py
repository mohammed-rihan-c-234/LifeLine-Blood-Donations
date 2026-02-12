from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib.auth import login
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
import logging
from .models import User, SOSAlert, BloodInventory
from .forms import SignUpForm, HospitalCreationForm, InventoryForm, HospitalUpdateForm, DonorProfileForm
import math
import json
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

# --- Helper: Haversine Distance Calculation ---
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2) * math.sin(dLat/2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# --- Authentication Views ---

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
            except Exception:
                form.add_error('username', 'This username is already taken.')
                return render(request, 'signup.html', {'form': form})
            if user.role == 'hospital':
                BloodInventory.objects.create(hospital=user)

            # Require email verification before login
            user.is_active = False
            user.email_verified = False
            user.save(update_fields=['is_active', 'email_verified'])

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            verify_url = request.build_absolute_uri(f"/verify-email/{uid}/{token}/")

            subject = 'LifeLine: Confirm your email'
            message = (
                f"Hello {user.first_name or user.username},\n\n"
                f"Please confirm your email by clicking the link below:\n"
                f"{verify_url}\n\n"
                f"If you did not sign up, you can ignore this email.\n\n"
                f"- LifeLine"
            )

            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None) or None,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                messages.success(request, "Account created. Please check your email to verify your account.")
            except Exception:
                logger.exception("Failed to send signup verification email (backend=%s).", getattr(settings, 'EMAIL_BACKEND', ''))
                fallback_hint = ""
                if getattr(settings, 'EMAIL_BACKEND', '').endswith('filebased.EmailBackend'):
                    fallback_hint = f" Check `sent_emails/` on the server: {getattr(settings, 'EMAIL_FILE_PATH', '')}."
                messages.error(
                    request,
                    "Account created, but we couldn't send the verification email." + fallback_hint,
                )

            return redirect('login')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})


def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, "Verification link is invalid or expired.")
        return redirect('login')

    user.is_active = True
    user.email_verified = True
    user.save(update_fields=['is_active', 'email_verified'])
    messages.success(request, "Email verified successfully. You can now log in.")
    return redirect('login')

# --- Main Dashboard Controller ---

@login_required
@never_cache
def dashboard(request):
    user = request.user
    
    # 1. ADMIN DASHBOARD
    if user.role == 'admin':
        hospitals = User.objects.filter(role='hospital')
        all_requests = SOSAlert.objects.all().order_by('-created_at')
        hospital_form = HospitalCreationForm()
        
        context = {
            'hospitals': hospitals,
            'requests': all_requests,
            'hospital_form': hospital_form
        }
        return render(request, 'admin_dashboard.html', context)

    # 2. PATIENT DASHBOARD
    elif user.role == 'user':
        my_alerts = SOSAlert.objects.filter(requester=user).order_by('-created_at')
        hospitals = User.objects.filter(role='hospital')
        nearby = []
        for h in hospitals:
            dist = calculate_distance(user.latitude, user.longitude, h.latitude, h.longitude)
            nearby.append({
                'name': h.first_name, 
                'dist': round(dist, 1), 
                'address': h.address
            })
        nearby.sort(key=lambda x: x['dist'])

        registered_hospitals_for_map = [
            {
                'id': h.id,
                'name': h.first_name or h.username,
                'latitude': h.latitude,
                'longitude': h.longitude,
                'address': h.address or '',
            }
            for h in hospitals
        ]

        return render(
            request,
            'patient_dashboard.html',
            {'alerts': my_alerts, 'hospitals': nearby[:5], 'registered_hospitals_for_map': registered_hospitals_for_map},
        )

    # 3. DONOR DASHBOARD
    elif user.role == 'donor':
        all_alerts = SOSAlert.objects.all().order_by('-created_at')
        return render(request, 'donor_dashboard.html', {'alerts': all_alerts})

    # 4. HOSPITAL DASHBOARD
    elif user.role == 'hospital':
        alerts = SOSAlert.objects.filter(status='pending').filter(
            Q(preferred_hospital__isnull=True) | Q(preferred_hospital=user)
        ).order_by('-created_at')
        inventory, _ = BloodInventory.objects.get_or_create(hospital=user)
        blood_map = {
            'A+': 'a_positive', 'A-': 'a_negative',
            'B+': 'b_positive', 'B-': 'b_negative',
            'AB+': 'ab_positive', 'AB-': 'ab_negative',
            'O+': 'o_positive', 'O-': 'o_negative',
        }

        alerts_with_stock = []
        for alert in alerts:
            field_name = blood_map.get(alert.blood_type)
            stock_left = getattr(inventory, field_name, 0) if field_name else 0
            can_accept = stock_left > 0
            alerts_with_stock.append({
                'alert': alert,
                'stock_left': stock_left,
                'can_accept': can_accept,
            })

        alerts_for_map = [
            {
                'id': a.id,
                'patient_name': a.patient_name or 'Unknown',
                'blood_type': a.blood_type,
                'latitude': a.latitude,
                'longitude': a.longitude,
                'note': a.note or '',
                'created_at': a.created_at.isoformat(),
            }
            for a in alerts
            if a.latitude is not None and a.longitude is not None
        ]

        return render(
            request,
            'hospital_dashboard.html',
            {
                'alerts': alerts_with_stock,
                'inventory': inventory,
                'alerts_for_map': alerts_for_map,
            },
        )
    
    return redirect('login')

# --- Admin Capabilities ---

@login_required
def add_hospital(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    if request.method == 'POST':
        form = HospitalCreationForm(request.POST)
        if form.is_valid():
            form.save()
    return redirect('dashboard')

@login_required
def manage_inventory(request, hospital_id):
    if request.user.role != 'admin':
        return redirect('dashboard')
    hospital = get_object_or_404(User, id=hospital_id, role='hospital')
    inventory, _ = BloodInventory.objects.get_or_create(hospital=hospital)
    if request.method == 'POST':
        form = InventoryForm(request.POST, instance=inventory)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = InventoryForm(instance=inventory)
    return render(request, 'manage_inventory.html', {'form': form, 'hospital': hospital})


@login_required
def manage_my_inventory(request):
    if request.user.role != 'hospital':
        return redirect('dashboard')
    hospital = request.user
    inventory, _ = BloodInventory.objects.get_or_create(hospital=hospital)
    if request.method == 'POST':
        form = InventoryForm(request.POST, instance=inventory)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = InventoryForm(instance=inventory)
    return render(request, 'manage_inventory.html', {'form': form, 'hospital': hospital})


@login_required
@never_cache
def donor_profile(request):
    if request.user.role != 'donor':
        return redirect('dashboard')
    if request.method == 'POST':
        form = DonorProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect('donor_profile')
    else:
        form = DonorProfileForm(instance=request.user)
    return render(request, 'donor_profile.html', {'form': form})


@login_required
def manage_hospital(request, hospital_id):
    if request.user.role != 'admin':
        return redirect('dashboard')

    hospital = get_object_or_404(User, id=hospital_id, role='hospital')
    if request.method == 'POST':
        form = HospitalUpdateForm(request.POST, instance=hospital)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = HospitalUpdateForm(instance=hospital)

    return render(request, 'manage_hospital.html', {'form': form, 'hospital': hospital})


@login_required
@require_POST
def delete_hospital(request, hospital_id):
    if request.user.role != 'admin':
        return redirect('dashboard')
    hospital = get_object_or_404(User, id=hospital_id, role='hospital')
    hospital.delete()
    return redirect('dashboard')

# --- SOS Operations ---

@login_required
def submit_sos(request):
    if request.method == 'POST':
        # FIXED: Use 'or "Unknown"' to prevent None values causing IntegrityError
        patient_name = request.POST.get('patient_name') or "Unknown Patient"
        blood_type = request.POST.get('blood_type')
        note = request.POST.get('note') or ""

        try:
            latitude = float(request.POST.get('latitude')) if request.POST.get('latitude') else None
            longitude = float(request.POST.get('longitude')) if request.POST.get('longitude') else None
        except ValueError:
            latitude, longitude = None, None

        if latitude is None or longitude is None:
            latitude = request.user.latitude
            longitude = request.user.longitude

        preferred_hospital = None
        preferred_hospital_name = ""
        preferred_hospital_id = (request.POST.get('preferred_hospital_id') or '').strip()
        if preferred_hospital_id.isdigit():
            candidate = User.objects.filter(id=int(preferred_hospital_id), role='hospital').first()
            if candidate:
                dist = calculate_distance(latitude, longitude, candidate.latitude, candidate.longitude)
                if dist <= 10:
                    preferred_hospital = candidate
                    preferred_hospital_name = candidate.first_name or candidate.username
        
        SOSAlert.objects.create(
            requester=request.user,
            patient_name=patient_name,
            blood_type=blood_type,
            note=note,
            latitude=latitude,
            longitude=longitude,
            preferred_hospital=preferred_hospital,
            preferred_hospital_name=preferred_hospital_name,
        )
    return redirect('dashboard')

@login_required
def respond_sos(request, alert_id, action):
    if request.user.role != 'hospital':
        return redirect('dashboard')

    if request.method != 'POST':
        return redirect('dashboard')
        
    alert = get_object_or_404(SOSAlert, id=alert_id)
    
    if action == 'accept':
        if alert.status != 'pending':
            return redirect('dashboard')
        inventory = get_object_or_404(BloodInventory, hospital=request.user)
        blood_map = {
            'A+': 'a_positive', 'A-': 'a_negative',
            'B+': 'b_positive', 'B-': 'b_negative',
            'AB+': 'ab_positive', 'AB-': 'ab_negative',
            'O+': 'o_positive', 'O-': 'o_negative',
        }
        field_name = blood_map.get(alert.blood_type)
        current_stock = getattr(inventory, field_name, 0) if field_name else 0
        if current_stock <= 0:
            messages.error(request, "No stock left for the requested blood group.")
            return redirect('dashboard')
        alert.status = 'accepted'
        alert.responder = request.user
        alert.save()
        
        # Deduct Inventory
        if field_name:
            setattr(inventory, field_name, current_stock - 1)
            inventory.save()

        # Notify requester
        recipient_email = (alert.requester.email or '').strip()
        if recipient_email:
            hospital_name = request.user.first_name or request.user.username
            subject = 'LifeLine SOS Update: Request Accepted'
            message = (
                f"Hello {alert.requester.first_name or alert.requester.username},\n\n"
                f"Your SOS request has been accepted by {hospital_name}.\n"
                f"Patient: {alert.patient_name}\n"
                f"Blood Type: {alert.blood_type}\n"
                f"Reason: {alert.note or '-'}\n\n"
                f"Please contact the hospital or proceed immediately.\n\n"
                f"- LifeLine"
            )
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None) or None,
                    recipient_list=[recipient_email],
                    fail_silently=False,
                )
            except Exception:
                logger.exception("Failed to send SOS acceptance email (backend=%s).", getattr(settings, 'EMAIL_BACKEND', ''))
                fallback_hint = ""
                if getattr(settings, 'EMAIL_BACKEND', '').endswith('filebased.EmailBackend'):
                    fallback_hint = f" Check `sent_emails/` on the server: {getattr(settings, 'EMAIL_FILE_PATH', '')}."
                messages.error(request, "Accepted the request, but failed to send email notification." + fallback_hint)
            
    elif action == 'decline':
        if alert.status != 'pending':
            return redirect('dashboard')
        alert.status = 'declined' 
        alert.save()

        recipient_email = (alert.requester.email or '').strip()
        if recipient_email:
            hospital_name = request.user.first_name or request.user.username
            subject = 'LifeLine SOS Update: Request Declined'
            message = (
                f"Hello {alert.requester.first_name or alert.requester.username},\n\n"
                f"Your SOS request was declined by {hospital_name}.\n"
                f"Patient: {alert.patient_name}\n"
                f"Blood Type: {alert.blood_type}\n"
                f"Reason: {alert.note or '-'}\n\n"
                f"Please try another hospital or resend the request.\n\n"
                f"- LifeLine"
            )
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None) or None,
                    recipient_list=[recipient_email],
                    fail_silently=False,
                )
            except Exception:
                logger.exception("Failed to send SOS decline email (backend=%s).", getattr(settings, 'EMAIL_BACKEND', ''))
                fallback_hint = ""
                if getattr(settings, 'EMAIL_BACKEND', '').endswith('filebased.EmailBackend'):
                    fallback_hint = f" Check `sent_emails/` on the server: {getattr(settings, 'EMAIL_FILE_PATH', '')}."
                messages.error(request, "Declined the request, but failed to send email notification." + fallback_hint)
        
    return redirect('dashboard')


@login_required
def respond_sos_donor(request, alert_id, action):
    if request.user.role != 'donor':
        return redirect('dashboard')
    if request.method != 'POST':
        return redirect('dashboard')

    alert = get_object_or_404(SOSAlert, id=alert_id)
    if alert.donor_status != 'pending':
        return redirect('dashboard')

    if action == 'accept':
        alert.donor_status = 'accepted'
        alert.donor_responder = request.user
        alert.save()
        request.user.donor_availability = 'pending'
        request.user.save(update_fields=['donor_availability'])
        action_text = 'accepted'
    elif action == 'decline':
        alert.donor_status = 'declined'
        alert.donor_responder = request.user
        alert.save()
        request.user.donor_availability = 'available'
        request.user.save(update_fields=['donor_availability'])
        action_text = 'declined'
    else:
        return redirect('dashboard')

    recipient_email = (alert.requester.email or '').strip()
    if recipient_email:
        donor_name = request.user.first_name or request.user.username
        subject = f'LifeLine Update: Donor {action_text.capitalize()}'
        message = (
            f"Hello {alert.requester.first_name or alert.requester.username},\n\n"
            f"A donor has {action_text} your request.\n"
            f"Donor: {donor_name}\n"
            f"Patient: {alert.patient_name}\n"
            f"Blood Type: {alert.blood_type}\n"
            f"Reason: {alert.note or '-'}\n\n"
            f"- LifeLine"
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None) or None,
                recipient_list=[recipient_email],
                fail_silently=False,
            )
        except Exception:
            logger.exception("Failed to send donor response email (backend=%s).", getattr(settings, 'EMAIL_BACKEND', ''))
            fallback_hint = ""
            if getattr(settings, 'EMAIL_BACKEND', '').endswith('filebased.EmailBackend'):
                fallback_hint = f" Check `sent_emails/` on the server: {getattr(settings, 'EMAIL_FILE_PATH', '')}."
            messages.error(request, "Donor response recorded, but failed to send email." + fallback_hint)

    return redirect('dashboard')


@login_required
def patient_donors(request, alert_id):
    if request.user.role != 'user':
        return redirect('dashboard')
    alert = get_object_or_404(SOSAlert, id=alert_id, requester=request.user)
    donors = list(
        User.objects.filter(
            role='donor',
            blood_group=alert.blood_type,
            donor_availability='available',
        ).order_by('first_name', 'username')
    )

    # Always include the donor who accepted/declined this request (if any),
    # even if they are no longer "available".
    if alert.donor_responder and alert.donor_responder not in donors:
        donors.insert(0, alert.donor_responder)

    return render(request, 'patient_donors.html', {'alert': alert, 'donors': donors})


@login_required
def donor_list(request):
    blood_group = (request.GET.get('blood_group') or '').strip()
    donors = User.objects.filter(role='donor')
    if blood_group:
        donors = donors.filter(blood_group=blood_group)
    donors = donors.order_by('first_name', 'username')
    return render(request, 'donor_list.html', {'donors': donors, 'blood_group': blood_group, 'blood_groups': User.BLOOD_GROUP_CHOICES})


@login_required
def donor_detail(request, donor_id):
    donor = get_object_or_404(User, id=donor_id, role='donor')
    return render(request, 'donor_detail.html', {'donor': donor})


@login_required
@require_POST
def update_location(request):
    try:
        latitude = float(request.POST.get('latitude'))
        longitude = float(request.POST.get('longitude'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Invalid latitude/longitude.'}, status=400)

    request.user.latitude = latitude
    request.user.longitude = longitude
    request.user.save(update_fields=['latitude', 'longitude'])
    return JsonResponse({'ok': True, 'latitude': latitude, 'longitude': longitude})


@login_required
def osm_nearby_hospitals(request):
    try:
        latitude = float(request.GET.get('latitude'))
        longitude = float(request.GET.get('longitude'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Invalid latitude/longitude.'}, status=400)

    try:
        radius = int(request.GET.get('radius', '5000'))
    except ValueError:
        radius = 5000
    radius = max(500, min(radius, 20000))

    query = f"""
[out:json][timeout:25];
(
  node["amenity"="hospital"](around:{radius},{latitude},{longitude});
  way["amenity"="hospital"](around:{radius},{latitude},{longitude});
  relation["amenity"="hospital"](around:{radius},{latitude},{longitude});
);
out center tags;
""".strip()

    data = urllib.parse.urlencode({'data': query}).encode('utf-8')
    req = urllib.request.Request(
        'https://overpass-api.de/api/interpreter',
        data=data,
        headers={'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'},
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Overpass request failed.'}, status=502)

    hospitals = []
    for el in payload.get('elements', []):
        if el.get('type') == 'node':
            lat = el.get('lat')
            lon = el.get('lon')
        else:
            center = el.get('center') or {}
            lat = center.get('lat')
            lon = center.get('lon')
        if lat is None or lon is None:
            continue

        tags = el.get('tags') or {}
        hospitals.append(
            {
                'id': f"{el.get('type')}/{el.get('id')}",
                'name': tags.get('name') or tags.get('name:en') or 'Hospital',
                'latitude': lat,
                'longitude': lon,
                'address': tags.get('addr:full')
                or tags.get('addr:street')
                or tags.get('addr:city')
                or '',
            }
        )

    return JsonResponse({'ok': True, 'hospitals': hospitals})

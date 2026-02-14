from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from core import views
from core.forms import LoginForm

urlpatterns = [
    # --- Custom Admin Features (MUST be before standard admin.site.urls) ---
    path('admin/add-hospital/', views.add_hospital, name='add_hospital'),
    path('admin/inventory/<int:hospital_id>/', views.manage_inventory, name='manage_inventory'),
    path('admin/hospital/<int:hospital_id>/', views.manage_hospital, name='manage_hospital'),
    path('admin/hospital/<int:hospital_id>/delete/', views.delete_hospital, name='delete_hospital'),
    path('hospital/inventory/', views.manage_my_inventory, name='manage_my_inventory'),

    # --- Built-in Django Admin ---
    path('admin/', admin.site.urls),
    
    # --- Core Navigation ---
    path('', views.dashboard, name='dashboard'),
    path('signup/', views.signup, name='signup'),
    path('verify-email/<str:uidb64>/<str:token>/', views.verify_email, name='verify_email'),
    
    # --- Authentication ---
    path('login/', auth_views.LoginView.as_view(template_name='login.html', authentication_form=LoginForm), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # --- SOS Operations ---
    path('sos/submit/', views.submit_sos, name='submit_sos'),
    path('sos/<int:alert_id>/feedback/', views.save_sos_feedback, name='save_sos_feedback'),
    path('sos/<int:alert_id>/<str:action>/', views.respond_sos, name='respond_sos'),
    path('sos/donor/<int:alert_id>/<str:action>/', views.respond_sos_donor, name='respond_sos_donor'),
    path('patient/requests/<int:alert_id>/donors/', views.patient_donors, name='patient_donors'),
    path('donors/', views.donor_list, name='donor_list'),
    path('donors/<int:donor_id>/', views.donor_detail, name='donor_detail'),
    path('donor/profile/', views.donor_profile, name='donor_profile'),

    # --- API ---
    path('api/location/update/', views.update_location, name='update_location'),
    path('api/osm/hospitals/', views.osm_nearby_hospitals, name='osm_nearby_hospitals'),
]

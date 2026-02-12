from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, BloodInventory, SOSAlert

# 1. Register the Custom User Model
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Add our custom fields to the admin list view
    list_display = ('username', 'role', 'first_name', 'address', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser')
    
    # Add our custom fields to the "Edit User" page
    fieldsets = UserAdmin.fieldsets + (
        ('LifeLine Info', {'fields': ('role', 'address', 'latitude', 'longitude')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('LifeLine Info', {'fields': ('role', 'address', 'latitude', 'longitude')}),
    )

# 2. Register Blood Inventory
@admin.register(BloodInventory)
class BloodInventoryAdmin(admin.ModelAdmin):
    list_display = ('hospital', 'updated_at', 'total_stock')
    search_fields = ('hospital__username', 'hospital__first_name')

    # Helper to show total units in the list
    def total_stock(self, obj):
        return (obj.a_positive + obj.a_negative + 
                obj.b_positive + obj.b_negative + 
                obj.ab_positive + obj.ab_negative + 
                obj.o_positive + obj.o_negative)

# 3. Register SOS Alerts
@admin.register(SOSAlert)
class SOSAlertAdmin(admin.ModelAdmin):
    list_display = ('blood_type', 'status', 'requester', 'created_at')
    list_filter = ('status', 'blood_type')
    search_fields = ('requester__username',)
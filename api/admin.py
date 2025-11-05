from django.contrib import admin

# Register your models here.
# api/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Meal

# --- 1. Custom User Admin Configuration ---

class UserAdmin(BaseUserAdmin):
    # Specify the fields to display in the user list view
    list_display = ('username', 'email', 'first_name', 'googleId', 'is_active', 'profileFilled')
    
    # Specify the fields to display/edit on the change form
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'googleId', 'age', 'gender', 'weight', 'height', 'goal', 'bmi', 'profileFilled')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Session Data', {'fields': ('sessionInfo',)}),
    )
    # The fields Django should use to search for users
    search_fields = ('email', 'first_name', 'googleId')
    ordering = ('email',)


# --- 2. Register Models ---

# Register the User model using the custom admin class
admin.site.register(User, UserAdmin)

# Register the Meal model (optional, but good practice for full visibility)
admin.site.register(Meal)
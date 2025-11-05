from django.db import models

# Create your models here.
# api/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

# --- Custom User Model (Replacing User.js) ---
class User(AbstractUser):
    # Core Auth Field
    googleId = models.CharField(max_length=255, unique=True, db_index=True, null=True, blank=True)
    
    # Profile Fields
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=50, null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True) 
    goal = models.CharField(max_length=255, null=True, blank=True)
    bmi = models.FloatField(null=True, blank=True)
    profileFilled = models.BooleanField(default=False)
    
    # Store nested JSON data as a TextField (SQLite fix)
    sessionInfo = models.TextField(null=True, blank=True) 
    
    # We will use the default AbstractUser fields like 'email' and 'name'
    
# --- Meal Model (Replacing Meal.js) ---
class Meal(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meals')
    
    mealType = models.CharField(max_length=50, null=True, blank=True)
    
    # Aggregate data saved for reporting consistency
    calories = models.FloatField(null=True, blank=True)
    protein = models.FloatField(null=True, blank=True)
    carbs = models.FloatField(null=True, blank=True)
    fats = models.FloatField(null=True, blank=True)
    
    # Items: Stored as a comma-separated string
    items = models.TextField() 

    # Image: Django's File/Image Field handles the file path (used to be imageUrl)
    image = models.ImageField(upload_to='meals/', null=True, blank=True)
    
    createdAt = models.DateTimeField(auto_now_add=True)
    
    # Store nested macros data as a TextField (SQLite fix)
    macros = models.TextField(null=True, blank=True) 

    @property
    def imageUrl(self):
        # Helper property for API consistency (matching Node.js response)
        return self.image.url if self.image else None

    def __str__(self):
        user_display = getattr(self.user, "username", getattr(self.user, "email", "UnknownUser"))
        return f"Meal ({self.pk or 'unsaved'}) for {user_display}"
 
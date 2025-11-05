# api/serializers.py
from rest_framework import serializers
from .models import User, Meal

# Serializer for the User model (used for profile and auth responses)
class UserSerializer(serializers.ModelSerializer):
    # 1. Define 'name' explicitly, mapping it to Django's 'first_name'
    name = serializers.CharField(source='first_name', read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'googleId', 'email', 'name', 'age', 'gender', 
            'weight', 'height', 'goal', 'bmi', 'profileFilled', 
            'sessionInfo', 'date_joined' 
        )
# Placeholder for the Meal Serializer (needed for meal views later)
class MealSerializer(serializers.ModelSerializer):
    # This field uses the @property defined in api/models.py
    imageUrl = serializers.ReadOnlyField(source='imageUrl') 

    class Meta:
        model = Meal
        fields = (
            'id', 'user', 'mealType', 'calories', 'items', 'imageUrl', 
            'createdAt', 'macros', 'protein', 'carbs', 'fats'
        )
        read_only_fields = ('user', 'calories', 'macros', 'protein', 'carbs', 'fats', 'items', 'imageUrl')
# api/urls.py
from django.urls import path
from .views import google_auth_view , get_profile_view, update_profile_view ,calculate_calorie_target_view , generate_health_report_view , add_meal ,delete_meal,get_daily_meals,get_monthly_meals

urlpatterns = [
    # Node.js: router.post('/google', googleAuth); -> Django: /auth/google/
    path('auth/google/', google_auth_view, name='google_auth'),
    path('profile/<int:user_id>/', get_profile_view, name='get_profile'), 
    # POST /profile/
    path('profile/', update_profile_view, name='update_profile'),
    
    
    path('calories/calculate/', calculate_calorie_target_view, name='calculate_calorie_target'),
    # POST /calories/report/
    path('calories/report/', generate_health_report_view, name='generate_health_report'),
    # Other paths will be added in Phase 2, 3, and 4

    path('meals/',add_meal ,name='add_meal'),
    path('meals/<int:meal_id>/', delete_meal, name='delete_meal'),  # DELETE
    path('meals/daily/', get_daily_meals, name='get_daily_meals'),  # GET
    path('meals/monthly/', get_monthly_meals, name='get_monthly_meals'),  # GET
]
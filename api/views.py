from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import authentication_classes
from .authentication import JWTGoogleAuthentication
from ultralytics import YOLO
from django.utils import timezone
from .models import Meal
import uuid
from .models import User
from collections import defaultdict
from .serializers import UserSerializer 
from .utils import (
    CALORIE_MAP, 
    generate_gemini_response, # <-- The helper function we use
    CALORIE_TARGET_SCHEMA, 
    HEALTH_REPORT_SCHEMA
)
from api.models import Meal

import jwt
from google.oauth2 import id_token
from google.auth.transport import requests
import datetime
import json
import os 
# NOTE: The imports below are ONLY for the Google Auth view, not for Gemini.

# --- Authentication Views ---

@csrf_exempt 
@api_view(['POST'])
def google_auth_view(request):
    """Replaces googleAuth controller."""
    try:
        token = request.data.get('token')
        if not token:
            return JsonResponse({"error": "Token missing"}, status=400)

        request_transport = requests.Request()
        payload = id_token.verify_oauth2_token(
            token, 
            request_transport, 
            settings.GOOGLE_CLIENT_ID 
        )
        
        user, created = User.objects.get_or_create(
            googleId=payload['sub'],
            defaults={
                'email': payload.get('email'), 
                'first_name': payload.get('name', 'User'),
                'username': payload['sub']
            }
        )

        from .serializers import UserSerializer 
        user_data = UserSerializer(user).data

        expiration = timezone.now() + datetime.timedelta(hours=24)
        jwt_token = jwt.encode(
            {'googleId': user.googleId, 'exp': expiration.timestamp()}, 
            settings.JWT_SECRET, 
            algorithm="HS256"
        )
        
        return JsonResponse({
            "user": user_data, 
            "token": jwt_token, 
            "profileIncomplete": not user.profileFilled
        }, status=200)

    except Exception as e:
        print(f"Authentication Error: {e}") 
        return JsonResponse({"error": str(e)}, status=400)

# --- Profile Views ---
# (Unchanged)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile_view(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.user.id != user.id:
        return JsonResponse({"error": "Forbidden"}, status=403)
    from .serializers import UserSerializer 
    return JsonResponse(UserSerializer(user).data, status=200)
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTGoogleAuthentication])
def update_profile_view(request):
    updates = request.data
    user = request.user 

    if 'name' in updates: user.first_name = updates['name']
    if 'age' in updates: user.age = updates['age']
    if 'gender' in updates: user.gender = updates['gender']
    if 'weight' in updates: user.weight = updates['weight']
    if 'height' in updates: user.height = updates['height']
    if 'goal' in updates: user.goal = updates['goal']
    user.profileFilled = True

    session_info = updates.get('sessionInfo')
    if session_info:
        # ✅ If frontend sent it as JSON string, convert to dict
        if isinstance(session_info, str):
            try:
                session_info = json.loads(session_info)
            except json.JSONDecodeError:
                session_info = {}

        session_info_obj = {
            'dailyCalories': session_info.get('dailyCalories'),
            'macros': {
                'protein': session_info.get('macros', {}).get('protein'),
                'carbs': session_info.get('macros', {}).get('carbs'),
                'fats': session_info.get('macros', {}).get('fats')
            }
        }
        user.sessionInfo = json.dumps(session_info_obj)

    if user.weight and user.height and user.height > 0:
        height_in_meters = user.height / 100 
        user.bmi = round(user.weight / (height_in_meters ** 2), 1)

    user.save()
    from .serializers import UserSerializer 
    return JsonResponse(UserSerializer(user).data, status=200)


# --- Calorie Views (AI Logic Fixed) ---

@api_view(['POST'])
@authentication_classes([JWTGoogleAuthentication])
@permission_classes([IsAuthenticated])
def calculate_calorie_target_view(request):
    """Replaces calculateCalorieTarget controller."""
    try:
        user_info = request.data
        
        prompt = f"""Calculate a daily calorie target for a person with the following profile:
- Name: {user_info.get('name')}
- Age: {user_info.get('age')}
- Gender: {user_info.get('gender')}
- Weight: {user_info.get('weight')} kg
- Height: {user_info.get('height')} cm
- BMI: {user_info.get('bmi')}
- Goal: {user_info.get('goal')}
# ... (rest of prompt) ...
"""
        
        # --- FIXED CALL: Use helper function from utils.py ---
        calorie_data = generate_gemini_response(prompt, CALORIE_TARGET_SCHEMA)
        print("cal",calorie_data)
        # --- END FIXED CALL ---
        
        if "error" in calorie_data:
            return JsonResponse(calorie_data, status=500)
            
        return JsonResponse(calorie_data, status=200)
    except Exception as e:
        print(f"Error calculating calorie target: {e}")
        return JsonResponse({'error': 'Failed to calculate calorie target'}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTGoogleAuthentication])
def generate_health_report_view(request):
    """Replaces generateHealthReport controller."""
    try:
        data = request.data
        
        prompt = f"""Generate a detailed personalized health report for the following user with the defined goal:
- Name: {data.get('name')}
# ... (rest of prompt) ...
"""

        # --- FIXED CALL: Use helper function from utils.py ---
        report_data = generate_gemini_response(prompt, HEALTH_REPORT_SCHEMA)
        # --- END FIXED CALL ---
        
        if "error" in report_data:
            return JsonResponse(report_data, status=500)
            
        return JsonResponse(report_data, status=200)

    except Exception as e:
        print(f"Error generating report: {e}")
        return JsonResponse({'error': 'Failed to generate health report'}, status=500)
    

MODEL_PATH = os.path.join(os.getcwd(), "best.pt")
yolo_model = YOLO(MODEL_PATH)

CALORIE_MAP = [
  {
    "name": "appam",
    "calories": "180",
    "Fats": "4.12",
    "Carbs": "30.47",
    "Proteins": "4.6"
  },
  {
    "name": "beetroot fry",
    "calories": "43",
    "Fats": "0.17",
    "Carbs": "9.56",
    "Proteins": "1.61"
  },
  {
    "name": "boiled egg",
    "calories": "154",
    "Fats": "10.57",
    "Carbs": "1.12",
    "Proteins": "12.53"
  },
  {
    "name": "carrot fry",
    "calories": "54",
    "Fats": "2.48",
    "Carbs": "7.99",
    "Proteins": "0.74"
  },
  {
    "name": "chicken 65",
    "calories": "182",
    "Fats": "9.85",
    "Carbs": "8.41",
    "Proteins": "16.09"
  },
  {
    "name": "chicken briyani",
    "calories": "139",
    "Fats": "3.93",
    "Carbs": "19.23",
    "Proteins": "6.36"
  },
  {
    "name": "chutney",
    "calories": "149",
    "Fats": "0.29",
    "Carbs": "36.85",
    "Proteins": "1.33"
  },
  {
    "name": "crab curry",
    "calories": "101",
    "Fats": "1.76",
    "Carbs": "0",
    "Proteins": "20.03"
  },
  {
    "name": "dosa",
    "calories": "212",
    "Fats": "2.07",
    "Carbs": "42.48",
    "Proteins": "5.03"
  },
  {
    "name": "idly",
    "calories": "135",
    "Fats": "0.62",
    "Carbs": "26.31",
    "Proteins": "6.36"
  },
  {
    "name": "kaara chutney",
    "calories": "149",
    "Fats": "0.29",
    "Carbs": "36.85",
    "Proteins": "1.33"
  },
  {
    "name": "lemon rice",
    "calories": "146",
    "Fats": "0.55",
    "Carbs": "31.48",
    "Proteins": "3"
  },
  {
    "name": "masala vada",
    "calories": "230",
    "Fats": "16.72",
    "Carbs": "16.09",
    "Proteins": "4.94"
  },
  {
    "name": "mushroom briyani",
    "calories": "150",
    "Fats": "6.5",
    "Carbs": "20",
    "Proteins": "7"
  },
  {
    "name": "mutton briyani",
    "calories": "141",
    "Fats": "4.34",
    "Carbs": "19.26",
    "Proteins": "5.84"
  },
  {
    "name": "paal kolukattai",
    "calories": "230",
    "Fats": "23.84",
    "Carbs": "5.54",
    "Proteins": "2.29"
  },
  {
    "name": "paneer briyani",
    "calories": "169",
    "Fats": "4.47",
    "Carbs": "26.41",
    "Proteins": "5.69"
  },
  {
    "name": "paneer masala",
    "calories": "211",
    "Fats": "16.66",
    "Carbs": "8.83",
    "Proteins": "7.68"
  },
  {
    "name": "prawn thokku",
    "calories": "101",
    "Fats": "3.46",
    "Carbs": "2.43",
    "Proteins": "14.42"
  },
  {
    "name": "puthina chutney",
    "calories": "44",
    "Fats": "1.64",
    "Carbs": "6.8",
    "Proteins": "2.04"
  },
  {
    "name": "raagi ball",
    "calories": "205",
    "Fats": "4.4",
    "Carbs": "35.52",
    "Proteins": "5.4"
  },
  {
    "name": "raagi malt",
    "calories": "52",
    "Fats": "1.02",
    "Carbs": "8.83",
    "Proteins": "2.32"
  },
  {
    "name": "sambar",
    "calories": "114",
    "Fats": "4.1",
    "Carbs": "15.9",
    "Proteins": "4.9"
  },
  {
    "name": "sambar rice",
    "calories": "90",
    "Fats": "1.85",
    "Carbs": "16.44",
    "Proteins": "2.75"
  },
  {
    "name": "vada",
    "calories": "282",
    "Fats": "8.64",
    "Carbs": "40.97",
    "Proteins": "10.59"
  },
  {
    "name": "veg briyani",
    "calories": "130",
    "Fats": "2.53",
    "Carbs": "23.33",
    "Proteins": "3.16"
  },
  {
    "name": "ven pongal",
    "calories": "70",
    "Fats": "1.71",
    "Carbs": "11.9",
    "Proteins": "1.88"
  },
  {
    "name": "white rice",
    "calories": "135",
    "Fats": "1.07",
    "Carbs": "27.64",
    "Proteins": "2.64"
  },
  {
    "name": "BhindiMasala",
    "calories": "112",
    "Fats": "6.4",
    "Carbs": "13.51",
    "Proteins": "2.99"
  },
  {
    "name": "Chai",
    "calories": "30",
    "Fats": "0.53",
    "Carbs": "6.12",
    "Proteins": "0.53"
  },
  {
    "name": "FishCurry",
    "calories": "100",
    "Fats": "4.59",
    "Carbs": "1.9",
    "Proteins": "12.4"
  },
  {
    "name": "GulabJamun",
    "calories": "323",
    "Fats": "15.75",
    "Carbs": "39.26",
    "Proteins": "7.15"
  },
  {
    "name": "Jalebi",
    "calories": "300",
    "Fats": "4.31",
    "Carbs": "62.36",
    "Proteins": "4.19"
  },
  {
    "name": "Kebab",
    "calories": "159",
    "Fats": "4.27",
    "Carbs": "19.77",
    "Proteins": "9.71"
  },
  {
    "name": "MuttonCurry",
    "calories": "126",
    "Fats": "8.77",
    "Carbs": "1.02",
    "Proteins": "10.37"
  },
  {
    "name": "curd",
    "calories": "100",
    "Fats": "4.2",
    "Carbs": "3.45",
    "Proteins": "11.75"
  },
  {
    "name": "papad",
    "calories": "371",
    "Fats": "3.25",
    "Carbs": "59.87",
    "Proteins": "25.56"
  },
  {
    "name": "raita",
    "calories": "101",
    "Fats": "7.21",
    "Carbs": "6.43",
    "Proteins": "3.31"
  },
  {
    "name": "roti",
    "calories": "264",
    "Fats": "1.3",
    "Carbs": "55.81",
    "Proteins": "9.61"
  },
  {
    "name": "rasam",
    "calories": "19",
    "Fats": "0.88",
    "Carbs": "2.82",
    "Proteins": "0.39"
  },
  {
    "name": "sweet",
    "calories": "390",
    "Fats": "0.15",
    "Carbs": "99.52",
    "Proteins": "2.79"
  },
{
  "name": "veg-fry",
  "calories": "168",
  "Fats": "6.59",
  "Carbs": "21.1",
  "Proteins": "7.72"
},
{
  "name": "SAMOSA",
  "calories": "308",
  "Fats": "17.86",
  "Carbs": "32.21",
  "Proteins": "4.67"
},
{
  "name": "UPMA",
  "calories": "209",
  "Fats": "3.15",
  "Carbs": "38.06",
  "Proteins": "6.76"
},
{
  "name": "cashew",
  "calories": "581",
  "Fats": "47.77",
  "Carbs": "30.16",
  "Proteins": "16.84"
},
{
  "name": "bread",
  "calories": "266",
  "Fats": "3.29",
  "Carbs": "50.61",
  "Proteins": "7.64"
},
{
  "name": "dates",
  "calories": "277",
  "Fats": "0.15",
  "Carbs": "74.97",
  "Proteins": "1.81"
},
{
  "name": "Kiwi",
  "calories": "61",
  "Fats": "0.52",
  "Carbs": "14.66",
  "Proteins": "1.14"
},
{
  "name": "mango",
  "calories": "60",
  "Fats": "0.25",
  "Carbs": "15.74",
  "Proteins": "0.47"
},
{
  "name": "Palak Paneer",
  "calories": "169",
  "Fats": "13.18",
  "Carbs": "6.07",
  "Proteins": "7.89"
},
{
  "name": "Paneer Ki Sabji",
  "calories": "125",
  "Fats": "8.52",
  "Carbs": "9.64",
  "Proteins": "4.02"
},
{
  "name": "MuskMelon",
  "calories": "34",
  "Fats": "0.19",
  "Carbs": "8.16",
  "Proteins": "0.84"
},
{
  "name": "apple",
  "calories": "52",
  "Fats": "0.17",
  "Carbs": "13.81",
  "Proteins": "0.26"
},
{
  "name": "banana",
  "calories": "89",
  "Fats": "0.33",
  "Carbs": "22.84",
  "Proteins": "1.09"
},
{
  "name": "custard apple",
  "calories": "101",
  "Fats": "0.6",
  "Carbs": "25.2",
  "Proteins": "1.7"
},
{
  "name": "Guava",
  "calories": "68",
  "Fats": "0.95",
  "Carbs": "14.32",
  "Proteins": "2.55"
},
{
  "name": "orange",
  "calories": "47",
  "Fats": "0.12",
  "Carbs": "11.75",
  "Proteins": "0.94"
},
{
  "name": "pineapple",
  "calories": "48",
  "Fats": "0.12",
  "Carbs": "12.63",
  "Proteins": "0.54"
},
{
  "name": "almonds",
  "calories": "578",
  "Fats": "50.64",
  "Carbs": "19.74",
  "Proteins": "21.26"
},
{
  "name": "pomogrenate",
  "calories": "68",
  "Fats": "0.3",
  "Carbs": "17.17",
  "Proteins": "0.95"
},
{
  "name": "Burger",
  "calories": "313",
  "Fats": "14.85",
  "Carbs": "31.13",
  "Proteins": "14.48"
},
{
  "name": "Pizza",
  "calories": "276",
  "Fats": "11.74",
  "Carbs": "30.33",
  "Proteins": "12.33"
},
{
  "name": "Omlette",
  "calories": "153",
  "Fats": "12.02",
  "Carbs": "0.69",
  "Proteins": "10.62"
},
{
  "name": "Cake",
  "calories": "297",
  "Fats": "4.3",
  "Carbs": "57.7",
  "Proteins": "7.3"
},
{
  "name": "dal",
  "calories": "101",
  "Fats": "3.23",
  "Carbs": "13.36",
  "Proteins": "5.28"
},
{
  "name": "poori",
  "calories": "296",
  "Fats": "9.43",
  "Carbs": "46.73",
  "Proteins": "7.54"
},
{
  "name": "pickle",
  "calories": "18",
  "Fats": "0.19",
  "Carbs": "4.12",
  "Proteins": "0.62"
},
{
  "name": "salad",
  "calories": "17",
  "Fats": "0.24",
  "Carbs": "3.2",
  "Proteins": "1.52"
}
]


# Import your calorie data

@csrf_exempt
@api_view(['POST'])
@authentication_classes([JWTGoogleAuthentication])
@permission_classes([IsAuthenticated])
def add_meal(request):
    print("called")
    user = request.user
    print("user",user)
    """POST /meals/ - Upload image, detect food using YOLO, and save meal"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=400)

    if 'image' not in request.FILES:
        return JsonResponse({'error': 'Image file required'}, status=400)

    # ✅ Save uploaded image
    image = request.FILES['image']
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'meals')
    os.makedirs(upload_dir, exist_ok=True)
    image_name = f"{uuid.uuid4()}.jpg"
    image_path = os.path.join(upload_dir, image_name)

    with open(image_path, 'wb+') as f:
        for chunk in image.chunks():
            f.write(chunk)

    # ✅ Run YOLOv8 inference
    results = yolo_model.predict(source=image_path, conf=0.5, imgsz=640, verbose=False)

    detected_items = []
    for box in results[0].boxes:
        cls_id = int(box.cls)
        label = results[0].names[cls_id]
        detected_items.append(label)

    if not detected_items:
        return JsonResponse({'message': 'No food detected'}, status=200)

    # ✅ Calculate calories and macros
    total_calories = total_protein = total_carbs = total_fats = 0.0
    for item in detected_items:
        entry = next((x for x in CALORIE_MAP if x['name'].lower() == item.lower()), None)
        if entry:
            total_calories += float(entry['calories'])
            total_fats += float(entry['Fats'])
            total_carbs += float(entry['Carbs'])
            total_protein += float(entry['Proteins'])
        else:
            total_calories += 100  # default if not found

    macros = {

        "protein": total_protein,
        "carbs": total_carbs,
        "fats": total_fats
    }

    # ✅ Save meal in DB
    meal = Meal.objects.create(
        user=user,  # replace with user if authentication is added
        mealType=request.POST.get('mealType', 'Unknown'),
        calories=total_calories,
        protein=total_protein,
        carbs=total_carbs,
        fats=total_fats,
        items=", ".join(detected_items),
        image=f"meals/{image_name}",
        macros=json.dumps(macros)
    )

    # ✅ Response
    return JsonResponse({
        "message": "Meal detected and saved successfully",
        "meal": {
            "id": meal.id,
            "items": detected_items,
            "calories": total_calories,
            "protein": total_protein,
            "carbs": total_carbs,
            "fats": total_fats,
            "macros": macros,
            "imageUrl": request.build_absolute_uri(meal.image.url) if meal.image else None
        }
    })
@api_view(['DELETE'])
@authentication_classes([JWTGoogleAuthentication])
@permission_classes([IsAuthenticated])
def delete_meal(request, meal_id):
    user = request.user
    try:
        meal = Meal.objects.get(id=meal_id, user=user)
        meal.delete()
        return JsonResponse({"message": "Meal deleted successfully"}, status=200)
    except Meal.DoesNotExist:
        return JsonResponse({"error": "Meal not found"}, status=404)
@api_view(['GET'])
@authentication_classes([JWTGoogleAuthentication])
@permission_classes([IsAuthenticated])



def get_daily_meals(request):
    user = request.user
    today = timezone.now().date()

    meals = Meal.objects.filter(user=user, createdAt__date=today)

    total_calories = total_protein = total_carbs = total_fats = 0
    breakdown = {"breakfast": 0, "lunch": 0, "dinner": 0, "snacks": 0, "other": 0}

    for meal in meals:
        total_calories += meal.calories or 0
        total_protein += meal.protein or 0
        total_carbs += meal.carbs or 0
        total_fats += meal.fats or 0

        mtype = meal.mealType.lower() if meal.mealType else "other"
        if mtype in breakdown:
            breakdown[mtype] += meal.calories or 0
        else:
            breakdown["other"] += meal.calories or 0

    return JsonResponse({
        "date": today.strftime("%Y-%m-%d"),
        "total": total_calories,
        "breakdown": breakdown,
        "macros": {
            "protein": total_protein,
            "carbs": total_carbs,
            "fats": total_fats
        }
    }, status=200)

from datetime import timedelta


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTGoogleAuthentication])
def get_monthly_meals(request):
    user = request.user
    today = timezone.now().date()
    start_of_month = today.replace(day=1)

    meals = Meal.objects.filter(user=user, createdAt__date__gte=start_of_month)

    daily_summary = defaultdict(lambda: {
        "total": 0,
        "breakdown": {
            "breakfast": 0,
            "lunch": 0,
            "dinner": 0,
            "snacks": 0,
            "other": 0
        },
        "macros": {
            "protein": 0,
            "carbs": 0,
            "fats": 0
        }
    })

    # Aggregate meals per day
    for meal in meals:
        day_number = meal.createdAt.day
        summary = daily_summary[day_number]

        # total calories
        summary["total"] += meal.calories or 0

        # macros
        summary["macros"]["protein"] += meal.protein or 0
        summary["macros"]["carbs"] += meal.carbs or 0
        summary["macros"]["fats"] += meal.fats or 0

        # meal type breakdown
        mtype = meal.mealType.lower() if meal.mealType else "other"
        if mtype in summary["breakdown"]:
            summary["breakdown"][mtype] += meal.calories or 0
        else:
            summary["breakdown"]["other"] += meal.calories or 0

    # Sort by day
    monthly_data = [
        {"day": day, **data}
        for day, data in sorted(daily_summary.items())
    ]

    response = {
        "month": today.strftime("%B"),
        "year": today.year,
        "days": monthly_data
    }

    return JsonResponse(response, status=200)

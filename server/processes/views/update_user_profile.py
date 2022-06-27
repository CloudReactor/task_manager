from django.http import JsonResponse

from rest_framework.views import APIView

from ..models import UserProfile
from ..serializers import UserSerializer


class UpdateUserProfile(APIView):
    def post(self, request):
        user = request.user

        user_profile = UserProfile.objects.get_or_create(user=user)[0]

        for attr, value in request.data.items():
            setattr(user_profile, attr, value)
            user_profile.save()
        serializer = UserSerializer(user)

        return JsonResponse({'user': serializer.data})

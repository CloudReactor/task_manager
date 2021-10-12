from django.http import JsonResponse

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework import status

from ..serializers import UserSerializer


class VerifyToken(APIView):
    """ Check is auth token correct """
    def get(self, request: Request) -> JsonResponse:
        serializer = UserSerializer(request.user)
        return JsonResponse({'status':status.HTTP_200_OK, 'user': serializer.data})

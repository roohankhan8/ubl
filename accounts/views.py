from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import MeSerializer


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        profile = getattr(request.user, "profile", None)
        return Response(
            MeSerializer(
                {
                    "id": request.user.id,
                    "username": request.user.username,
                    "email": request.user.email,
                    "role": profile.role if profile else None,
                }
            ).data
        )

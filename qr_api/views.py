from django.http import HttpResponse
from django.urls import reverse
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Person
from .serializers import PersonSerializer
from .qr_generator import build_qr_matrix, matrix_to_svg


def absolute_url(request, name, person_id):
    return request.build_absolute_uri(reverse(name, kwargs={"person_id": person_id}))


class GenerateQRCodeAPIView(APIView):
    """Save person data and return QR-related URLs."""

    def post(self, request):
        serializer = PersonSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        person = serializer.save()
        person_url = absolute_url(request, "person_detail", person.id)

        try:
            build_qr_matrix(person_url)
        except ValueError as error:
            person.delete()
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Data saved and QR code generated successfully",
            "person_database_id": person.id,
            "qr_contains": person_url,
            "qr_image_url": absolute_url(request, "person_qr_image", person.id),
            "person_data_url": person_url,
        })


class PersonQRCodeImageAPIView(APIView):
    """Return the QR code as an SVG image."""

    def get(self, request, person_id):
        person = get_object_or_404(Person, id=person_id)
        person_url = absolute_url(request, "person_detail", person.id)

        try:
            svg = matrix_to_svg(build_qr_matrix(person_url))
        except ValueError as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

        return HttpResponse(svg, content_type="image/svg+xml")


class PersonDetailAPIView(APIView):
    """Return saved person details."""

    def get(self, request, person_id):
        person = get_object_or_404(Person, id=person_id)
        return Response(PersonSerializer(person).data)

from django.http import HttpResponse
from django.urls import reverse

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Person
from .serializers import PersonSerializer
from .qr_generator import build_qr_matrix, matrix_to_svg


class GenerateQRCodeAPIView(APIView):
    """API endpoint to save person data and return QR-related URLs."""

    def post(self, request):
        name = request.data.get("name")
        age = request.data.get("age")
        email = request.data.get("email")
        person_id = request.data.get("person_id")
        city = request.data.get("city")

        if name in [None, ""] or age in [None, ""] or email in [None, ""] or person_id in [None, ""] or city in [None, ""]:
            return Response(
                {"error": "All fields are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            age = int(age)
        except ValueError:
            return Response(
                {"error": "Age must be a number"},
                status=status.HTTP_400_BAD_REQUEST
            )

        person = Person.objects.create(
            name=name,
            age=age,
            email=email,
            person_id=person_id,
            city=city
        )

        person_url = get_person_url(request, person.id)
        qr_image_url = get_qr_image_url(request, person.id)

        try:
            build_qr_matrix(person_url)
        except ValueError as error:
            person.delete()
            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            "message": "Data saved and QR code generated successfully",
            "person_database_id": person.id,
            "qr_contains": person_url,
            "qr_image_url": qr_image_url,
            "person_data_url": person_url
        })


class PersonQRCodeImageAPIView(APIView):
    """API endpoint that returns QR code as an SVG image."""

    def get(self, request, person_id):
        try:
            person = Person.objects.get(id=person_id)
        except Person.DoesNotExist:
            return Response(
                {"error": "Person not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        person_url = get_person_url(request, person.id)

        try:
            matrix = build_qr_matrix(person_url)
            svg = matrix_to_svg(matrix)
        except ValueError as error:
            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return HttpResponse(svg, content_type="image/svg+xml")


class PersonDetailAPIView(APIView):
    """API endpoint that returns saved person details."""

    def get(self, request, person_id):
        try:
            person = Person.objects.get(id=person_id)
        except Person.DoesNotExist:
            return Response(
                {"error": "Person not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = PersonSerializer(person)
        return Response(serializer.data)


def get_person_url(request, person_id):
    path = reverse("person_detail", kwargs={"person_id": person_id})
    return request.build_absolute_uri(path)


def get_qr_image_url(request, person_id):
    path = reverse("person_qr_image", kwargs={"person_id": person_id})
    return request.build_absolute_uri(path)
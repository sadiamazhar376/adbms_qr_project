from django.urls import path
from .views import GenerateQRCodeAPIView, PersonQRCodeImageView, PersonDetailAPIView
urlpatterns = [
    path("qr/generate/", GenerateQRCodeAPIView.as_view(), name="generate_qr_code"),
    path("qr/image/<int:person_id>/", PersonQRCodeImageView.as_view(), name="person_qr_image"),
    path("person/<int:person_id>/", PersonDetailAPIView.as_view(), name="person_detail"),
]

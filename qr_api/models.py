from django.db import models

# Create your models here.
class Person(models.Model):
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    email = models.EmailField()
    person_id = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    def __str__(self):
        return self.name



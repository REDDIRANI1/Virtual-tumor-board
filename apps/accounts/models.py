import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        WARRIOR = 'warrior', 'Warrior'
        DOCTOR = 'doctor', 'Doctor'
        MODERATOR = 'moderator', 'Moderator'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.WARRIOR)

    def __str__(self):
        return self.username

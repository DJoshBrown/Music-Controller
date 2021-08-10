from django.db import models
from django.db.models.fields import CharField
import string, random

def generate_unique_code():

    length = 6
    while True: 
        code = ''.join(random.choices(string.ascii_uppercase, k=length))
        if Room.objects.filter(code=code).count() == 0:
            break

    return code

# Create your models here.
#Note that we want "Fat Models, Thin Views". This is the mantra of Django. Lets process as much as we can within our models



class Room(models.Model):

    code = CharField(max_length=8, default=generate_unique_code, unique=True)
    host = CharField(max_length=50, unique=True)
    guest_can_pause = models.BooleanField(null=False, default=False)
    votes_to_skip = models.IntegerField(null=False, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    current_song = models.CharField(max_length=50, null=True)

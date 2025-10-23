from tortoise import fields
from tortoise.models import Model

class Key(Model):
    id = fields.IntField(pk=True)
    token = fields.CharField(max_length=3000, null=True, default=None)
    api_key = fields.CharField(max_length=255, null=True, default=None)

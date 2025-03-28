from tortoise import fields, Tortoise
from tortoise.models import Model

from tortoise_imagefield import ImageField, StorageTypes


# Define an isolated test model
class ItemModel(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255)
    image = ImageField()
    avatar = ImageField(null=True, directory_name="avatars", field_for_name="name")


class ItemS3Model(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255)
    s3_image = ImageField(storage_type=StorageTypes.S3_AWS)
    s3_avatar = ImageField(storage_type=StorageTypes.S3_AWS, null=True, directory_name="avatars", field_for_name="name")

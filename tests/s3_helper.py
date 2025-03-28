import boto3
from botocore.exceptions import ClientError

from tortoise_imagefield.config import Config

cfg = Config()


class S3Helper:
    _instance = None
    _client = None

    def __init__(self):
        if not self._client:
            self._client = boto3.client(
                "s3",
                aws_access_key_id=cfg.s3_access_key,
                aws_secret_access_key=cfg.s3_secret_key,
                region_name=cfg.s3_region,
            )

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)

        return cls._instance

    def clear(self):
        objects = self._client.list_objects_v2(Bucket=cfg.s3_bucket, Prefix=cfg.image_url)
        if "Contents" in objects:
            delete_keys = [{"Key": obj["Key"]} for obj in objects["Contents"]]

            self._client.delete_objects(Bucket=cfg.s3_bucket, Delete={"Objects": delete_keys})

    def check_exists(self, image_key):
        try:
            self._client.head_object(Bucket=cfg.s3_bucket, Key=image_key)
            return True
        except ClientError:
            return False

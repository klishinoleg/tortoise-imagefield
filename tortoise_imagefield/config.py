import os
from typing import Self, Optional

from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()


class Config:
    """
    Singleton class for managing configuration settings.

    Attributes:
        image_url (str): URL path for accessing uploaded images.
        image_dir (str): Local directory for storing uploaded images.
        s3_bucket (Optional[str]): AWS S3 bucket name.
        s3_region (Optional[str]): AWS S3 region.
        s3_access_key (Optional[str]): AWS S3 access key ID.
        s3_secret_key (Optional[str]): AWS S3 secret access key.
        s3_cdn_domain (Optional[str]): CloudFront or CDN domain for S3 images.
    """

    _instance: Self = None  # Singleton instance

    def __new__(cls):
        """
        Implements singleton pattern to ensure only one instance of Config exists.
        Initializes settings from environment variables.
        """
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)

            # Load configuration from environment variables
            cls._instance.image_dir = os.getenv("IMAGES_UPLOAD_DIR", "uploads")
            cls._instance.image_url = os.getenv("IMAGES_UPLOAD_URL", "uploads")
            cls._instance.s3_bucket = os.getenv("S3_BUCKET", None)
            cls._instance.s3_region = os.getenv("S3_REGION", None)
            cls._instance.s3_access_key = os.getenv("S3_ACCESS_KEY", None)
            cls._instance.s3_secret_key = os.getenv("S3_SECRET_KEY", None)
            cls._instance.s3_cdn_domain = os.getenv("S3_CDN_DOMAIN", None)

        return cls._instance  # Return singleton instance

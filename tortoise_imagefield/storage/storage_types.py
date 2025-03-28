import enum


class StorageTypes(enum.Enum):
    """
    Enum representing different storage backends for image handling.

    **Values:**
    - `LOCAL`: Stores images on the local filesystem.
    - `S3_AWS`: Stores images in an AWS S3 bucket.
    """
    LOCAL = "LOCAL"
    S3_AWS = "S3_AWS"

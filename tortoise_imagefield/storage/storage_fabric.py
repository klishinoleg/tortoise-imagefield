from typing import Type
from .storage_interface import StorageInterface
from .storage_types import StorageTypes
from .types import LocalStorage, S3AWSStorage
from ..config import Config

cfg = Config()


class StorageFabric:
    """
    Factory class for selecting the appropriate storage backend.

    This class provides a method to retrieve the correct storage implementation
    based on the specified storage type.
    """

    @classmethod
    def get_storage(cls, storage_type: StorageTypes) -> Type[StorageInterface]:
        """
        Returns the appropriate storage class based on the given storage type.

        **Parameters:**
        - `storage_type` (StorageTypes): The type of storage to use.
          Can be one of:
          - `StorageTypes.LOCAL`: Uses local file storage.
          - `StorageTypes.S3_AWS`: Uses AWS S3 storage.

        **Returns:**
        - `Type[StorageInterface]`: The corresponding storage class.

        **Raises:**
        - `ValueError`: If an unsupported storage type is provided.
        - `ValueError`: If S3 storage is selected but required credentials are missing.
        """
        if storage_type == StorageTypes.LOCAL:
            return LocalStorage

        if storage_type == StorageTypes.S3_AWS:
            # Ensure all required S3 credentials are provided
            if not all((cfg.s3_access_key, cfg.s3_bucket, cfg.s3_secret_key, cfg.s3_region)):
                raise ValueError("S3 access key, bucket, secret key, and region must be set")
            return S3AWSStorage

        # Raise an error if an unsupported storage type is used
        raise ValueError(f"Storage type {storage_type} is not supported")

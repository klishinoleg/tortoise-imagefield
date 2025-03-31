from typing import Tuple, Optional, Union, Type
from PIL import Image
from starlette.datastructures import UploadFile
from tortoise.exceptions import ValidationError
from .loaders import *
from .loader_interface import LoaderInterface
from ..config import Config

cfg = Config()


class LoaderAdapter(LoaderInterface):
    """
    Adapter class to dynamically select the appropriate image loader
    based on the input format (URL, Base64, or file upload).
    """

    @classmethod
    async def load(cls, value: Union[str, UploadFile]) -> Tuple[Image, Optional[str]]:
        """
        Determines the image format and loads the image using the appropriate loader.

        **Parameters:**
        - `value` (Union[str, UploadFile]): The input image, either a URL, Base64 string, or file.

        **Returns:**
        - `Tuple[Image, Optional[str]]`: The loaded image object and its filename (if applicable).

        **Raises:**
        - `ValidationError`: If the image format is invalid.
        """
        return await cls._get_loader(value).load(value)

    @classmethod
    def is_value_source(cls, value: Union[str, UploadFile], raise_error: bool = False) -> bool:
        return cls._get_loader(value, raise_error) is not None

    @classmethod
    def _get_none_or_raise(cls, msg: str, raise_error: bool = True) -> None:
        if raise_error:
            raise ValidationError(msg)
        return None

    @classmethod
    def _get_loader(cls, value: Union[str, UploadFile], raise_error=True) -> Optional[Type[LoaderInterface]]:
        if isinstance(value, str):
            if value.lower().startswith(("http://", "https://")):
                if cfg.s3_cdn_domain and cfg.s3_cdn_domain.lower() in value.lower():
                    return cls._get_none_or_raise("Load from self cdn error", raise_error)
                elif cfg.s3_bucket and cfg.s3_bucket.lower() in value.lower():
                    return cls._get_none_or_raise("Load from self bucket error")
                return UrlLoader
            elif value.startswith("data:"):
                return Base64Loader
            return cls._get_none_or_raise("Invalid image string format: it must start with 'http://' or 'data:'",
                                          raise_error)

        if isinstance(value, UploadFile):
            return UploadFileLoader
        return cls._get_none_or_raise("Invalid image format. Provide a valid URL, Base64 string, or an uploaded file.",
                                      raise_error)

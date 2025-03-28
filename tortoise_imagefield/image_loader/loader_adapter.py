from typing import Tuple, Optional, Union
from PIL import Image
from starlette.datastructures import UploadFile
from tortoise.exceptions import ValidationError
from .loaders import *
from .loader_interface import LoaderInterface


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

        if isinstance(value, str):
            if value.lower().startswith(("http://", "https://")):
                return await UrlLoader.load(value)
            elif value.startswith("data:"):
                return await Base64Loader.load(value)
            raise ValidationError("Invalid image string format: it must start with 'http://' or 'data:'")

        if isinstance(value, UploadFile):
            return await UploadFileLoader.load(value)

        raise ValidationError("Invalid image format. Provide a valid URL, Base64 string, or an uploaded file.")

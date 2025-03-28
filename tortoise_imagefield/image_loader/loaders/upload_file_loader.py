from typing import Tuple, Optional
from PIL import Image
from starlette.datastructures import UploadFile
from tortoise.exceptions import ValidationError
import io
from ..loader_interface import LoaderInterface


class UploadFileLoader(LoaderInterface):
    """
    Loader for handling image uploads from Starlette's `UploadFile`.

    This class is responsible for processing image files uploaded via FastAPI/Starlette.
    """

    @classmethod
    async def load(cls, value: UploadFile) -> Tuple[Image, Optional[str]]:
        """
        Asynchronously loads and processes an uploaded image file.

        **Parameters:**
        - `value` (UploadFile): The uploaded file to be processed.

        **Returns:**
        - `Tuple[Image, Optional[str]]`: A tuple containing:
          - `Image`: The loaded image object.
          - `Optional[str]`: The original filename of the uploaded file.

        **Raises:**
        - `ValidationError`: If the uploaded file is not a valid image.
        """
        try:
            file_content = await value.read()  # Asynchronously read file content
            image = Image.open(io.BytesIO(file_content))  # Convert bytes to an image
            return image, value.filename
        except Exception:
            raise ValidationError("Invalid image file.")

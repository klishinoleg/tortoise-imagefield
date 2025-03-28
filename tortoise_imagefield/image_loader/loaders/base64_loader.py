import base64
from io import BytesIO
from typing import Tuple, Optional
from PIL import Image
from tortoise.exceptions import ValidationError

from ..loader_interface import LoaderInterface


class Base64Loader(LoaderInterface):
    """
    Decodes a base64-encoded image string and processes it.

    This loader extracts the image from a base64-encoded string, validates it,
    and converts it into a PIL Image object.
    """

    @classmethod
    async def load(cls, value: str) -> Tuple[Image, Optional[str]]:
        """
        Asynchronously decodes a base64 image string and processes it.

        **Parameters:**
        - `value` (str): A base64-encoded image string (with or without a data URI header).

        **Returns:**
        - `Tuple[Image, Optional[str]]`: A tuple containing:
          - `Image`: The decoded and loaded image.
          - `Optional[str]`: `None`, since there is no filename for base64 images.

        **Raises:**
        - `ValidationError`: If the base64 string is invalid or the image cannot be loaded.
        """
        try:
            # Split the base64 string if it contains a data URI header
            if "," in value:
                header, encoded = value.split(",", 1)
            else:
                encoded = value  # No header present, assume raw base64 string

            # Decode base64 content
            image_data = base64.b64decode(encoded)

            # Convert bytes into a PIL Image
            image = Image.open(BytesIO(image_data))
            return image, None

        except (ValueError, IndexError):
            raise ValidationError("Invalid base64 image format.")

        except Exception:
            raise ValidationError("Invalid image file.")

import os
from io import BytesIO
from typing import Tuple, Optional
from urllib.parse import urlparse

import aiohttp
from PIL import Image
from tortoise.exceptions import ValidationError

from ..loader_interface import LoaderInterface


class UrlLoader(LoaderInterface):
    """
    Downloads and processes an image from a given URL asynchronously.

    This class retrieves an image over HTTP, validates it, and extracts its filename.
    """

    @classmethod
    async def load(cls, value: str) -> Tuple[Image, Optional[str]]:
        """
        Asynchronously downloads and processes an image from a URL.

        **Parameters:**
        - `value` (str): The URL of the image to download.

        **Returns:**
        - `Tuple[Image, Optional[str]]`: A tuple containing:
          - `Image`: The downloaded and loaded image.
          - `Optional[str]`: The filename extracted from the URL (if available).

        **Raises:**
        - `ValidationError`: If the image cannot be downloaded or is invalid.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(value) as response:
                    if response.status != 200:
                        raise ValidationError(f"Failed to download image: HTTP {response.status}")

                    file_content = await response.read()
                    image = Image.open(BytesIO(file_content))

                    # Extract filename from URL
                    parsed_url = urlparse(value)
                    filename = os.path.basename(parsed_url.path)

                    # Ensure filename has an extension
                    if filename and "." not in filename:
                        filename = None

                    return image, filename
        except Exception:
            raise ValidationError("Invalid image file or failed to download image.")

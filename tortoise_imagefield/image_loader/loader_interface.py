from abc import ABC, abstractmethod
from typing import Tuple, Optional, Union

from PIL import Image
from starlette.datastructures import UploadFile


class LoaderInterface(ABC):
    """
    Abstract base class for image loaders.

    Implementing classes must provide an asynchronous `load()` method
    that handles loading images from different sources.
    """

    @classmethod
    @abstractmethod
    async def load(cls, value: Union[str, UploadFile]) -> Tuple[Image, Optional[str]]:
        """
        Abstract method for loading images.

        **Parameters:**
        - `value` (Union[str, UploadFile]): The input image, which can be:
          - A URL (`http://...`, `https://...`).
          - A Base64-encoded string (`data:image/...`).
          - An uploaded file (`UploadFile` from Starlette).

        **Returns:**
        - `Tuple[Image, Optional[str]]`: A tuple containing:
          - The loaded `PIL.Image` object.
          - The filename (if available) or `None`.

        **Raises:**
        - `NotImplementedError`: If the method is not implemented in a subclass.
        """
        raise NotImplementedError

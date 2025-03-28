import uuid
from abc import ABC, abstractmethod
from typing import Optional, Self

from PIL import Image

from .crop_image import crop_image


class StorageInterface(ABC):
    """
    Abstract base class for image storage management.

    Defines a common interface for different storage implementations
    (e.g., Local Storage, AWS S3).

    **Attributes:**
    - `_cache_prefix` (str): Prefix for cached image directories.
    - `_filename` (str): The name of the stored image file.
    - `_img` (Optional[Image]): The loaded image instance.
    - `_field_dir` (str): The directory where the image is stored.
    - `_croped_filename` (Optional[str]): The filename of the cropped version of the image.
    - `_croped_img` (Optional[Image]): The cropped image instance.
    """
    _cache_prefix = "cache"
    _filename: str
    _img: Optional[Image] = None
    _field_dir: str
    _croped_filename: Optional[str] = None
    _croped_img: Optional[Image] = None

    def __init__(self, filename: str, field_dir: str, img: Optional[Image] = None):
        """
        Initializes the storage instance.

        **Parameters:**
        - `filename` (str): The name of the image file.
        - `field_dir` (str): The directory where the image is stored.
        - `img` (Optional[Image]): The image instance if it's being created (default: `None`).
        """
        self._filename = filename
        self._img = img
        self._field_dir = field_dir
        self._croped_filename = None
        self._croped_img = None

    @classmethod
    async def create(cls, img: Image, field_dir: str, filename: Optional[str] = None) -> Self:
        """
        Creates a new storage instance and saves the image.

        **Parameters:**
        - `img` (Image): The image to be stored.
        - `field_dir` (str): The directory where the image should be saved.
        - `filename` (Optional[str]): The name of the file (if not provided, a UUID-based filename is generated).

        **Returns:**
        - `Self`: An instance of the storage class.
        """
        ext = img.format.lower() if img.format else "png"
        if not filename:
            filename = f"{uuid.uuid4()}.{ext}"
        elif "." not in filename:
            filename += f".{ext}"
        storage = cls(filename, field_dir, img)
        await storage.save_image()
        return storage

    @classmethod
    def load(cls, filename: str, field_dir: str) -> Self:
        """
        Loads an image from storage.

        **Parameters:**
        - `filename` (str): The name of the file.
        - `field_dir` (str): The directory where the image is stored.

        **Returns:**
        - `Self`: An instance of the storage class.
        """
        return cls(filename, field_dir)

    @abstractmethod
    async def delete_image(self):
        """Deletes the stored image file."""
        raise NotImplementedError

    @abstractmethod
    def get_image_url(self) -> str:
        """Returns the public URL of the stored image."""
        raise NotImplementedError

    @abstractmethod
    def get_cached_url(self) -> str:
        """Returns the public URL of the cached (processed) image."""
        raise NotImplementedError

    @abstractmethod
    def get_image_path(self) -> str:
        """Returns the file system path to the stored image."""
        raise NotImplementedError

    @abstractmethod
    def get_cached_path(self) -> Optional[str]:
        """Returns the file system path to the cached (processed) image."""
        raise NotImplementedError

    @abstractmethod
    async def _load_image(self):
        """Loads the image from storage."""
        raise NotImplementedError

    @abstractmethod
    async def _save_cached_image(self):
        """Saves the processed (cached) version of the image."""
        raise NotImplementedError

    async def save_image(self):
        """
        Saves the image, ensuring unique filenames if needed.

        - If the filename already exists, it appends a numeric prefix (`1_`, `2_`, etc.).
        - Calls `_save_image()` to actually save the file.
        """
        n = 0
        base_filenae = "" + self._filename
        while await self._check_image_exists():
            n += 1
            self._filename = f"{n}_{base_filenae}"
        await self._save_image()

    @abstractmethod
    async def _check_image_exists(self) -> bool:
        """Checks if the image file already exists in storage."""
        raise NotImplementedError

    @abstractmethod
    async def _save_image(self):
        """Saves the image file to storage."""
        raise NotImplementedError

    @abstractmethod
    async def _check_cached_image(self) -> bool:
        """Checks if the processed (cached) image exists."""
        raise NotImplementedError

    def _get_cache_dir_name(self):
        """
        Generates a cache directory name based on the image filename.
        - Replaces `.` with `_` to ensure compatibility with file systems.
        **Returns:**
        - `str`: The directory name used for storing cached images.
        """
        return self._filename.replace(".", "_")

    async def crop_to_cache(self, width: int, height: Optional[int] = None, position: Optional[str] = None) -> Self:
        """
        Crops and caches the image.

        - If the requested crop size does not exist, it will be created.
        - Uses `_check_cached_image()` to determine if caching is needed.

        **Parameters:**
        - `width` (int): The width of the cropped image.
        - `height` (Optional[int]): The height of the cropped image (default: same as `width`).
        - `position` (Optional[str]): The cropping position (e.g., `"center"`, `"top"`, `"left"`).

        **Returns:**
        - `Self`: The updated storage instance with the cropped image cached.
        """
        if not self._filename:
            return self
        await self._load_image()
        if not self._img:
            return self
        self._croped_filename = f"{width}x{height or width}-{position}.webp"
        if not await self._check_cached_image():
            self._croped_img = crop_image(self._img, width, height or width, position)
            await self._save_cached_image()
        return self

    def get_filename(self):
        """
        Returns the filename of the stored image.

        **Returns:**
        - `str`: The filename of the stored image.
        """
        return self._filename

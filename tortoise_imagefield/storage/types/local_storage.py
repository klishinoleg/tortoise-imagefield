import asyncio
import os
import shutil
from io import BytesIO
import aiofiles
import aiofiles.os
from typing import Optional
from PIL import Image, UnidentifiedImageError
from ..storage_interface import StorageInterface
from ...config import Config

cfg = Config()


class LocalStorage(StorageInterface):
    """
    Local storage implementation for handling image uploads.

    This class provides methods for storing images on the local filesystem, retrieving them,
    deleting them, handling cached versions, and checking their existence.
    """

    def get_image_path(self) -> Optional[str]:
        """Returns the full filesystem path to the original image."""
        return self._get_file_path()

    def get_cached_path(self) -> Optional[str]:
        """Returns the full filesystem path of the cached (processed) image."""
        if not self._croped_filename:
            return None
        return os.path.join(self._get_cache_dir(), self._croped_filename)

    def get_cached_url(self) -> Optional[str]:
        """Returns the URL for the cached (processed) WebP image."""
        if not self._croped_filename:
            return None
        return f"/{cfg.image_url}/{self._field_dir}/{self._cache_prefix}/{self._get_cache_dir_name()}/{self._croped_filename}"

    def get_image_url(self) -> str:
        """Returns the URL for the original image."""
        return f"/{cfg.image_url}/{self._field_dir}/{self._filename}"

    async def delete_image(self):
        """
        Asynchronously deletes the original image and its cached versions from local storage.

        - Removes the original file if it exists.
        - Removes the cache directory if it exists.
        """
        file_path = self._get_file_path()
        if await aiofiles.os.path.exists(file_path):
            await aiofiles.os.remove(file_path)

        cache_dir = self._get_cache_dir()
        if await aiofiles.os.path.exists(cache_dir):
            await asyncio.to_thread(shutil.rmtree, cache_dir)

    @staticmethod
    async def _load_file(file_path: str) -> bytes:
        """
        Asynchronously reads a file from the given path.

        **Parameters:**
        - `file_path` (str): Path to the file.

        **Returns:**
        - `bytes`: File content.
        """
        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()

    async def _load_image(self):
        """
        Asynchronously loads the original image from local storage.

        - Reads the file content.
        - Checks if the file is empty.
        - Tries to open the image using Pillow.

        **Raises:**
        - `ValueError`: If the file is empty or cannot be identified as an image.
        """
        file_path = self._get_file_path()
        if not await aiofiles.os.path.exists(file_path):
            return

        content = await self._load_file(file_path)
        if not content:
            raise ValueError(f"File {file_path} is empty and cannot be loaded.")

        try:
            image = Image.open(BytesIO(content))
            image.load()  # Load the image into memory
            self._img = image
        except UnidentifiedImageError:
            raise ValueError(f"Failed to identify image format: {file_path}")

    async def _save_image(self):
        """
        Asynchronously saves the original image to the local storage directory.

        - Ensures the target directory exists.
        - Calls `_save_file()` to write the image to disk.
        """
        os.makedirs(self._get_field_dir_path(), exist_ok=True)
        if self._img:
            await self._save_file(self._img, self._get_file_path())

    async def _check_image_exists(self) -> bool:
        """Asynchronously checks if the original image exists in local storage."""
        return await aiofiles.os.path.exists(self._get_file_path())

    async def _save_cached_image(self):
        """
        Asynchronously saves the cached (processed) image to local storage.

        - Ensures that the processed image exists before saving.
        """
        if self._croped_img:
            await self._save_file(self._croped_img, self.get_cached_path())

    async def _check_cached_image(self) -> bool:
        """Asynchronously checks if the cached (processed) image exists."""
        await aiofiles.os.makedirs(self._get_cache_dir(), exist_ok=True)
        return await aiofiles.os.path.exists(self.get_cached_path())

    def _get_field_dir_path(self) -> str:
        """Returns the directory path where the original image is stored."""
        return os.path.join(cfg.image_dir, self._field_dir)

    def _get_file_path(self) -> Optional[str]:
        """Constructs the absolute file path for the original image."""
        if not self._filename:
            return None
        return os.path.join(self._get_field_dir_path(), self._filename)

    def _get_cache_dir(self) -> str:
        """Returns the directory path for cached (processed) images."""
        return os.path.join(self._get_field_dir_path(), self._cache_prefix, self._get_cache_dir_name())

    @staticmethod
    async def _save_file(img: Image, file_path: str):
        """
        Asynchronously saves an image to the given file path.

        - Uses a `BytesIO` buffer to store the image before writing it to disk.

        **Parameters:**
        - `img` (Image): The image to save.
        - `file_path` (str): The target file path.
        """
        buffer = BytesIO()
        img.save(buffer, format=img.format)
        buffer.seek(0)

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(buffer.getvalue())

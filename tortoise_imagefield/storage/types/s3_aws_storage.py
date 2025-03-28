from io import BytesIO
from typing import Optional
import aiohttp
import aioboto3
from PIL import Image
from ..storage_interface import StorageInterface
from ...config import Config

cfg = Config()


class S3AWSStorage(StorageInterface):
    _client = None

    @staticmethod
    def get_client():
        """
        Returns an asynchronous S3 client using aioboto3.
        Ensures that a new session is created per request.
        """
        session = aioboto3.Session()
        return session.client(
            "s3",
            aws_access_key_id=cfg.s3_access_key,
            aws_secret_access_key=cfg.s3_secret_key,
            region_name=cfg.s3_region,
        )

    async def delete_image(self):
        """
        Asynchronously deletes the original image and its cached versions from S3.

        - If the image exists, it is deleted from the S3 bucket.
        - If any cached versions exist, the corresponding folder is also deleted.
        """
        if self._filename:
            await self._delete_from_s3(image_key=self._get_image_key())
            await self._delete_folder_from_s3(folder_prefix=self._get_image_cache_folder_key())

    def get_image_url(self) -> Optional[str]:
        """
        Returns the public URL for the original image.

        - If CloudFront is configured, returns the CDN URL.
        - Otherwise, returns the standard S3 URL.
        """
        if self._filename:
            return self._get_s3_or_cdn_url(self._get_image_key())
        return None

    def get_cached_url(self) -> Optional[str]:
        """
        Returns the public URL for the cached WebP image.

        - Cached images are generated on demand and stored in a separate folder in S3.
        - Uses the same logic as `get_image_url()`, but for the processed image.
        """
        if self._croped_filename:
            return self._get_s3_or_cdn_url(self._get_image_cache_key())
        return None

    def get_image_path(self) -> Optional[str]:
        """
        Returns the S3 object key (path) for the original image.

        - This is used for internal file management rather than public URLs.
        """
        return self._get_image_key()

    def get_cached_path(self) -> Optional[str]:
        """
        Returns the S3 object key (path) for the cached image.

        - Used internally for processing and verifying stored images.
        """
        return self._get_image_cache_key()

    async def _check_image_exists(self) -> bool:
        """
        Asynchronously checks if the original image exists in S3.

        - This is useful for validating before generating URLs.
        """
        return await self._exist_on_s3(self._get_image_key())

    async def _load_image(self):
        """
        Asynchronously loads the original image from S3 or CloudFront.

        - Uses `aiohttp` for non-blocking HTTP requests.
        - If the request is successful (status 200), the image is stored in memory.
        """
        image_url = self._get_s3_or_cdn_url(self._get_image_key())

        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    self._img = Image.open(BytesIO(image_data))

    async def _save_cached_image(self):
        """
        Asynchronously uploads the cached (processed) image to S3.

        - Only runs if a cropped version of the image exists.
        - Uses `_save_to_s3()` to handle the upload process.
        """
        if self._croped_img and self._croped_filename:
            await self._save_to_s3(self._croped_img, self._get_image_cache_key())

    async def _save_image(self):
        """
        Uploads the original image to S3.

        - This is a synchronous operation.
        - Uses `_save_to_s3()` to handle the upload process.
        """
        if self._img and self._filename:
            await self._save_to_s3(self._img, self._get_image_key())

    async def _check_cached_image(self) -> bool:
        """
        Asynchronously checks if a cached (processed) version of the image exists in S3.

        - If a cached image exists, it avoids unnecessary reprocessing.
        """
        return await self._exist_on_s3(self._get_image_cache_key())

    def _get_image_key(self) -> Optional[str]:
        """
        Constructs the S3 object key (path) for the original image.

        Example:
        - `uploads/item_images/sample.jpg`
        """
        return "/".join([cfg.image_url, self._field_dir, self._filename]) if self._filename else None

    def _get_image_cache_folder_key(self) -> Optional[str]:
        """
        Constructs the S3 folder key for cached images.

        Example:
        - `uploads/item_images/cache`

        - If no filename exists, returns None.
        """
        if not self._filename:
            return None
        return "/".join([cfg.image_url, self._field_dir, self._cache_prefix, self._get_cache_dir_name()])

    def _get_image_cache_key(self) -> Optional[str]:
        """
        Constructs the S3 object key (path) for the cached WebP image.

        Example:
        - `uploads/item_images/cache/200x200-center.webp`

        - If no cropped filename exists, returns None.
        """
        if self._croped_filename:
            return "/".join([self._get_image_cache_folder_key(), self._croped_filename])
        return None

    async def _save_to_s3(self, image: Image, image_key: str):
        """
        Asynchronously saves an image to S3 with public-read ACL.

        **Parameters:**
        - `image` (Image): The image to upload.
        - `image_key` (str): The S3 object key.
        """
        buffer = BytesIO()

        # Ensure image format is set (default to PNG)
        image_format = image.format if image.format else "PNG"

        image.save(buffer, format=image_format)
        buffer.seek(0)

        async with self.get_client() as s3:
            await s3.upload_fileobj(
                buffer,
                Bucket=cfg.s3_bucket,
                Key=image_key,
                ExtraArgs={"ACL": "public-read"},
            )

    async def _delete_from_s3(self, image_key: str):
        """
        Asynchronously deletes a single object from S3.

        **Parameters:**
        - `image_key` (str): The S3 object key to delete.
        """
        async with self.get_client() as s3:
            await s3.delete_object(Bucket=cfg.s3_bucket, Key=image_key)

    async def _delete_folder_from_s3(self, folder_prefix: str):
        """
        Asynchronously deletes all objects inside a folder in S3.

        **Parameters:**
        - `folder_prefix` (str): The S3 folder prefix.
        """
        async with self.get_client() as s3:
            response = await s3.list_objects_v2(Bucket=cfg.s3_bucket, Prefix=folder_prefix)

            if "Contents" in response:
                delete_keys = [{"Key": obj["Key"]} for obj in response["Contents"]]
                await s3.delete_objects(Bucket=cfg.s3_bucket, Delete={"Objects": delete_keys})

    async def _exist_on_s3(self, image_key: str) -> bool:
        """
        Asynchronously checks if an object exists in S3.

        **Parameters:**
        - `image_key` (str): The S3 object key.

        **Returns:**
        - `bool`: `True` if the object exists, otherwise `False`.
        """
        try:
            async with self.get_client() as s3:
                await s3.head_object(Bucket=cfg.s3_bucket, Key=image_key)
            return True
        except Exception as e:
            return False

    @staticmethod
    def _get_s3_or_cdn_url(image_key: Optional[str]) -> Optional[str]:
        """
        Constructs a public URL for an S3 object.

        - Uses CloudFront if configured.
        - Falls back to the default S3 URL.

        **Parameters:**
        - `image_key` (Optional[str]): The S3 object key.

        **Returns:**
        - `Optional[str]`: Public URL of the image or None if the key is missing.
        """
        if not image_key:
            return None

        if cfg.s3_cdn_domain:
            return f"https://{cfg.s3_cdn_domain.rstrip('/')}/{image_key}"

        return f"https://{cfg.s3_bucket}.s3.{cfg.s3_region}.amazonaws.com/{image_key}"

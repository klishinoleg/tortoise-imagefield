from __future__ import annotations

import copy
import types
from typing import Type, Optional, Self, Set, Any

from slugify import slugify
from tortoise import Model
from tortoise.exceptions import IntegrityError, BaseORMException
from tortoise.fields import CharField

from .image_loader.loader_adapter import LoaderAdapter
from .storage.storage_fabric import StorageFabric
from .storage.storage_interface import StorageInterface
from .storage.storage_types import StorageTypes


class ImageField(CharField):
    """
    Custom Tortoise ORM field for handling image uploads.
    Supports file paths, base64 strings, and URLs.
    """
    _storage: Type[StorageInterface]
    _file_prefix: str = "__IMG_FILE__"
    _field_for_name: Optional[str] = None
    _directory_name: Optional[str] = None

    field_type = Optional[str]

    def __init__(self,
                 storage_type: StorageTypes = StorageTypes.LOCAL,
                 directory_name: Optional[str] = None,
                 field_for_name: Optional[str] = None, *args, **kwargs):
        """
        Initialize the ImageField.

        :param storage_type: Defines where images will be stored (local/S3).
        :param directory_name: Custom directory for image storage.
        :param field_for_name: Specifies a model field for slugifying filenames.
        """
        if not kwargs.get("max_length"):
            kwargs["max_length"] = 255
        super().__init__(*args, **kwargs)
        self._storage = StorageFabric.get_storage(storage_type=storage_type)
        self._field_for_name = field_for_name
        self._directory_name = directory_name

    def get_field_for_name(self) -> Optional[str]:
        """Returns the field used for slugifying filenames."""
        return self._field_for_name

    def get_storage(self) -> Type[StorageInterface]:
        """Returns the storage interface used by this field."""
        return self._storage

    def to_python_value(self, value: Any) -> Optional[str]:
        """
        Converts the database value to a Python value.

        - If the value contains `self._file_prefix`, it is removed.
        - This ensures that only the actual filename is returned for processing.
        - `self._file_prefix` is used to differentiate between a raw text input and a stored filename.
        """
        if isinstance(value, str) and self._file_prefix in value:
            return value.replace(self._file_prefix, "")
        return value

    def to_db_value(self, value: Optional[str], instance: type[Model] | Model) -> Optional[str]:
        """
        Prepares the value before storing it in the database.

        - If the value is a filename and does not contain `self._file_prefix`, it is added.
        - `self._file_prefix` helps distinguish a filename stored in the database from raw text values.
        """
        if value is None:
            return None
        if not isinstance(value, str):
            raise IntegrityError(f"Bad field value: {type(value)}")
        if self._file_prefix in value:
            return value
        return self._file_prefix + value

    def get_model_dir(self):
        """
        Returns the directory name based on the model's class name.
        This helps in organizing uploaded images by model type.
        """
        return self._directory_name or f"{self.model.__name__.lower()}_{self.model_field_name.lower()}_images"

    def get_for_dialect(self, *args, **kwargs):
        """
        Adds additional image-related methods dynamically to the model.
        """
        field_name = str(self.model_field_name)

        # Retrieves the image file name from the model instance
        def get_file_name(instance) -> Optional[str]:
            return getattr(instance, field_name)

        # Create attribute sets for tracking image fields
        get_image_fields = get_model_attr_access("_tif_image_fields")
        get_precreated_images = get_model_attr_access("_tif_precreated_images")
        get_images_for_deleted = get_model_attr_access("_tif_images_for_deleted")

        get_image_fields(self.model).add(field_name)

        async def get_webp_image(instance: Type[Model], width: int, height: int,
                                 position: str = "center", return_path: bool = False) -> Optional[str]:
            """
            Retrieves a cached WebP version of the image.

            - If the requested size is not cached, it will be created.
            - Supports cropping and resizing before returning the image.

            **Parameters:**
            - `instance` (Type[Model]): The model instance that contains the image field.
            - `width` (int): The desired width of the output image.
            - `height` (int): The desired height of the output image.
            - `position` (str, default="center"): The cropping position (`"center"`, `"top"`, `"left"`, etc.).
            - `return_path` (bool, default=False): If `True`, returns the file path instead of the image URL.

            **Returns:**
            - `Optional[str]`: The URL or file path of the cached WebP image, or `None` if the process fails.
            """
            storage = await (self.get_storage()
                             .load(get_file_name(instance), self.get_model_dir())
                             .crop_to_cache(width, height, position)
                             )
            if return_path:
                return storage.get_cached_path()
            return storage.get_cached_url()

        def get_image_path(instance: Type[Model]) -> Optional[str]:
            """Method to get the original image path (local or S3 key)"""
            return self.get_storage()(get_file_name(instance), self.get_model_dir()).get_image_path()

        def get_image_url(instance: Type[Model]) -> Optional[str]:
            """Method to get the original image URL"""
            return self.get_storage()(get_file_name(instance), self.get_model_dir()).get_image_url()

        def get_field_from_model(fn: str) -> Self:
            """Retrieves the field object from the model."""
            return getattr(self.model, "_meta").fields_map.get(fn)

        async def precreate_images(instance: Type[Model]):
            """
            Handles image creation before saving to the database.

            **IMPORTANT METHOD!**

            Iterates over all image fields of this type and replaces the original image with the name of the saved file.

            **Steps:**
            1. Loads the original image using the loader.
            2. Determines the file name if `field_for_name` is defined.
            3. Sends the file to the storage and replaces the image reference in `kwargs` with the saved file name.
            """
            for image_field_name in get_image_fields(self.model):
                field = get_field_from_model(image_field_name)
                if instance.pk and not next((f for f, iv in get_images_for_deleted(instance) if f == field), None):
                    continue
                value = getattr(instance, image_field_name)
                if not LoaderAdapter.is_value_source(value):
                    continue
                image, filename = await LoaderAdapter.load(value)
                field_for_name = field.get_field_for_name()
                if field_for_name and getattr(instance, field_for_name):
                    filename = slugify(getattr(instance, field_for_name))
                new_storage = await field.get_storage().create(image, field.get_model_dir(), filename)
                filename = new_storage.get_filename()
                setattr(instance, image_field_name, filename)
                get_precreated_images(instance).add((field, filename))

        async def clean_files(file_name: str, field: Self):
            """
            Deletes old images when updating or deleting an object.

            - Deletes the file by its name using the associated model field and file name.
            - Used in cases of updating, deleting, or when saving fails.
            """
            await field.get_storage()(file_name, field.get_model_dir()).delete_image()

        def setattr_wrapper(original_method):

            def set_attr(instance: Type[Model], key: str, value: Any):
                """
                Handles updating existing image references in the model.
                - This method is called during model initialization or when using `update_from_dict`.
                - It also checks for updated images and adds them to the deletion list if the save operation is successful.
                """
                if key in get_image_fields(instance):
                    field = get_field_from_model(key)
                    file_name = getattr(instance, key, None)
                    if isinstance(value, str) and (file_name is None or str(file_name) not in value):
                        if file_name is not None and not LoaderAdapter.is_value_source(file_name):
                            LoaderAdapter.is_value_source(value, raise_error=True)
                    if file_name != value and (LoaderAdapter.is_value_source(value) or value is None):
                        get_images_for_deleted(instance).add((field, file_name))
                return original_method(instance, key, value)

            return set_attr

        def save_wrapper(original_method):
            async def save(instance: Type[Model], *args, **kwargs):
                """
                Saves the instance and handles old image cleanup.

                - After a successful save, it removes images that have been updated.
                - In case of an error while saving the model, it deletes the newly created images before saving.
                """
                await precreate_images(instance)
                try:
                    result = await original_method(instance, *args, **kwargs)
                    for field, file_name in get_images_for_deleted(instance):
                        if file_name and getattr(instance, field.model_field_name) != file_name:
                            await clean_files(file_name, field)
                    get_images_for_deleted(instance).clear()
                    return result
                except BaseORMException as e:
                    for field, file_name in get_precreated_images(instance):
                        await clean_files(file_name, field)
                    get_precreated_images(instance).clear()
                    raise e

            return save

        def delete_wrapper(original_method):
            async def delete(instance: Type[Model], *args, **kwargs):
                """Deletes the instance and ensures images are removed."""
                result = await original_method(instance, *args, **kwargs)
                for fn in get_image_fields(instance):
                    file_name = getattr(instance, fn)
                    if file_name:
                        field = get_field_from_model(fn)
                        await clean_files(file_name, field)
                return result

            return delete

        # Dynamically add methods to the model
        setattr(self.model, f"get_{field_name}_webp", get_webp_image)
        setattr(self.model, f"get_{field_name}_url", get_image_url)
        setattr(self.model, f"get_{field_name}_path", get_image_path)

        # Override save/delete methods only if there are image fields
        if len(get_image_fields(self.model)) <= 1:
            setattr(self.model, f"save", save_wrapper(copy_method(self.model, "save")))
            setattr(self.model, f"delete", delete_wrapper(copy_method(self.model, "delete")))
            setattr(self.model, f"__setattr__", setattr_wrapper(copy_method(self.model, "__setattr__")))
        return super().get_for_dialect(*args, **kwargs)


def get_model_attr_access(attr_name: str):
    """
    Returns a function that retrieves or initializes a set attribute for a given model.

    :param attr_name: The name of the attribute to retrieve or initialize.
    :return: A lambda function that takes a model and returns a set[str].
    """
    return lambda model: _get_or_create_attr(model, attr_name)


def _get_or_create_attr(model: Type[Model], attr_name: str) -> Set[str] or Set[ImageField, str]:
    """
    Retrieves or initializes a set attribute for the given model.

    :param model: The model class.
    :param attr_name: The name of the attribute.
    :return: The attribute value, which is a set of strings.
    """
    if not hasattr(model, attr_name):
        setattr(model, attr_name, set())
    return getattr(model, attr_name)


def copy_method(cls, method_name):
    """
    Creates a copy of a class method by its name.

    :param cls: The class containing the method
    :param method_name: The name of the method to copy
    :return: A new method (copied)
    """
    if not hasattr(cls, method_name):
        raise AttributeError(f"Method '{method_name}' not found in class {cls.__name__}")

    method = getattr(cls, method_name)
    if not callable(method):
        raise TypeError(f"'{method_name}' is not a callable method in class {cls.__name__}")

    # Create a new function based on the method
    new_method = types.FunctionType(
        method.__code__,  # Original method code
        method.__globals__,  # Use original global variables
        name=method.__name__,  # Retain original method name
        argdefs=method.__defaults__,  # Set default arguments
        closure=method.__closure__  # Pass closures if any
    )

    return new_method

import enum
from typing import Optional
from PIL import Image


class CropPositions(enum.Enum):
    CENTER = "center"
    TOP = "top"
    LEFT = "left"
    BOTTOM = "bottom"
    RIGHT = "right"


def crop_image(img: Image, width: int, height: int, position: Optional[str]) -> Image:
    """
    Crops and resizes an image to the specified dimensions and saves it in WebP format.
    Uses a separate thread to avoid blocking the event loop.

    **Parameters:**
    - `img` (Image): The source image to be cropped and resized.
    - `width` (int): The desired width of the output image.
    - `height` (int): The desired height of the output image.
    - `position` (Optional[str]): The cropping position (e.g., `"center"`, `"top"`, `"left"`).
      If `None`, it defaults to `CropPositions.CENTER`.

    **Returns:**
    - `Image`: The processed image in WebP format.
    """
    return _process_image(img, width, height, position or CropPositions.CENTER)


def _process_image(img: Image, width: int, height: int, position: str):
    """
    Opens an image, resizes and crops it according to the given parameters,
    and saves the output in WebP format.

    **Parameters:**
    - `img` (Image): The source image to be processed.
    - `width` (int): The target width for the resized image.
    - `height` (int): The target height for the resized image.
    - `position` (str): The position for cropping (e.g., `"center"`, `"top"`, `"left"`).

    **Returns:**
    - `Image`: The cropped and resized image in WebP format.
    """

    img = img.convert("RGBA")  # Convert to RGB mode for better compatibility
    box = _calculate_box(img, width, height, position)  # Determine the cropping area
    new_img = img.resize((width, height), Image.Resampling.LANCZOS, box=box)  # Resize and crop
    new_img.format = "WEBP"
    return new_img


def _crop_image(img: Image.Image, width: int, height: int, position: str):
    """
    Crops the image based on the specified position.

    - If the image is smaller than the target dimensions, it returns the original image.
    - Supports cropping from the center, top, bottom, left, or right.

    **Parameters:**
    - `img` (Image.Image): The source image to be cropped.
    - `width` (int): The desired width of the output image.
    - `height` (int): The desired height of the output image.
    - `position` (str): The cropping position. Can be:
      - `"center"`: Crop from the center.
      - `"top"`: Crop from the top.
      - `"bottom"`: Crop from the bottom.
      - `"left"`: Crop from the left.
      - `"right"`: Crop from the right.

    **Returns:**
    - `Image.Image`: The cropped image or the original image if it's too small to crop.
    """
    if not isinstance(position, CropPositions):
        position = CropPositions(position)
    img_width, img_height = img.size
    if img_width < width or img_height < height:
        return img  # Return original if it's too small to crop

    left = 0
    top = 0

    if position == CropPositions.CENTER:
        left = (img_width - width) // 2
        top = (img_height - height) // 2
    elif position == CropPositions.TOP:
        left = (img_width - width) // 2
        top = 0
    elif position == CropPositions.BOTTOM:
        left = (img_width - width) // 2
        top = img_height - height
    elif position == CropPositions.LEFT:
        left = 0
        top = (img_height - height) // 2
    elif position == CropPositions.RIGHT:
        left = img_width - width
        top = (img_height - height) // 2

    right = left + width
    bottom = top + height

    return img.crop((left, top, right, bottom))  # Return cropped image


def _calculate_box(img: Image.Image, width: int, height: int, position: str) -> tuple[float, float, float, float]:
    """
    Calculates the cropping box for resizing an image while maintaining aspect ratio.

    - Adjusts the cropping area based on the given position.
    - Ensures that the final image matches the target aspect ratio.

    **Parameters:**
    - `img` (Image.Image): The input image to be cropped.
    - `width` (int): The target width of the output image.
    - `height` (int): The target height of the output image.
    - `position` (str): The cropping position. Can be:
      - `"center"`: Crop from the center.
      - `"top"`: Crop from the top.
      - `"bottom"`: Crop from the bottom.
      - `"left"`: Crop from the left.
      - `"right"`: Crop from the right.

    **Returns:**
    - `tuple[float, float, float, float]`: A tuple `(left, top, right, bottom)` defining the cropping box.
    """
    if not isinstance(position, CropPositions):
        position = CropPositions(position)
    img_width, img_height = img.size
    aspect_ratio_img = img_width / img_height
    aspect_ratio_target = width / height

    # Determine the new dimensions based on aspect ratio
    if aspect_ratio_img > aspect_ratio_target:
        # Image is wider than target -> adjust width
        new_width = int(img_height * aspect_ratio_target)
        new_height = img_height
    else:
        # Image is taller than target -> adjust height
        new_width = img_width
        new_height = int(img_width / aspect_ratio_target)

    # Default cropping position calculations
    left = (img_width - new_width) // 2 if position in [CropPositions.CENTER, CropPositions.TOP,
                                                        CropPositions.BOTTOM] else 0
    top = (img_height - new_height) // 2 if position in [CropPositions.CENTER, CropPositions.LEFT,
                                                         CropPositions.RIGHT] else 0

    # Adjust cropping based on position
    if position == CropPositions.TOP:
        top = 0
    elif position == CropPositions.BOTTOM:
        top = img_height - new_height
    elif position == CropPositions.LEFT:
        left = 0
    elif position == CropPositions.RIGHT:
        left = img_width - new_width

    # Calculate final coordinates
    right = left + new_width
    bottom = top + new_height

    return left, top, right, bottom

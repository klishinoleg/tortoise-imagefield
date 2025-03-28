# Tortoise ImageField

Tortoise ImageField is an **image storage solution** for Tortoise ORM that supports **file uploads, Base64 encoding, and
external URLs**. It allows storing images **locally or in AWS S3 + CloudFront**, and includes **caching, cropping, and
WebP conversion** for optimized performance.

## ✨ Features

- **Supports multiple input formats:** File Uploads, Base64, and external URLs.
- **Storage options:** Local filesystem or AWS S3 with CloudFront.
- **Automatic caching and WebP conversion** to optimize image delivery.
- **Built-in cropping support** to generate resized images on demand.
- **Automatic filename renaming and slugify** based on a selected model field.
- **Asynchronous interaction with S3** for efficient uploads, deletions, and retrievals.
- **Fully asynchronous image processing** for non-blocking operations and better scalability.

---


## 📌 Installation

```sh
pip install tortoise-imagefield
```

---

## 🚀 Quick Start

### Define a Model with `ImageField`

```python
from tortoise import fields, Model
from tortoise_imagefield import ImageField, StorageTypes


class Item(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    image = ImageField()  # Store locally
    s3_image = ImageField(storage_type=StorageTypes.S3_AWS)  # Store in AWS S3
    image_ugc = ImageField(directory_name="ugc", field_for_name="name")
```

## 🛠 ImageField Parameters

| Parameter            | Description                                                                              | Default               |
|----------------------|------------------------------------------------------------------------------------------|-----------------------|
| **`storage_type`**   | Defines the storage backend (`StorageTypes.LOCAL` or `StorageTypes.S3_AWS`).             | `StorageTypes.LOCAL`  |
| **`directory_name`** | Custom directory name for storing images. If not set, defaults to `{class_name}_images`. | `{class_name}_images` |
| **`field_for_name`** | Specifies a model field that will be used to generate a slugified filename.              | `None`                |

### Automatically Added Methods in Models

When using `ImageField`, the following **helper methods** are dynamically added to your model, based on the field name.

### **🔹 Generated Methods**

| Method Name             | Description                                                                | Parameters                                                                                                                                                                                                                                        |
|-------------------------|----------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `get_{field_name}_webp` | Returns the WebP-optimized cached image URL.                               | `width: int` – Desired width <br> `height: int` – Desired height <br> `position: str = "center"` – Cropping position (`"center"`, `"top"`, `"left"`) <br> `return_path: bool = False` – If `True`, returns the **local path** instead of the URL. |
| `get_{field_name}_url`  | Returns the original uploaded image URL.                                   | _No parameters_                                                                                                                                                                                                                                   |
| `get_{field_name}_path` | Returns the original file path (for local storage) or S3 key (for AWS S3). | _No parameters_                                                                                                                                                                                                                                   |

---

## Image Processing

### Crop & Convert to WebP (Cached)

```python
item = await Item.get(id=1)
cached_image_webp = await item.get_image_webp(200, 200)
cached_s3_image_webp = await item.get_image_webp(100, 100)
```

---

### **🔹 Example Usage**

Assume the model has an `ImageField` named `image`:

```python
item = await Item.get(id=1)

# Get WebP-optimized URL (resized to 200x200)
webp_url = await item.get_image_webp(200, 200)
print(webp_url)  # Example: "https://cdn.example.com/images/image_200x200.webp"

# Get the original image URL
original_url = await item.get_image_url()
print(original_url)  # Example: "https://s3.example.com/uploads/image.jpg"

# Get the file path (local) or S3 key
image_path = await item.get_image_path()
print(image_path)  # Example: "/uploads/image.jpg" or "s3://bucket-name/uploads/image.jpg"
```

### Upload an Image

#### Upload via **File Upload**

```python
await Item.create(name="Test Item", image=file)
```

#### Upload via **Base64 string**

```python
await Item.create(name="Test Item", image="data:image/png;base64,iVBORw...")
```

#### Upload via **External URL**

```python
await Item.create(name="Test Item", image="https://example.com/image.jpg")
```

#### Upload via **Fast API**

```python
@app.post("/upload/")
async def upload_image(
        name: str = Form(...),
        image: UploadFile = File(...),
        s3_image: UploadFile = File(...)):
    """Handles image upload and saves it to the database with Upload File."""
    item = await Item.create(name=name, image=image, s3_image=s3_image)
    return {"id": item.id,
            "name": item.name,
            "image_url": await item.get_image_webp(200, 200),
            "s3_image_url": await item.get_s3_image_webp(250, 250)
            }


@app.post("/items/")
async def create_item(request: Request):
    """Handles image upload and saves it to the database with base64 or URL."""
    data = await request.json()
    item = await Item.create(**data)
    return {"id": item.id,
            "name": item.name,
            "image_url": await item.get_image_webp(200, 200),
            "s3_image_url": await item.get_s3_image_webp(150)
            }
```

---

## 🔧 Configuration via `.env` and Manual Settings

### 📂 `.env` File Configuration

You can configure storage settings using an `.env` file:

```ini
DATABASE_URL = sqlite://db.sqlite3
IMAGES_UPLOAD_DIR = uploads
IMAGES_UPLOAD_URL = uploads
S3_BUCKET =
S3_REGION =
S3_ACCESS_KEY =
S3_SECRET_KEY =
S3_CDN_DOMAIN =
```

The package **uses public access for S3**, as it is intended to be a simple storage **solution for public images**.

📖 For a complete guide, see [S3 Configuration](S3config.md).

#### Make sure to load these variables in your application:

```python
from dotenv import load_dotenv
import os

load_dotenv()

print(os.getenv("S3_BUCKET"))  # Prints the configured S3 bucket

```

### ⚙️ Manual Configuration via Config

You can also configure the library manually:

```python
from tortoise_imagefield import Config

cfg = Config()
cfg.image_dir = "app/uploads"
cfg.image_url = "static"
```

#### Config Class:

```python
class Config:
    image_url: str
    image_dir: str
    s3_bucket: Optional[str]
    s3_region: Optional[str]
    s3_access_key: Optional[str]
    s3_secret_key: Optional[str]
    s3_cdn_domain: Optional[str]

```

## 📜 License

This project is licensed under the **MIT License**.

🚀 **Now you're ready to optimize image handling with Tortoise ORM!**
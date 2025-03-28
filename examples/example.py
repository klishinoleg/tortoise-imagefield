from typing import Optional, Self
from fastapi import FastAPI, File, UploadFile, Form, Request
from starlette.staticfiles import StaticFiles
from tortoise.contrib.fastapi import register_tortoise
from tortoise.models import Model
from tortoise import fields
import os
from dotenv import load_dotenv
import uvicorn
from tortoise_imagefield.config import Config
from tortoise_imagefield import ImageField
from tortoise_imagefield.storage.storage_types import StorageTypes
from tortoise.contrib.pydantic import PydanticModel

# Load environment variables
load_dotenv()
cfg = Config()
app = FastAPI()
app.mount("/" + cfg.image_url, StaticFiles(directory=cfg.image_dir), name="upload")


# Define the database model
class Item(Model):
    """
    Item model with different image storage options.
    - `image`: Stored locally
    - `s3_image`: Stored in AWS S3
    - `s3_image_ugc`: Stored in AWS S3 with custom directory and filename slugification
    """
    id = fields.IntField(pk=True)  # Primary key
    name = fields.CharField(max_length=255)  # Name field
    ugc_name = fields.CharField(max_length=255)  # Additional field for user-generated content naming
    image = ImageField(field_for_name="name", directory_name="images")  # Local image storage
    s3_image = ImageField(storage_type=StorageTypes.S3_AWS)  # S3 image storage
    s3_image_ugc = ImageField(storage_type=StorageTypes.S3_AWS, directory_name="ugc",
                              field_for_name="ugc_name")  # S3 with custom path

    @property
    async def image_cache(self) -> Optional[str]:
        """Returns a cached WebP version of the locally stored image."""
        return await self.get_image_webp(200, 200)

    @property
    async def s3_image_cache(self):
        """Returns a cached WebP version of the S3 stored image."""
        return await self.get_s3_image_webp(50, 50)


# Define the schema for API responses
class ItemSchema(PydanticModel):
    """Pydantic model for serializing the `Item` model data."""
    id: int
    name: str
    ugc_name: str
    image_cache: Optional[str]
    s3_image_cache: Optional[str]
    ugc_image: Optional[str]

    @classmethod
    async def from_tortoise_orm(cls, obj: Item) -> Self:
        """
        Converts an Item model instance into a Pydantic response schema.
        This includes generating URLs for WebP image caching.
        """
        return cls(
            id=obj.id,
            name=obj.name,
            ugc_name=obj.ugc_name,
            image_cache=await obj.image_cache,
            s3_image_cache=await obj.s3_image_cache,
            ugc_image=obj.get_s3_image_ugc_url(),
        )

    class Config:
        """Configuration to link the schema with the original Tortoise model."""
        orig_model = Item


# Register Tortoise ORM with FastAPI
register_tortoise(
    app,
    db_url=os.getenv("DATABASE_URL", "sqlite://db.sqlite3"),
    modules={"models": ["example"]},
    generate_schemas=True,
    add_exception_handlers=True,
)


@app.post("/upload/")
async def upload_image(
        name: str = Form(...),
        ugc_name: str = Form(...),
        image: UploadFile = File(...),
        s3_image: UploadFile = File(...),
        s3_image_ugc: UploadFile = File(...)
):
    """
    Handles image upload via form-data and saves it to the database.
    - `image`: Local storage
    - `s3_image`: AWS S3 storage
    - `s3_image_ugc`: AWS S3 storage with user-defined naming
    """
    item = await Item.create(
        name=name, ugc_name=ugc_name, image=image, s3_image=s3_image, s3_image_ugc=s3_image_ugc
    )
    return await ItemSchema.from_tortoise_orm(item)


@app.post("/items/")
async def create_item(request: Request):
    """
    Creates an `Item` instance from JSON request data.
    """
    data = await request.json()
    item = await Item.create(**data)
    return await ItemSchema.from_tortoise_orm(item)


@app.get("/items/{item_id}/")
async def get_item(item_id: int):
    """
    Fetches a single item by its ID.
    """
    item = await Item.get_or_none(id=item_id)
    if not item:
        return {"error": "Item not found"}
    return await ItemSchema.from_tortoise_orm(item)


@app.get("/items/")
async def get_items():
    """
    Fetches all items stored in the database.
    """
    items = await Item.all()
    return [await ItemSchema.from_tortoise_orm(item) for item in items]


if __name__ == "__main__":
    # Run the FastAPI application with Uvicorn
    uvicorn.run("example:app", host="0.0.0.0", port=8020)

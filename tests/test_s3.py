import base64
import os
import shutil
import pytest
import requests
from PIL import Image
from fastapi import FastAPI, File, Form, Request, UploadFile, HTTPException
from fastapi.testclient import TestClient
from slugify import slugify
from tortoise import Tortoise
from tortoise.exceptions import IntegrityError
from tests.helpers import print_func_commentary, path_join, check_image_url
from tests.models import ItemS3Model
from tests.s3_helper import S3Helper
from tortoise_imagefield.config import Config

cfg = Config()
s3_helper = S3Helper()

app = FastAPI()


@app.post("/upload/")
async def upload_image(request: Request, name: str = Form(...), image: UploadFile = File(...)):
    """Handles image upload and saves it to the database."""
    item = await ItemS3Model.create(name=name, s3_image=image)
    return {"id": item.id, "name": item.name, "image_url": await item.get_s3_image_webp(200, 200)}


@app.post("/item/{item_id}/")
async def update_item(request: Request, item_id: int):
    """Handles image upload and saves it to the database."""
    item = await ItemS3Model.get_or_none(id=item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="ItemModel not found")
    await item.update_from_dict(await request.json())
    await item.save()
    return {
        "id": item.id, "name": item.name,
        "image_url": await item.get_s3_image_webp(200, 200),
        "avatar_url": await item.get_s3_avatar_webp(50, 50)
    }


@app.post("/create/")
async def create_item(request: Request):
    """Handles image upload and saves it to the database."""
    item = await ItemS3Model.create(**await request.json())
    return {
        "id": item.id, "name": item.name,
        "image_url": await item.get_s3_image_webp(200, 200),
        "avatar_url": await item.get_s3_avatar_webp(50, 50)
    }


@pytest.fixture(scope="module", autouse=True)
async def initialize_db():
    """Initialize Tortoise ORM for async tests."""
    if not cfg.s3_bucket or not cfg.s3_access_key or not cfg.s3_region or not cfg.s3_access_key:
        pytest.skip("S3 bucket or S3 key or S3 region not set")
    print(f"🔹 Test uploads directory: {cfg.image_dir}")
    s3_helper.clear()
    if os.path.exists(path_join("test_db.sqlite3")):
        os.remove(path_join("test_db.sqlite3"))
        print(f"🗑️ Test database has been deleted.")
    await Tortoise.init(
        db_url="sqlite://tests/test_db.sqlite3",
        modules={"models": ["tests.models"]}
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()


client = TestClient(app)


@pytest.mark.asyncio
async def test_image_upload_and_cache():
    """Tests S3 image upload and WebP caching for different input types."""
    print_func_commentary()
    test_cases = [
        {"name": "File Upload", "image": ("image.png", open(path_join("image.png"), "rb"), "image/png")},
        {"name": "Base64 Upload",
         "s3_image": f"data:image/jpeg;base64,{base64.b64encode(open(path_join('image.png'), 'rb').read()).decode()}"},
        {"name": "URL Upload", "s3_image": "https://picsum.photos/500"},
    ]

    for case in test_cases:
        # Upload the image
        if isinstance(case.get("image"), tuple):  # File case
            response = client.post("/upload/", files={"image": case["image"]}, data={"name": case["name"]})
        else:
            response = client.post("/create/", json=case)

        assert response.status_code == 200, f"✗ {case['name']} - Upload failed"
        print(f"✓ {case['name']} - Upload successful")

        item_data = response.json()

        # Fetch the uploaded item
        item = await ItemS3Model.get_or_none(id=item_data["id"])
        assert item is not None, f"✗ {case['name']} - ItemModel not found in database"
        print(f"✓ {case['name']} - ItemModel retrieved from database:")
        print({"id": item.id, "name": item.name, "image": item.s3_image})
        assert item.name == case["name"], f"✗ {case['name']} - Name mismatch"
        print(f"✓ {case['name']} - Name matches")

        # Get WebP cached image
        webp_url = await item.get_s3_image_webp(100, 100)
        assert webp_url is not None, f"✗ {case['name']} - WebP image URL is None"
        print(f"✓ {case['name']} - WebP image URL generated")

        webp_path = await item.get_s3_image_webp(100, 100, return_path=True)
        assert webp_path is not None, f"✗ {case['name']} - WebP image path is None"
        print(f"✓ {case['name']} - WebP image path found")

        check_image_url(requests, webp_url, case["name"] + " Webp")
        file_path = item.get_s3_image_path()

        # Verify the file exists
        assert s3_helper.check_exists(file_path)
        print(f"{file_path} is exists")

        # Verify the cache file exists
        assert s3_helper.check_exists(webp_path)
        print(f"{webp_path} is exists")
        print(f"✓ {case['name']} - passed successfully!")
    print("All test cases passed successfully!")


@pytest.mark.asyncio
async def test_update() -> None:
    """Tests S3 update function."""
    print_func_commentary()
    item = await ItemS3Model.get_or_none(pk=1)
    print(f"✓ Retrieved item with ID {item.id}")

    image_path = item.get_s3_image_path()
    assert s3_helper.check_exists(image_path)
    print(f"{image_path} is exists")

    new_image_data = {"name": "URL Upload New", "s3_image": "https://picsum.photos/500"}
    response = client.post(f"/item/{item.id}", json=new_image_data)
    assert response.status_code == 200, f"✗ Update request failed with status {response.status_code}"
    print("✓ Update request successful")

    data = response.json()
    print(data)
    assert requests.get(data.get("image_url")).status_code == 200, "✗ Updated image URL is not accessible"
    print("✓ Updated image URL is accessible")

    new_item = await ItemS3Model.get_or_none(pk=1)
    print({"id": new_item.id, "name": new_item.name, "image": new_item.s3_image})
    assert new_item.name == new_image_data.get("name"), "✗ Name was not updated correctly"
    print(f"✓ Name updated successfully: {new_item.name}")

    assert item.name != new_item.name, "✗ Old and new names are identical"
    print("✓ Name changed from old to new")

    assert item.s3_image != new_item.s3_image, "✗ Old and new images are identical"
    print("✓ Image path changed")

    assert not s3_helper.check_exists(item.get_s3_image_path())
    print(f"{item.get_s3_image_path()} is not exist (deleted)")

    webp_url = await item.get_s3_image_webp(100, 100)
    if webp_url:
        assert client.get(webp_url).status_code == 404, "✗ WebP cache should be removed but is still accessible"
    print("✓ WebP cache was successfully removed")

    print(f"✓ Test update completed for item ID {item.id}")


@pytest.mark.asyncio
async def test_delete():
    """Test S3 images after the object deleted"""
    print_func_commentary()
    item = await ItemS3Model.get_or_none(pk=1)
    print(f"✓ Delete ItemModel with ID {item.id} test started")

    image_path = item.get_s3_image_path()
    cache_path = await item.get_s3_image_webp(100, 100, return_path=True)

    assert s3_helper.check_exists(image_path)
    print(f"{image_path} is exists")

    assert s3_helper.check_exists(cache_path)
    print(f"{cache_path} is exists")

    await item.delete()
    print(f"✓ ItemModel with ID {item.id} deleted")

    assert not s3_helper.check_exists(image_path)
    print(f"{image_path} has been deleted")

    assert not s3_helper.check_exists(cache_path)
    print(f"{cache_path} has been deleted")

    print(f"✓ Delete test completed for item ID {item.id}")


@pytest.mark.asyncio
async def test_required():
    """Test case for S3 required, slugify and directory name."""
    print_func_commentary()
    with_avatar_data = {
        "name": "Image with avatar",
        "s3_image": "https://picsum.photos/500",
        "s3_avatar": "https://picsum.photos/100"
    }
    without_image_data = {"name": "Bad data"}
    print("✓ Testing creation without image (should fail)...")
    with pytest.raises(IntegrityError):
        client.post("/create/", json=without_image_data)

    print("✓ Expected IntegrityError raised successfully")

    print("✓ Testing creation with image and avatar...")
    response = client.post("/create/", json=with_avatar_data)
    assert response.status_code == 200, "✗ Failed to create item with image and avatar"
    print("✓ ItemModel with image and avatar created successfully")

    data = response.json()
    assert data.get("image_url") is not None, "✗ Image URL is missing"
    print(f"✓ Image URL found: {data.get('image_url')}")
    check_image_url(requests, data.get("image_url"), "Image", (200, 200))

    assert data.get("avatar_url") is not None, "✗ Avatar URL is missing"
    print(f"✓ Avatar URL found: {data.get('avatar_url')}")
    check_image_url(requests, data.get("avatar_url"), "Avatar", (50, 50))
    assert "/avatars/" in data.get("avatar_url"), "✗ 'avatars' in Avatar URL is missing"
    print(f"✓ 'avatars' in Avatars URL")
    assert slugify(with_avatar_data.get("name")) in data.get("avatar_url")
    print(slugify(with_avatar_data.get("name")), "in avarar url")


@pytest.mark.asyncio
async def test_doubles():
    """Check images doubles with similar names"""
    print_func_commentary()
    case = {"name": "File Upload", "image": ("image.png", open(path_join("image.png"), "rb"), "image/png")}
    response_1 = client.post("/upload/", files={"image": case["image"]}, data={"name": case["name"]})
    response_2 = client.post("/upload/", files={"image": case["image"]}, data={"name": case["name"]})
    data_1 = response_1.json()
    data_2 = response_2.json()
    assert data_1.get("name") == data_2.get("name"), "✗ Names are not identical"
    print("✓ Names are identical")
    assert data_1.get("image_url") != data_2.get("image_url"), "✗ Images doubles"
    print(data_1.get("image_url"))
    print(data_2.get("image_url"))
    print(f"✓ Images are difference")

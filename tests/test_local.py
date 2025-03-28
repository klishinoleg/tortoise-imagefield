import base64
import os
import shutil
import pytest
from PIL import Image
from fastapi import FastAPI, File, Form, Request, UploadFile, HTTPException
from fastapi.testclient import TestClient
from slugify import slugify
from tortoise import Tortoise
from tortoise.exceptions import IntegrityError
from tests.helpers import path_join, check_file, print_func_commentary, check_image_url
from tests.models import ItemModel
from fastapi.staticfiles import StaticFiles
from tortoise_imagefield import Config

cfg = Config()
cfg.image_dir = path_join("uploads")
upload_dir = cfg.image_dir

app = FastAPI()

if not os.path.exists(upload_dir):
    os.mkdir(upload_dir)
app.mount("/" + cfg.image_url, StaticFiles(directory=upload_dir), name="upload")


@app.post("/upload/")
async def upload_image(request: Request, name: str = Form(...), image: UploadFile = File(...)):
    """Handles image upload and saves it to the database."""
    item = await ItemModel.create(name=name, image=image)
    return {"id": item.id, "name": item.name, "image_url": await item.get_image_webp(200, 200)}


@app.post("/item/{item_id}/")
async def update_item(request: Request, item_id: int):
    """Handles image upload and saves it to the database."""
    item = await ItemModel.get_or_none(id=item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="ItemModel not found")
    await item.update_from_dict(await request.json())
    await item.save()
    return {
        "id": item.id, "name": item.name,
        "image_url": await item.get_image_webp(200, 200),
        "avatar_url": await item.get_avatar_webp(50, 50)
    }


@app.post("/create/")
async def create_item(request: Request):
    """Handles image upload and saves it to the database."""
    item = await ItemModel.create(**await request.json())
    return {
        "id": item.id, "name": item.name,
        "image_url": await item.get_image_webp(200, 200),
        "avatar_url": await item.get_avatar_webp(50, 50)
    }


@pytest.fixture(scope="module", autouse=True)
async def initialize_db():
    """Initialize Tortoise ORM for async tests."""
    print(f"🔹 Test uploads directory: {cfg.image_dir}")
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)
        print(f"🗑️ Directory {upload_dir} has been deleted after test.")

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
    """Tests image upload and WebP caching for different input types."""
    print_func_commentary()
    test_cases = [
        {"name": "File Upload", "image": ("image.png", open(path_join("image.png"), "rb"), "image/png")},
        {"name": "Base64 Upload",
         "image": f"data:image/jpeg;base64,{base64.b64encode(open(path_join('image.png'), 'rb').read()).decode()}"},
        {"name": "URL Upload", "image": "https://picsum.photos/500"},
    ]

    for case in test_cases:
        # Upload the image
        if isinstance(case["image"], tuple):  # File case
            response = client.post("/upload/", files={"image": case["image"]}, data={"name": case["name"]})
        else:
            response = client.post("/create/", json=case)

        assert response.status_code == 200, f"✗ {case['name']} - Upload failed"
        print(f"✓ {case['name']} - Upload successful")

        item_data = response.json()

        # Fetch the uploaded item
        item = await ItemModel.get_or_none(id=item_data["id"])
        assert item is not None, f"✗ {case['name']} - ItemModel not found in database"
        print(f"✓ {case['name']} - ItemModel retrieved from database:")
        print({"id": item.id, "name": item.name, "image": item.image})
        assert item.name == case["name"], f"✗ {case['name']} - Name mismatch"
        print(f"✓ {case['name']} - Name matches")

        # Get WebP cached image
        webp_url = await item.get_image_webp(100, 100)
        assert webp_url is not None, f"✗ {case['name']} - WebP image URL is None"
        print(f"✓ {case['name']} - WebP image URL generated")

        webp_path = await item.get_image_webp(100, 100, return_path=True)
        assert webp_path is not None, f"✗ {case['name']} - WebP image path is None"
        print(f"✓ {case['name']} - WebP image path found")

        check_image_url(client, webp_url, case["name"] + " Webp")
        file_path = item.get_image_path()

        # Verify the file exists
        check_file(file_path, "Image")

        # Verify the cache file exists
        check_file(webp_path, "Webp path")

        # Verify the cache file has correct dimensions
        with Image.open(webp_path) as img:
            assert img.size == (100, 100), f"✗ {case['name']} - WebP image size incorrect"
            print(f"✓ {case['name']} - WebP image has correct size (100x100)")

        print(f"✓ {case['name']} - passed successfully!")


@pytest.mark.asyncio
async def test_update() -> None:
    """Tests update function."""
    print_func_commentary()
    item = await ItemModel.get_or_none(pk=1)
    print(f"✓ Retrieved item with ID {item.id}")

    image_path = item.get_image_path()
    check_file(image_path, "Original image")

    new_image_data = {"name": "URL Upload New", "image": "https://picsum.photos/500"}
    response = client.post(f"/item/{item.id}", json=new_image_data)
    assert response.status_code == 200, f"✗ Update request failed with status {response.status_code}"
    print("✓ Update request successful")

    data = response.json()
    assert client.get(data.get("image_url")).status_code == 200, "✗ Updated image URL is not accessible"
    print("✓ Updated image URL is accessible")

    new_item = await ItemModel.get_or_none(pk=1)
    print({"id": new_item.id, "name": new_item.name, "image": new_item.image})
    assert new_item.name == new_image_data.get("name"), "✗ Name was not updated correctly"
    print(f"✓ Name updated successfully: {new_item.name}")

    assert item.name != new_item.name, "✗ Old and new names are identical"
    print("✓ Name changed from old to new")

    assert item.image != new_item.image, "✗ Old and new images are identical"
    print("✓ Image path changed")

    check_file(item.get_image_path(), "Image (Updated)", False)

    webp_url = await item.get_image_webp(100, 100)
    if webp_url:
        assert client.get(webp_url).status_code == 404, "✗ WebP cache should be removed but is still accessible"
    print("✓ WebP cache was successfully removed")

    print(f"✓ Test update completed for item ID {item.id}")


@pytest.mark.asyncio
async def test_delete():
    """Test images after the object deleted"""
    print_func_commentary()
    item = await ItemModel.get_or_none(pk=2)
    print(f"✓ Delete ItemModel with ID {item.id} test started")

    image_path = item.get_image_path()
    cache_path = await item.get_image_webp(100, 100, return_path=True)

    check_file(image_path, "Image")

    check_file(cache_path, "Cache")

    await item.delete()
    print(f"✓ ItemModel with ID {item.id} deleted")

    check_file(image_path, "Image", False)

    check_file(cache_path, "Cache", False)

    print(f"✓ Delete test completed for item ID {item.id}")


@pytest.mark.asyncio
async def test_required():
    """Test case for required, slugify and directory name."""
    print_func_commentary()
    with_avatar_data = {
        "name": "Image with avatar",
        "image": "https://picsum.photos/500",
        "avatar": "https://picsum.photos/100"
    }
    without_image_data = {"name": "Bad data"}
    print("✓ Testing creation without image (should fail)...")
    with pytest.raises(IntegrityError, match="NOT NULL constraint failed: itemmodel.image"):
        client.post("/create/", json=without_image_data)
    print("✓ Expected IntegrityError raised successfully")

    print("✓ Testing creation with image and avatar...")
    response = client.post("/create/", json=with_avatar_data)
    assert response.status_code == 200, "✗ Failed to create item with image and avatar"
    print("✓ ItemModel with image and avatar created successfully")

    data = response.json()
    assert data.get("image_url") is not None, "✗ Image URL is missing"
    print(f"✓ Image URL found: {data.get('image_url')}")
    check_image_url(client, data.get("image_url"), "Image", (200, 200))

    assert data.get("avatar_url") is not None, "✗ Avatar URL is missing"
    print(f"✓ Avatar URL found: {data.get('avatar_url')}")
    check_image_url(client, data.get("avatar_url"), "Avatar", (50, 50))

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

import os
from io import BytesIO
import inspect

from PIL import Image


def check_image_url(client, url, name, size=(100, 100), code=200):
    cache_response = client.get(url)
    assert cache_response.status_code == code
    img = Image.open(BytesIO(cache_response.content))
    assert img.size == size
    print(f"✓ {name} url is OK!")


def check_file(file_path, name, exist=True):
    assert os.path.exists(file_path) is exist, f"✗ {name} - File exists check is error"
    print(f"✓ {name} - File {'' if exist else 'not'} exists at {file_path}")


def print_func_commentary(length: int = 150):
    frame = inspect.currentframe().f_back
    func = frame.f_globals.get(frame.f_code.co_name)

    if func and callable(func):
        docstring = inspect.getdoc(func) or "No documentation available"
    else:
        docstring = "No documentation available (function not found)"
    padding = (length - len(docstring) - 2) // 2
    formatted_text = f"{'=' * padding} {docstring} {'=' * padding}"
    if len(formatted_text) < length:
        formatted_text += "="
    print("")
    print("=" * length)
    print(f"{formatted_text}")
    print("=" * length)
    print("")


def path_join(*args):
    base_path = os.getcwd()
    if "tests" not in base_path:
        base_path = os.path.join(base_path, "tests")
    return os.path.join(base_path, *args)

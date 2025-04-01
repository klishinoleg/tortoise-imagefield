from setuptools import setup, find_packages

setup(
    name="tortoise-imagefield",
    version="0.1.3",
    author="Klishin Oleg",
    author_email="klishinoleg@gmail.com",
    description="Asynchronous Tortoise ORM field for handling image uploads with cropping, caching, and support for AWS S3 or local storage.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/tortoise-imagefield",
    packages=find_packages(),
    install_requires=[
        "tortoise-orm",
        "boto3",
        "pillow",
        "starlette",
        "asgiref",
        "python-slugify",
        "aiohttp",
        "aiofiles",
        "aioboto3"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)

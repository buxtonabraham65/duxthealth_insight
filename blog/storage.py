
import os
import uuid

import cloudinary
import cloudinary.uploader

from django.core.files.storage import Storage
from django.core.files.base import ContentFile


class CloudinaryMediaStorage(Storage):
    """
    Store Django uploaded media files in Cloudinary.
    """

    def __init__(self):
        cloudinary.config(
            cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
            api_key=os.environ.get("CLOUDINARY_API_KEY"),
            api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
            secure=True,
        )

    def _save(self, name, content):
        folder = os.path.dirname(name).replace("\\", "/")
        filename = os.path.basename(name)

        name_without_extension, extension = os.path.splitext(filename)

        public_id = f"{name_without_extension}_{uuid.uuid4().hex[:12]}"

        content.seek(0)

        result = cloudinary.uploader.upload(
            content,
            folder=f"duxthealth_insight/{folder}".strip("/"),
            public_id=public_id,
            resource_type="image",
        )

        return result["public_id"]

    def _open(self, name, mode="rb"):
        raise NotImplementedError(
            "Cloudinary files are accessed through their URLs."
        )

    def exists(self, name):
        return False

    def url(self, name):
        return cloudinary.CloudinaryImage(name).build_url(secure=True)

    def delete(self, name):
        if name:
            cloudinary.uploader.destroy(
                name,
                resource_type="image",
            )

    def get_available_name(self, name, max_length=None):
        return name

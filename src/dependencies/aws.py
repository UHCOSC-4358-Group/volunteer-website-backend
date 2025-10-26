import boto3
from fastapi import HTTPException, Request, UploadFile
import logging
import os
from uuid import uuid4
from mypy_boto3_s3 import S3Client
from mypy_boto3_s3.service_resource import Bucket


def create_bucket():

    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
    AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
    AWS_BUCKET_REGION = os.getenv("AWS_BUCKET_REGION")

    if (
        AWS_ACCESS_KEY is None
        or AWS_SECRET_KEY is None
        or AWS_BUCKET_NAME is None
        or AWS_BUCKET_REGION is None
    ):
        raise HTTPException(500, "Environment variables not loaded!")

    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=AWS_BUCKET_REGION,
    )

    s3_client: S3Client = session.client("s3")

    return s3_client


def get_s3(request: Request):
    s3 = getattr(request.app.state, "s3", None)
    if s3 is None:
        raise HTTPException(status_code=500, detail="S3 not initialized on app.state")
    yield s3


def upload_image(s3: S3Client, image: UploadFile):
    AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
    AWS_BUCKET_REGION = os.getenv("AWS_BUCKET_REGION")
    if AWS_BUCKET_NAME is None:
        raise HTTPException(500, "AWS S3 Bucket name not loaded!")
    if AWS_BUCKET_REGION is None:
        raise HTTPException(500, "AWS S3 Region name not loaded!")

    file_name = image.filename

    if file_name is None:
        raise HTTPException(422, "File sent is not correct!")

    file_extension = file_name.split(".")[-1]

    extensions = ["jpg", "jpeg", "jpe", "bmp", "gif", "png"]
    if file_extension not in extensions:
        raise HTTPException(422, "File sent is not correct image format!")

    file_name = f"{str(uuid4())}.{file_extension}"

    content_type = image.content_type

    if content_type is None:
        raise HTTPException(422, "File sent has invalid content type!")

    s3.upload_fileobj(
        image.file,
        AWS_BUCKET_NAME,
        file_name,
        ExtraArgs={"ContentType": content_type, "ACL": "public-read"},
    )

    object_url = (
        f"https://{AWS_BUCKET_NAME}.s3.{AWS_BUCKET_REGION}.amazonaws.com/{file_name}"
    )

    return object_url


# def load_file():

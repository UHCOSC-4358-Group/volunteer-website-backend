import boto3
from botocore import exceptions
from fastapi import Request, UploadFile
import os
from uuid import uuid4
from mypy_boto3_s3 import S3Client
from ..util import error


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
        raise error.ExternalServiceError(
            "AWS_S3", "Required AWS credentials not configured"
        )

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
        raise error.ExternalServiceError("AWS_S3", "S3 is not initialized on app.state")
    yield s3


def upload_image(s3: S3Client, image: UploadFile):
    AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
    AWS_BUCKET_REGION = os.getenv("AWS_BUCKET_REGION")
    if AWS_BUCKET_NAME is None or AWS_BUCKET_REGION is None:
        raise error.ExternalServiceError(
            "AWS_S3", "Required AWS credentials not configured"
        )

    file_name = image.filename

    if file_name is None:
        raise error.ValidationError(
            "Invalid file format", {"file": "Filename is required"}
        )

    file_extension = file_name.split(".")[-1]

    extensions = ["jpg", "jpeg", "jpe", "bmp", "gif", "png"]
    if file_extension not in extensions:
        raise error.ValidationError(
            "Invalid file format",
            {"file": f"Format .{file_extension} is not supported"},
        )

    file_name = f"{str(uuid4())}.{file_extension}"

    content_type = image.content_type

    if content_type is None:
        raise error.ValidationError(
            "Invalid file format", {"file": f"Content type of file was not found"}
        )
    try:
        s3.upload_fileobj(
            image.file,
            AWS_BUCKET_NAME,
            file_name,
            ExtraArgs={"ContentType": content_type, "ACL": "public-read"},
        )
    except exceptions.ClientError as e:
        raise error.ExternalServiceError("AWS_S3", f"AWS API error: {e.response}")
    except exceptions.BotoCoreError as e:
        raise error.ExternalServiceError("AWS_S3", f"Connection error: {str(e)}")
    except Exception as e:
        raise error.ExternalServiceError("AWS_S3", f"Unexpected error: {str(e)}")

    object_url = (
        f"https://{AWS_BUCKET_NAME}.s3.{AWS_BUCKET_REGION}.amazonaws.com/{file_name}"
    )

    return object_url


# def load_file():

#!/usr/bin/env python3
"""
修改 handler.py 以支持:
1. OSS 上传替代 S3/rp_upload (使用 alibabacloud_oss_v2)
2. 图片通过 URL 上传
3. 视频通过 URL 或 base64 上传
4. 输出文件上传到 OSS
"""

import re
import subprocess
import sys

# ============================================================================
# 0. 安装依赖
# ============================================================================
print("Installing alibabacloud-oss-v2...")
subprocess.check_call([sys.executable, "-m", "uv", "pip", "install", "alibabacloud-oss-v2"])
print("Dependencies installed successfully!")

# 读取原始 handler.py
with open('/handler.py', 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================================================
# 1. 添加 OSS 相关的导入和配置
# ============================================================================
oss_imports = '''
# OSS Configuration (alibabacloud_oss_v2)
import alibabacloud_oss_v2 as oss
from datetime import datetime

# OSS Environment Variables
# 需要设置以下环境变量:
# - OSS_ACCESS_KEY_ID (或 ALIBABA_CLOUD_ACCESS_KEY_ID)
# - OSS_ACCESS_KEY_SECRET (或 ALIBABA_CLOUD_ACCESS_KEY_SECRET)
# - OSS_BUCKET_NAME
# - OSS_REGION (例如: cn-shanghai)
# - OSS_ENDPOINT (可选, 例如: https://oss-cn-shanghai.aliyuncs.com)
# - OSS_PREFIX (可选, 默认: comfyui-outputs)

OSS_BUCKET_NAME = os.environ.get("OSS_BUCKET_NAME", "")
OSS_REGION = os.environ.get("OSS_REGION", "cn-shanghai")
OSS_ENDPOINT = os.environ.get("OSS_ENDPOINT", "")
OSS_PREFIX = os.environ.get("OSS_PREFIX", "comfyui-outputs")

# 用于缓存 OSS client 实例
_oss_client = None


def get_oss_client():
    """
    Get OSS client instance for file uploads.
    Uses alibabacloud_oss_v2 SDK with V4 signature.

    Returns:
        oss.Client: The OSS client instance, or None if not configured.
    """
    global _oss_client

    if _oss_client is not None:
        return _oss_client

    if not OSS_BUCKET_NAME:
        print("worker-comfyui - OSS not configured, missing OSS_BUCKET_NAME")
        return None

    if not OSS_REGION:
        print("worker-comfyui - OSS not configured, missing OSS_REGION")
        return None

    try:
        # 从环境变量中加载凭证信息 (支持 ALIBABA_CLOUD_ACCESS_KEY_ID/SECRET 或 OSS_ACCESS_KEY_ID/SECRET)
        # 先检查是否设置了 OSS_ 前缀的环境变量，如果有则设置为 ALIBABA_CLOUD_ 前缀
        oss_key_id = os.environ.get("OSS_ACCESS_KEY_ID", "")
        oss_key_secret = os.environ.get("OSS_ACCESS_KEY_SECRET", "")
        if oss_key_id and oss_key_secret:
            os.environ["ALIBABA_CLOUD_ACCESS_KEY_ID"] = oss_key_id
            os.environ["ALIBABA_CLOUD_ACCESS_KEY_SECRET"] = oss_key_secret

        credentials_provider = oss.credentials.EnvironmentVariableCredentialsProvider()

        # 加载 SDK 默认配置
        cfg = oss.config.load_default()
        cfg.credentials_provider = credentials_provider
        cfg.region = OSS_REGION

        # 如果指定了 Endpoint 则使用
        if OSS_ENDPOINT:
            cfg.endpoint = OSS_ENDPOINT

        # 创建 OSS 客户端
        _oss_client = oss.Client(cfg)
        print(f"worker-comfyui - OSS client initialized for region: {OSS_REGION}, bucket: {OSS_BUCKET_NAME}")
        return _oss_client
    except Exception as e:
        print(f"worker-comfyui - Error creating OSS client: {e}")
        return None


def upload_to_oss(file_bytes, filename, job_id, content_type=None):
    """
    Upload file bytes to OSS.

    Args:
        file_bytes (bytes): The file content to upload.
        filename (str): The original filename.
        job_id (str): The job ID for organizing uploads.
        content_type (str, optional): The content type of the file.

    Returns:
        str: The OSS URL of the uploaded file, or None if upload failed.
    """
    client = get_oss_client()
    if not client:
        return None

    try:
        # Generate unique path: prefix/job_id/timestamp_filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        oss_key = f"{OSS_PREFIX}/{job_id}/{timestamp}_{filename}"

        # 构建上传请求
        request = oss.PutObjectRequest(
            bucket=OSS_BUCKET_NAME,
            key=oss_key,
            body=file_bytes,
        )

        # 如果有 content_type 则设置
        if content_type:
            request.content_type = content_type

        # 执行上传
        result = client.put_object(request)

        if result.status_code == 200:
            # 构造访问 URL
            # 格式: https://{bucket}.{region}.aliyuncs.com/{key}
            if OSS_ENDPOINT:
                endpoint_host = OSS_ENDPOINT.replace("https://", "").replace("http://", "")
                oss_url = f"https://{OSS_BUCKET_NAME}.{endpoint_host}/{oss_key}"
            else:
                oss_url = f"https://{OSS_BUCKET_NAME}.oss-{OSS_REGION}.aliyuncs.com/{oss_key}"

            print(f"worker-comfyui - Successfully uploaded to OSS: {oss_url}")
            return oss_url
        else:
            print(f"worker-comfyui - OSS upload failed with status: {result.status_code}")
            return None
    except Exception as e:
        print(f"worker-comfyui - Error uploading to OSS: {e}")
        import traceback
        traceback.print_exc()
        return None


def download_from_url(url, timeout=120):
    """
    Download file from URL.

    Args:
        url (str): The URL to download from.
        timeout (int): Request timeout in seconds.

    Returns:
        tuple: (bytes, content_type) or (None, None) if download failed.
    """
    try:
        print(f"worker-comfyui - Downloading from URL: {url}")
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()
        content_type = response.headers.get('content-type', 'application/octet-stream')
        return response.content, content_type
    except requests.Timeout:
        print(f"worker-comfyui - Timeout downloading from URL: {url}")
        return None, None
    except requests.RequestException as e:
        print(f"worker-comfyui - Error downloading from URL {url}: {e}")
        return None, None
    except Exception as e:
        print(f"worker-comfyui - Unexpected error downloading from URL {url}: {e}")
        return None, None

'''

# 在 COMFY_HOST 定义之后插入 OSS 配置
pattern = r'(COMFY_HOST = "[^"]*")'
match = re.search(pattern, content)
if match:
    insert_pos = match.end()
    content = content[:insert_pos] + oss_imports + content[insert_pos:]
else:
    # 如果找不到 COMFY_HOST，就在 import 之后添加
    content = content.replace('import traceback', 'import traceback' + oss_imports)

# ============================================================================
# 2. 重写 upload_images 函数以支持 URL
# ============================================================================
new_upload_images = '''def upload_images(images):
    """
    Upload a list of images (base64 encoded or URL) to the ComfyUI server using the /upload/image endpoint.

    Args:
        images (list): A list of dictionaries, each containing:
                      - 'name': the filename for the image
                      - 'image': a base64 encoded string (optional if 'url' provided)
                      - 'url': a URL to download the image from (optional if 'image' provided)

    Returns:
        dict: A dictionary indicating success or error.
    """
    if not images:
        return {"status": "success", "message": "No images to upload", "details": []}

    responses = []
    upload_errors = []

    print(f"worker-comfyui - Uploading {len(images)} image(s)...")

    for image in images:
        try:
            name = image["name"]
            blob = None
            content_type = "image/png"

            # Check if image is provided as URL
            if "url" in image and image["url"]:
                print(f"worker-comfyui - Downloading image from URL: {image['url']}")
                blob, content_type = download_from_url(image["url"], timeout=60)
                if blob is None:
                    raise ValueError(f"Failed to download image from URL: {image['url']}")
                # Determine content type from URL or response
                if not content_type or content_type == 'application/octet-stream':
                    ext = os.path.splitext(name)[1].lower()
                    content_type_map = {
                        '.png': 'image/png',
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.gif': 'image/gif',
                        '.webp': 'image/webp',
                        '.bmp': 'image/bmp',
                    }
                    content_type = content_type_map.get(ext, 'image/png')

            elif "image" in image and image["image"]:
                # Handle base64 encoded image
                image_data_uri = image["image"]

                # Strip Data URI prefix if present
                if "," in image_data_uri:
                    # Extract content type from data URI if present
                    prefix = image_data_uri.split(",", 1)[0]
                    if ":" in prefix and ";" in prefix:
                        content_type = prefix.split(":")[1].split(";")[0]
                    base64_data = image_data_uri.split(",", 1)[1]
                else:
                    base64_data = image_data_uri

                blob = base64.b64decode(base64_data)
            else:
                raise ValueError(f"Image {name} must have either 'url' or 'image' field")

            # Prepare the form data
            files = {
                "image": (name, BytesIO(blob), content_type),
                "overwrite": (None, "true"),
            }

            # POST request to upload the image
            response = requests.post(
                f"http://{COMFY_HOST}/upload/image", files=files, timeout=30
            )
            response.raise_for_status()

            responses.append(f"Successfully uploaded {name}")
            print(f"worker-comfyui - Successfully uploaded {name}")

        except base64.binascii.Error as e:
            error_msg = f"Error decoding base64 for {image.get('name', 'unknown')}: {e}"
            print(f"worker-comfyui - {error_msg}")
            upload_errors.append(error_msg)
        except requests.Timeout:
            error_msg = f"Timeout uploading {image.get('name', 'unknown')}"
            print(f"worker-comfyui - {error_msg}")
            upload_errors.append(error_msg)
        except requests.RequestException as e:
            error_msg = f"Error uploading {image.get('name', 'unknown')}: {e}"
            print(f"worker-comfyui - {error_msg}")
            upload_errors.append(error_msg)
        except Exception as e:
            error_msg = (
                f"Unexpected error uploading {image.get('name', 'unknown')}: {e}"
            )
            print(f"worker-comfyui - {error_msg}")
            upload_errors.append(error_msg)

    if upload_errors:
        print(f"worker-comfyui - image(s) upload finished with errors")
        return {
            "status": "error",
            "message": "Some images failed to upload",
            "details": upload_errors,
        }

    print(f"worker-comfyui - image(s) upload complete")
    return {
        "status": "success",
        "message": "All images uploaded successfully",
        "details": responses,
    }

'''

# 替换原有的 upload_images 函数
pattern = r'def upload_images\(images\):.*?return \{\s*"status": "success",\s*"message": "All images uploaded successfully",\s*"details": responses,\s*\}'
content = re.sub(pattern, new_upload_images.strip(), content, flags=re.DOTALL)

# ============================================================================
# 3. 添加 upload_videos 函数
# ============================================================================
upload_videos_func = '''

def upload_videos(videos):
    """
    Upload a list of videos (base64 encoded or URL) to the ComfyUI server using the /upload/image endpoint.
    Note: ComfyUI uses the same endpoint for videos as it does for images.

    Args:
        videos (list): A list of dictionaries, each containing:
                      - 'name': the filename for the video
                      - 'video': a base64 encoded string (optional if 'url' provided)
                      - 'url': a URL to download the video from (optional if 'video' provided)

    Returns:
        dict: A dictionary indicating success or error.
    """
    if not videos:
        return {"status": "success", "message": "No videos to upload", "details": []}

    responses = []
    upload_errors = []

    print(f"worker-comfyui - Uploading {len(videos)} video(s)...")

    for video in videos:
        try:
            name = video["name"]
            blob = None
            content_type = "video/mp4"

            # Check if video is provided as URL
            if "url" in video and video["url"]:
                print(f"worker-comfyui - Downloading video from URL: {video['url']}")
                blob, content_type = download_from_url(video["url"], timeout=300)
                if blob is None:
                    raise ValueError(f"Failed to download video from URL: {video['url']}")
                # Determine content type from filename if not properly detected
                if not content_type or content_type == 'application/octet-stream':
                    ext = os.path.splitext(name)[1].lower()
                    content_type_map = {
                        '.mp4': 'video/mp4',
                        '.webm': 'video/webm',
                        '.mov': 'video/quicktime',
                        '.avi': 'video/x-msvideo',
                        '.mkv': 'video/x-matroska',
                        '.gif': 'image/gif',
                    }
                    content_type = content_type_map.get(ext, 'video/mp4')

            elif "video" in video and video["video"]:
                # Handle base64 encoded video
                video_data_uri = video["video"]

                # Strip Data URI prefix if present
                if "," in video_data_uri:
                    prefix = video_data_uri.split(",", 1)[0]
                    if ":" in prefix and ";" in prefix:
                        content_type = prefix.split(":")[1].split(";")[0]
                    base64_data = video_data_uri.split(",", 1)[1]
                else:
                    base64_data = video_data_uri

                blob = base64.b64decode(base64_data)
            else:
                raise ValueError(f"Video {name} must have either 'url' or 'video' field")

            # Prepare the form data (ComfyUI uses /upload/image for videos too)
            files = {
                "image": (name, BytesIO(blob), content_type),
                "overwrite": (None, "true"),
            }

            # POST request to upload the video
            response = requests.post(
                f"http://{COMFY_HOST}/upload/image", files=files, timeout=120
            )
            response.raise_for_status()

            responses.append(f"Successfully uploaded {name}")
            print(f"worker-comfyui - Successfully uploaded video {name}")

        except base64.binascii.Error as e:
            error_msg = f"Error decoding base64 for {video.get('name', 'unknown')}: {e}"
            print(f"worker-comfyui - {error_msg}")
            upload_errors.append(error_msg)
        except requests.Timeout:
            error_msg = f"Timeout uploading {video.get('name', 'unknown')}"
            print(f"worker-comfyui - {error_msg}")
            upload_errors.append(error_msg)
        except requests.RequestException as e:
            error_msg = f"Error uploading {video.get('name', 'unknown')}: {e}"
            print(f"worker-comfyui - {error_msg}")
            upload_errors.append(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error uploading {video.get('name', 'unknown')}: {e}"
            print(f"worker-comfyui - {error_msg}")
            upload_errors.append(error_msg)

    if upload_errors:
        print(f"worker-comfyui - video(s) upload finished with errors")
        return {
            "status": "error",
            "message": "Some videos failed to upload",
            "details": upload_errors,
        }

    print(f"worker-comfyui - video(s) upload complete")
    return {
        "status": "success",
        "message": "All videos uploaded successfully",
        "details": responses,
    }

'''

# 在 upload_images 函数之后添加 upload_videos 函数
# 找到 upload_images 函数结束后的下一个函数
pattern = r'(print\(f"worker-comfyui - image\(s\) upload complete"\)\s*\n\s*return \{\s*"status": "success",\s*"message": "All images uploaded successfully",\s*"details": responses,\s*\})'
match = re.search(pattern, content)
if match:
    insert_pos = match.end()
    content = content[:insert_pos] + upload_videos_func + content[insert_pos:]

# ============================================================================
# 4. 修改 validate_input 函数
# ============================================================================
new_validate_input = '''def validate_input(job_input):
    """
    Validates the input for the handler function.

    Args:
        job_input (dict): The input data to validate.

    Returns:
        tuple: A tuple containing the validated data and an error message, if any.
               The structure is (validated_data, error_message).
    """
    # Validate if job_input is provided
    if job_input is None:
        return None, "Please provide input"

    # Check if input is a string and try to parse it as JSON
    if isinstance(job_input, str):
        try:
            job_input = json.loads(job_input)
        except json.JSONDecodeError:
            return None, "Invalid JSON format in input"

    # Validate 'workflow' in input
    workflow = job_input.get("workflow")
    if workflow is None:
        return None, "Missing 'workflow' parameter"

    # Validate 'images' in input, if provided
    # Now supports both 'image' (base64) and 'url' fields
    images = job_input.get("images")
    if images is not None:
        if not isinstance(images, list):
            return None, "'images' must be a list"
        for img in images:
            if not isinstance(img, dict):
                return None, "Each image must be an object"
            if "name" not in img:
                return None, "Each image must have a 'name' field"
            if "image" not in img and "url" not in img:
                return None, "Each image must have either 'image' (base64) or 'url' field"

    # Validate 'videos' in input, if provided
    # Supports both 'video' (base64) and 'url' fields
    videos = job_input.get("videos")
    if videos is not None:
        if not isinstance(videos, list):
            return None, "'videos' must be a list"
        for vid in videos:
            if not isinstance(vid, dict):
                return None, "Each video must be an object"
            if "name" not in vid:
                return None, "Each video must have a 'name' field"
            if "video" not in vid and "url" not in vid:
                return None, "Each video must have either 'video' (base64) or 'url' field"

    # Optional: API key for Comfy.org API Nodes, passed per-request
    comfy_org_api_key = job_input.get("comfy_org_api_key")

    # Return validated data and no error
    return {
        "workflow": workflow,
        "images": images,
        "videos": videos,
        "comfy_org_api_key": comfy_org_api_key,
    }, None

'''

# 替换原有的 validate_input 函数
pattern = r'def validate_input\(job_input\):.*?return \{\s*"workflow": workflow,\s*"images": images,\s*"comfy_org_api_key": comfy_org_api_key,\s*\}, None'
content = re.sub(pattern, new_validate_input.strip(), content, flags=re.DOTALL)

# ============================================================================
# 5. 修改 handler 函数以支持 videos 和 OSS 上传
# ============================================================================

# 5.1 在图片上传之后添加视频上传逻辑
old_upload_pattern = r'''(# Upload input images if they exist
    if input_images:
        upload_result = upload_images\(input_images\)
        if upload_result\["status"\] == "error":
            # Return upload errors
            return \{
                "error": "Failed to upload one or more input images",
                "details": upload_result\["details"\],
            \})'''

new_upload_code = '''# Upload input images if they exist
    if input_images:
        upload_result = upload_images(input_images)
        if upload_result["status"] == "error":
            # Return upload errors
            return {
                "error": "Failed to upload one or more input images",
                "details": upload_result["details"],
            }

    # Upload input videos if they exist
    input_videos = validated_data.get("videos")
    if input_videos:
        upload_result = upload_videos(input_videos)
        if upload_result["status"] == "error":
            # Return upload errors
            return {
                "error": "Failed to upload one or more input videos",
                "details": upload_result["details"],
            }'''

content = re.sub(old_upload_pattern, new_upload_code, content)

# 5.2 修改输出处理部分以使用 OSS
# 找到输出处理部分并替换为 OSS 上传逻辑
old_output_pattern = r'''if os\.environ\.get\("BUCKET_ENDPOINT_URL"\):
                            try:
                                with tempfile\.NamedTemporaryFile\(
                                    suffix=file_extension, delete=False
                                \) as temp_file:
                                    temp_file\.write\(image_bytes\)
                                    temp_file_path = temp_file\.name
                                print\(
                                    f"worker-comfyui - Wrote image bytes to temporary file: \{temp_file_path\}"
                                \)

                                print\(f"worker-comfyui - Uploading \{filename\} to S3\.\.\."\)
                                s3_url = rp_upload\.upload_image\(job_id, temp_file_path\)
                                os\.remove\(temp_file_path\)  # Clean up temp file
                                print\(
                                    f"worker-comfyui - Uploaded \{filename\} to S3: \{s3_url\}"
                                \)
                                # Append dictionary with filename and URL
                                output_data\.append\(
                                    \{
                                        "filename": filename,
                                        "type": "s3_url",
                                        "data": s3_url,
                                    \}
                                \)
                            except Exception as e:
                                error_msg = f"Error uploading \{filename\} to S3: \{e\}"
                                print\(f"worker-comfyui - \{error_msg\}"\)
                                errors\.append\(error_msg\)
                                if "temp_file_path" in locals\(\) and os\.path\.exists\(
                                    temp_file_path
                                \):
                                    try:
                                        os\.remove\(temp_file_path\)
                                    except OSError as rm_err:
                                        print\(
                                            f"worker-comfyui - Error removing temp file \{temp_file_path\}: \{rm_err\}"
                                        \)'''

new_output_code = '''# Try OSS upload first, then fall back to S3, then base64
                        oss_client = get_oss_client()
                        if oss_client:
                            try:
                                # Determine content type
                                ext = os.path.splitext(filename)[1].lower()
                                content_type_map = {
                                    '.png': 'image/png',
                                    '.jpg': 'image/jpeg',
                                    '.jpeg': 'image/jpeg',
                                    '.gif': 'image/gif',
                                    '.webp': 'image/webp',
                                    '.mp4': 'video/mp4',
                                    '.webm': 'video/webm',
                                    '.mov': 'video/quicktime',
                                }
                                content_type = content_type_map.get(ext, 'application/octet-stream')

                                print(f"worker-comfyui - Uploading {filename} to OSS...")
                                oss_url = upload_to_oss(image_bytes, filename, job_id, content_type)
                                if oss_url:
                                    print(f"worker-comfyui - Uploaded {filename} to OSS: {oss_url}")
                                    output_data.append({
                                        "filename": filename,
                                        "type": "oss_url",
                                        "data": oss_url,
                                    })
                                else:
                                    raise Exception("OSS upload returned None")
                            except Exception as e:
                                error_msg = f"Error uploading {filename} to OSS: {e}"
                                print(f"worker-comfyui - {error_msg}")
                                errors.append(error_msg)
                        elif os.environ.get("BUCKET_ENDPOINT_URL"):
                            try:
                                with tempfile.NamedTemporaryFile(
                                    suffix=file_extension, delete=False
                                ) as temp_file:
                                    temp_file.write(image_bytes)
                                    temp_file_path = temp_file.name
                                print(
                                    f"worker-comfyui - Wrote image bytes to temporary file: {temp_file_path}"
                                )

                                print(f"worker-comfyui - Uploading {filename} to S3...")
                                s3_url = rp_upload.upload_image(job_id, temp_file_path)
                                os.remove(temp_file_path)  # Clean up temp file
                                print(
                                    f"worker-comfyui - Uploaded {filename} to S3: {s3_url}"
                                )
                                # Append dictionary with filename and URL
                                output_data.append(
                                    {
                                        "filename": filename,
                                        "type": "s3_url",
                                        "data": s3_url,
                                    }
                                )
                            except Exception as e:
                                error_msg = f"Error uploading {filename} to S3: {e}"
                                print(f"worker-comfyui - {error_msg}")
                                errors.append(error_msg)
                                if "temp_file_path" in locals() and os.path.exists(
                                    temp_file_path
                                ):
                                    try:
                                        os.remove(temp_file_path)
                                    except OSError as rm_err:
                                        print(
                                            f"worker-comfyui - Error removing temp file {temp_file_path}: {rm_err}"
                                        )'''

content = re.sub(old_output_pattern, new_output_code, content, flags=re.DOTALL)

# ============================================================================
# 6. 添加 alibabacloud_oss_v2 到导入 (在文件头部)
# ============================================================================
# 在 import 部分添加
if 'import alibabacloud_oss_v2' not in content:
    content = content.replace('import traceback', 'import traceback\nimport alibabacloud_oss_v2 as oss\nfrom datetime import datetime')

# 写回文件
with open('/handler.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("=" * 60)
print("handler.py has been successfully modified!")
print("=" * 60)
print("Changes made:")
print("1. Added OSS upload functionality using alibabacloud_oss_v2 SDK")
print("   - get_oss_client(): Creates OSS client with V4 signature")
print("   - upload_to_oss(): Uploads file bytes to OSS")
print("2. Added download_from_url helper function")
print("3. Updated upload_images to support URL downloads")
print("4. Added upload_videos function for video uploads")
print("5. Updated validate_input to support images URL and videos")
print("6. Updated handler to use OSS for output uploads (with S3 fallback)")
print("")
print("Required environment variables for OSS:")
print("  - OSS_ACCESS_KEY_ID (or ALIBABA_CLOUD_ACCESS_KEY_ID)")
print("  - OSS_ACCESS_KEY_SECRET (or ALIBABA_CLOUD_ACCESS_KEY_SECRET)")
print("  - OSS_BUCKET_NAME")
print("  - OSS_REGION (e.g., cn-shanghai)")
print("  - OSS_ENDPOINT (optional, e.g., https://oss-cn-shanghai.aliyuncs.com)")
print("  - OSS_PREFIX (optional, default: comfyui-outputs)")

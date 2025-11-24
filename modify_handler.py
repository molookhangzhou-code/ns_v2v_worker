#!/usr/bin/env python3
"""
修改 handler.py 以支持 video 通过 URL 上传
"""

import re

# 读取原始 handler.py
with open('/handler.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 在 upload_images 函数之后添加 upload_videos 函数
upload_videos_func = '''

def upload_videos(videos):
    """
    Upload a list of videos (base64 encoded or URL) to the ComfyUI server using the /upload/image endpoint.
    Note: ComfyUI uses the same endpoint for videos as it does for images.

    Args:
        videos (list): A list of dictionaries, each containing the 'name' of the video and either:
                      - 'video': a base64 encoded string
                      - 'url': a URL to download the video from

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

            # Check if video is provided as URL or base64
            if "url" in video and video["url"]:
                # Download video from URL
                print(f"worker-comfyui - Downloading video from URL: {video['url']}")
                video_response = requests.get(video["url"], timeout=120, stream=True)
                video_response.raise_for_status()

                # Get content type to determine video format
                content_type = video_response.headers.get('content-type', 'video/mp4')
                blob = video_response.content

            elif "video" in video and video["video"]:
                # Handle base64 encoded video
                video_data_uri = video["video"]

                # Strip Data URI prefix if present
                if "," in video_data_uri:
                    base64_data = video_data_uri.split(",", 1)[1]
                else:
                    base64_data = video_data_uri

                blob = base64.b64decode(base64_data)
                content_type = "video/mp4"  # Default to mp4
            else:
                raise ValueError(f"Video {name} must have either 'url' or 'video' field")

            # Prepare the form data (ComfyUI uses /upload/image for videos too)
            files = {
                "image": (name, BytesIO(blob), content_type),
                "overwrite": (None, "true"),
            }

            # POST request to upload the video
            response = requests.post(
                f"http://{COMFY_HOST}/upload/image", files=files, timeout=60
            )
            response.raise_for_status()

            responses.append(f"Successfully uploaded {name}")
            print(f"worker-comfyui - Successfully uploaded video {name}")

        except requests.exceptions.RequestException as e:
            error_msg = f"Error downloading video from URL for {video.get('name', 'unknown')}: {e}"
            upload_errors.append(error_msg)
            print(f"worker-comfyui - {error_msg}")
        except base64.binascii.Error as e:
            error_msg = f"Error decoding base64 for {video.get('name', 'unknown')}: {e}"
            upload_errors.append(error_msg)
            print(f"worker-comfyui - {error_msg}")
        except Exception as e:
            error_msg = f"Unexpected error uploading {video.get('name', 'unknown')}: {e}"
            upload_errors.append(error_msg)
            print(f"worker-comfyui - {error_msg}")

    if upload_errors:
        return {
            "status": "error",
            "message": "Some videos failed to upload",
            "details": responses + upload_errors,
        }

    return {"status": "success", "message": "All videos uploaded successfully", "details": responses}
'''

# 找到 upload_images 函数的结束位置并插入 upload_videos
# 查找 upload_images 函数后的下一个函数定义
match = re.search(r'(def upload_images.*?)\n(def \w+)', content, re.DOTALL)
if match:
    content = content[:match.end(1)] + upload_videos_func + '\n' + content[match.end(1):]
else:
    # 如果找不到下一个函数，就添加到文件末尾
    content += upload_videos_func

# 2. 修改 validate_input 函数以支持 videos 参数
# 在 images 验证之后添加 videos 验证
videos_validation = '''
    # Validate 'videos' in input, if provided
    videos = job_input.get("videos")
    if videos is not None:
        if not isinstance(videos, list) or not all(
            "name" in video and ("video" in video or "url" in video) for video in videos
        ):
            return None, "Invalid 'videos' format, must be a list of objects with 'name' and either 'video' (base64) or 'url'"
'''

# 在 images 验证代码块之后插入
pattern = r'(# Validate \'images\' in input.*?return None, "Invalid \'images\' format[^"]*")\s*\n'
match = re.search(pattern, content, re.DOTALL)
if match:
    content = content[:match.end()] + '\n' + videos_validation + content[match.end():]

# 3. 在 handler 函数中添加对 videos 的处理
# 查找 upload_images 调用的位置
pattern = r'(upload_result = upload_images\(validated_input\.get\("images"\)\))'
replacement = r'''\1

    # Handle video uploads if provided
    if "videos" in validated_input:
        upload_videos_result = upload_videos(validated_input.get("videos"))
        if upload_videos_result["status"] == "error":
            return {"error": upload_videos_result["message"], "details": upload_videos_result["details"]}'''

content = re.sub(pattern, replacement, content)

# 写回文件
with open('/handler.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("handler.py has been successfully modified to support video uploads via URL")

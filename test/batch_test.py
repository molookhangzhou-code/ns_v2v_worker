#!/usr/bin/env python3
"""
批量测试 V2V RunPod Endpoint
使用固定参考图像对所有视频进行生成
"""

import json
import os
import requests
import time
import base64
import subprocess
from pathlib import Path

# RunPod 配置
RUNPOD_ENDPOINT_ID = "0dyq37pwoz6s2e"
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")

# API URLs
RUN_URL = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/run"
STATUS_URL = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/status"

# 测试目录
TEST_DIR = Path(__file__).parent

# 固定参考图像
REF_IMAGE = TEST_DIR / "ComfyUI_02793_.png"

# 所有测试视频
VIDEOS = [
    "f628e0b75a26f5fd1c27a4279de88bb5_raw.mp4",  # 675k - 最小
    "28cc6a297c6f68cdbf5b060a2a8e8e32_raw.mp4",  # 1.2M
    "d45623db44b3b7b608b69de2025e4252_raw.mp4",  # 1.2M
    "605b8464ed87d867f0573ed0998e46dc_raw.mp4",  # 1.7M
    "b2b5247f8d9ed1c2810649145a3b0dea_raw.mp4",  # 5.5M - 最大
]


def load_workflow():
    """加载 workflow 模板"""
    workflow_path = TEST_DIR.parent / "NSFW-V2V-1120 (2).json"
    with open(workflow_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def file_to_base64(file_path: Path) -> str:
    """将文件转换为 base64"""
    with open(file_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def get_video_dimensions(video_path: Path) -> tuple[int, int]:
    """使用 ffprobe 获取视频尺寸"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height',
        '-of', 'json',
        str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    stream = data['streams'][0]
    return stream['width'], stream['height']


def calculate_target_dimensions(width: int, height: int, target_short_side: int = 480) -> tuple[int, int]:
    """计算目标尺寸，保持宽高比，短边为 target_short_side，对齐到 16"""
    if width < height:
        # 宽度是短边
        new_width = (target_short_side // 16) * 16
        new_height = ((height * target_short_side // width) // 16) * 16
    else:
        # 高度是短边
        new_height = (target_short_side // 16) * 16
        new_width = ((width * target_short_side // height) // 16) * 16
    return new_width, new_height


def build_request(video_path: Path, ref_image_path: Path, prompt: str = "一个少女正在跳舞"):
    """构建请求"""
    workflow = load_workflow()

    # 修改 workflow 中的视频文件名
    workflow["175"]["inputs"]["video"] = "motion_video.mp4"
    workflow["240"]["inputs"]["video"] = "motion_video.mp4"

    # 修改参考图像文件名
    workflow["75"]["inputs"]["image"] = "ref_image.png"

    # 修改提示词
    workflow["154"]["inputs"]["text"] = prompt

    # 设置较短的最大秒数用于测试
    workflow["165"]["inputs"]["value"] = 4  # 4秒

    # 获取视频尺寸并计算目标尺寸
    target_short_side = 480
    workflow["228"]["inputs"]["value"] = target_short_side

    # 获取视频实际尺寸
    video_width, video_height = get_video_dimensions(video_path)
    target_width, target_height = calculate_target_dimensions(video_width, video_height, target_short_side)
    print(f"  视频尺寸: {video_width}x{video_height} -> 目标尺寸: {target_width}x{target_height}")

    # 将 SimpleMath+ 节点 181 和 183 替换为 easy int 节点
    # 因为服务器的 SimpleMath+ 不支持参数 c
    workflow["181"] = {
        "inputs": {"value": target_width},
        "class_type": "easy int",
        "_meta": {"title": "Target Width"}
    }
    workflow["183"] = {
        "inputs": {"value": target_height},
        "class_type": "easy int",
        "_meta": {"title": "Target Height"}
    }

    # 修复输出节点：让节点283使用生成的视频(节点31)而不是原视频(节点240)
    if "283" in workflow:
        workflow["283"]["inputs"]["images"] = ["31", 0]

    # 读取参考图像
    ref_image_base64 = file_to_base64(ref_image_path)

    # 读取视频
    video_base64 = file_to_base64(video_path)

    # 构建请求 payload
    payload = {
        "input": {
            "workflow": workflow,
            "videos": [
                {
                    "name": "motion_video.mp4",
                    "video": f"data:video/mp4;base64,{video_base64}"
                }
            ],
            "images": [
                {
                    "name": "ref_image.png",
                    "image": f"data:image/png;base64,{ref_image_base64}"
                }
            ]
        }
    }

    return payload


def submit_job(payload: dict) -> str:
    """提交任务，返回 job_id"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {RUNPOD_API_KEY}"
    }

    response = requests.post(RUN_URL, json=payload, headers=headers, timeout=300)
    response.raise_for_status()

    result = response.json()
    return result.get("id")


def check_status(job_id: str, retries: int = 3) -> dict:
    """检查任务状态"""
    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}
    url = f"{STATUS_URL}/{job_id}"

    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                raise e


def wait_for_completion(job_id: str, timeout: int = 600, interval: int = 10) -> dict:
    """等待任务完成"""
    start_time = time.time()

    while time.time() - start_time < timeout:
        result = check_status(job_id)
        status = result.get("status")

        elapsed = int(time.time() - start_time)
        print(f"  [{elapsed}s] 状态: {status}")

        if status == "COMPLETED":
            return result
        elif status == "FAILED":
            return result
        elif status in ["IN_QUEUE", "IN_PROGRESS"]:
            time.sleep(interval)
        else:
            time.sleep(interval)

    return {"status": "TIMEOUT"}


def main():
    if not RUNPOD_API_KEY:
        print("错误: 请设置 RUNPOD_API_KEY 环境变量")
        print("export RUNPOD_API_KEY=your_api_key")
        return

    if not REF_IMAGE.exists():
        print(f"错误: 参考图像不存在: {REF_IMAGE}")
        return

    print("=" * 60)
    print("批量 V2V 测试")
    print("=" * 60)
    print(f"参考图像: {REF_IMAGE.name}")
    print(f"视频数量: {len(VIDEOS)}")
    print("=" * 60)

    # 存储所有任务
    jobs = []

    # 提交所有任务
    for i, video_name in enumerate(VIDEOS, 1):
        video_path = TEST_DIR / video_name
        if not video_path.exists():
            print(f"\n[{i}/{len(VIDEOS)}] 跳过 - 文件不存在: {video_name}")
            continue

        print(f"\n[{i}/{len(VIDEOS)}] 处理: {video_name}")
        print(f"  文件大小: {video_path.stat().st_size / 1024:.1f} KB")

        # 构建请求
        print("  构建请求...")
        payload = build_request(video_path, REF_IMAGE)
        payload_size = len(json.dumps(payload)) / 1024 / 1024
        print(f"  Payload 大小: {payload_size:.2f} MB")

        # 提交任务
        print("  提交任务...")
        try:
            job_id = submit_job(payload)
            print(f"  Job ID: {job_id}")
            jobs.append({
                "video": video_name,
                "job_id": job_id,
                "status": "SUBMITTED"
            })
        except Exception as e:
            print(f"  提交失败: {e}")
            jobs.append({
                "video": video_name,
                "job_id": None,
                "status": "SUBMIT_FAILED",
                "error": str(e)
            })

    # 保存任务列表
    jobs_file = TEST_DIR / "batch_jobs.json"
    with open(jobs_file, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    print(f"\n任务列表已保存: {jobs_file}")

    # 等待所有任务完成
    print("\n" + "=" * 60)
    print("等待任务完成...")
    print("=" * 60)

    for job in jobs:
        if not job.get("job_id"):
            continue

        print(f"\n等待: {job['video']}")
        result = wait_for_completion(job["job_id"])
        job["status"] = result.get("status", "UNKNOWN")
        job["result"] = result

        if job["status"] == "COMPLETED":
            output = result.get("output", {})
            print(f"  ✅ 完成!")
            if "message" in output:
                print(f"  消息: {output['message']}")
        elif job["status"] == "FAILED":
            print(f"  ❌ 失败: {result.get('error', 'Unknown error')}")
        else:
            print(f"  ⚠️ 状态: {job['status']}")

    # 保存最终结果
    results_file = TEST_DIR / "batch_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)

    # 打印摘要
    print("\n" + "=" * 60)
    print("测试摘要")
    print("=" * 60)
    completed = sum(1 for j in jobs if j["status"] == "COMPLETED")
    failed = sum(1 for j in jobs if j["status"] in ["FAILED", "SUBMIT_FAILED"])
    print(f"完成: {completed}/{len(jobs)}")
    print(f"失败: {failed}/{len(jobs)}")
    print(f"结果已保存: {results_file}")


if __name__ == "__main__":
    main()

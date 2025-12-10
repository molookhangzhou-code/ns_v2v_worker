#!/usr/bin/env python3
"""
测试 V2V RunPod Endpoint
随机组合两个视频进行测试
"""

import json
import os
import random
import requests
import time
import base64
from pathlib import Path

# RunPod 配置
RUNPOD_ENDPOINT_ID = "0dyq37pwoz6s2e"
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")

# API URLs
RUN_URL = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/run"
STATUS_URL = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/status"

# 测试视频目录
TEST_DIR = Path(__file__).parent
VIDEOS = list(TEST_DIR.glob("*.mp4"))


def load_workflow():
    """加载 workflow 模板"""
    workflow_path = TEST_DIR.parent / "NSFW-V2V-1120 (2).json"
    with open(workflow_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def video_to_base64(video_path: Path) -> str:
    """将视频转换为 base64"""
    with open(video_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def extract_first_frame_base64(video_path: Path) -> str:
    """从视频中提取第一帧并转换为 base64 PNG"""
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # 使用 ffmpeg 提取第一帧
        cmd = [
            'ffmpeg', '-y', '-i', str(video_path),
            '-vframes', '1', '-f', 'image2', tmp_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)

        with open(tmp_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def build_request(video1: Path, video2: Path, prompt: str = "一个少女正在跳舞"):
    """
    构建请求
    video1: 动作视频（提供姿势）
    video2: 参考图像来源（取第一帧作为参考）
    """
    workflow = load_workflow()

    # 修改 workflow 中的视频文件名
    # 节点 175 和 240 加载动作视频
    workflow["175"]["inputs"]["video"] = "motion_video.mp4"
    workflow["240"]["inputs"]["video"] = "motion_video.mp4"

    # 修改节点 75 的参考图像文件名（使用简单文件名）
    workflow["75"]["inputs"]["image"] = "ref_image.png"

    # 修改提示词
    workflow["154"]["inputs"]["text"] = prompt

    # 设置较短的最大秒数用于测试
    workflow["165"]["inputs"]["value"] = 4  # 4秒

    # 修复 SimpleMath+ 节点兼容性问题
    # 服务器上的版本只支持 a, b 参数，不支持 c
    # 节点 181: (min(a,b)*c//min(a,b))//16*16 简化为 c//16*16 = 480//16*16 = 480
    # 节点 183: (max(a,b)*c//min(a,b))//16*16
    # 直接设置固定值 480（短边）和根据视频比例计算的长边
    target_size = 480
    workflow["181"]["inputs"] = {
        "value": f"{target_size}",
        "a": target_size,
        "b": target_size
    }
    workflow["183"]["inputs"] = {
        "value": f"{target_size}",
        "a": target_size,
        "b": target_size
    }
    # 节点 166 也需要修复: a*b (MaxSecond * FPS)
    workflow["166"]["inputs"] = {
        "value": "a*b",
        "a": 4,  # MaxSecond
        "b": 30  # 假设 30fps
    }

    # 从参考视频提取第一帧作为参考图像
    print("  提取参考图像...")
    ref_image_base64 = extract_first_frame_base64(video2)

    # 构建请求 payload
    payload = {
        "input": {
            "workflow": workflow,
            "videos": [
                {
                    "name": "motion_video.mp4",
                    "video": f"data:video/mp4;base64,{video_to_base64(video1)}"
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

    print(f"提交任务到: {RUN_URL}")
    response = requests.post(RUN_URL, json=payload, headers=headers, timeout=300)
    response.raise_for_status()

    result = response.json()
    job_id = result.get("id")
    print(f"任务已提交，Job ID: {job_id}")
    return job_id


def check_status(job_id: str, retries: int = 3) -> dict:
    """检查任务状态，带重试"""
    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}"
    }

    url = f"{STATUS_URL}/{job_id}"

    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
            if attempt < retries - 1:
                print(f"  连接错误，重试 {attempt + 2}/{retries}...")
                time.sleep(2)
            else:
                raise e


def wait_for_completion(job_id: str, timeout: int = 600, interval: int = 10) -> dict:
    """等待任务完成"""
    start_time = time.time()

    while time.time() - start_time < timeout:
        result = check_status(job_id)
        status = result.get("status")

        print(f"状态: {status}")

        if status == "COMPLETED":
            print("任务完成!")
            return result
        elif status == "FAILED":
            print(f"任务失败: {result.get('error')}")
            return result
        elif status in ["IN_QUEUE", "IN_PROGRESS"]:
            time.sleep(interval)
        else:
            print(f"未知状态: {status}")
            time.sleep(interval)

    print("任务超时")
    return {"status": "TIMEOUT"}


def main():
    if not RUNPOD_API_KEY:
        print("错误: 请设置 RUNPOD_API_KEY 环境变量")
        print("export RUNPOD_API_KEY=your_api_key")
        return

    if len(VIDEOS) < 2:
        print(f"错误: 需要至少2个视频文件，当前只有 {len(VIDEOS)} 个")
        return

    # 按文件大小排序，选择最小的两个视频以加快上传
    sorted_videos = sorted(VIDEOS, key=lambda x: x.stat().st_size)
    smallest_videos = sorted_videos[:3]  # 取最小的3个
    video1, video2 = random.sample(smallest_videos, 2)

    print("=" * 60)
    print("V2V RunPod 测试")
    print("=" * 60)
    print(f"动作视频: {video1.name}")
    print(f"参考视频: {video2.name}")
    print("=" * 60)

    # 构建请求
    print("\n构建请求...")
    payload = build_request(video1, video2)

    # 打印 payload 大小
    payload_size = len(json.dumps(payload)) / 1024 / 1024
    print(f"Payload 大小: {payload_size:.2f} MB")

    # 提交任务
    print("\n提交任务...")
    job_id = submit_job(payload)

    # 保存 job_id
    with open(TEST_DIR / "job_id.txt", "w") as f:
        f.write(job_id)

    # 等待完成
    print("\n等待任务完成...")
    result = wait_for_completion(job_id)

    # 保存结果
    with open(TEST_DIR / "result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到: {TEST_DIR / 'result.json'}")

    # 如果有输出，保存视频
    if result.get("status") == "COMPLETED":
        output = result.get("output", {})
        if "message" in output:
            print(f"消息: {output['message']}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
测试脚本：测试ComfyUI Worker的视频上传功能

使用方法:
1. 基础测试（使用example-request.json）:
   python test_video_upload.py

2. 指定workflow文件:
   python test_video_upload.py --workflow my-workflow.json

3. 指定视频URL:
   python test_video_upload.py --video-url https://example.com/video.mp4

4. 指定视频名称:
   python test_video_upload.py --video-name input_video.mp4

5. 完整参数示例:
   python test_video_upload.py \
     --workflow my-workflow.json \
     --video-url https://example.com/video.mp4 \
     --video-name test.mp4 \
     --endpoint https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync

环境变量:
  RUNPOD_ENDPOINT: RunPod端点URL
  RUNPOD_API_KEY: RunPod API密钥（如果需要）
"""

import json
import sys
import argparse
import os
from pathlib import Path
import requests
from typing import Dict, Any, Optional


def load_workflow(workflow_path: str) -> Dict[str, Any]:
    """
    从JSON文件加载workflow

    Args:
        workflow_path: workflow JSON文件路径

    Returns:
        workflow字典
    """
    try:
        with open(workflow_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 检查是否已经包含input包装
        if "input" in data:
            return data["input"]["workflow"]
        else:
            return data

    except FileNotFoundError:
        print(f"❌ 错误: 找不到文件 {workflow_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ 错误: JSON解析失败 - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 错误: 加载workflow失败 - {e}")
        sys.exit(1)


def build_request_payload(
    workflow: Dict[str, Any],
    video_url: Optional[str] = None,
    video_name: str = "input_video.mp4",
    video_base64: Optional[str] = None,
    images: Optional[list] = None
) -> Dict[str, Any]:
    """
    构建请求payload

    Args:
        workflow: ComfyUI workflow字典
        video_url: 视频URL（与video_base64二选一）
        video_name: 视频文件名
        video_base64: Base64编码的视频数据（与video_url二选一）
        images: 图像列表（可选）

    Returns:
        完整的请求payload
    """
    payload = {
        "input": {
            "workflow": workflow
        }
    }

    # 添加视频
    if video_url or video_base64:
        video_obj = {"name": video_name}

        if video_url:
            video_obj["url"] = video_url
        elif video_base64:
            video_obj["video"] = video_base64

        payload["input"]["videos"] = [video_obj]

    # 添加图像（如果提供）
    if images:
        payload["input"]["images"] = images

    return payload


def send_request(
    endpoint: str,
    payload: Dict[str, Any],
    api_key: Optional[str] = None,
    timeout: int = 300
) -> Dict[str, Any]:
    """
    发送请求到RunPod端点

    Args:
        endpoint: RunPod端点URL
        payload: 请求payload
        api_key: API密钥（如果需要）
        timeout: 超时时间（秒）

    Returns:
        响应JSON
    """
    headers = {
        "Content-Type": "application/json"
    }

    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    print(f"📤 发送请求到: {endpoint}")
    print(f"⏱️  超时时间: {timeout}秒")

    try:
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=timeout
        )

        response.raise_for_status()
        return response.json()

    except requests.exceptions.Timeout:
        print(f"❌ 错误: 请求超时（超过{timeout}秒）")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ 错误: 请求失败 - {e}")
        if hasattr(e.response, 'text'):
            print(f"响应内容: {e.response.text}")
        sys.exit(1)


def print_request_summary(payload: Dict[str, Any]):
    """打印请求摘要"""
    print("\n" + "="*60)
    print("📋 请求摘要")
    print("="*60)

    input_data = payload.get("input", {})

    # Workflow信息
    workflow = input_data.get("workflow", {})
    if workflow:
        print(f"✅ Workflow节点数: {len(workflow)}")
    else:
        print("⚠️  Workflow为空")

    # 视频信息
    videos = input_data.get("videos", [])
    if videos:
        print(f"🎬 视频数量: {len(videos)}")
        for idx, video in enumerate(videos, 1):
            name = video.get("name", "未命名")
            if "url" in video:
                print(f"   {idx}. {name} (URL: {video['url']})")
            elif "video" in video:
                data_len = len(video['video'])
                print(f"   {idx}. {name} (Base64, {data_len} 字符)")
    else:
        print("ℹ️  无视频")

    # 图像信息
    images = input_data.get("images", [])
    if images:
        print(f"🖼️  图像数量: {len(images)}")
        for idx, image in enumerate(images, 1):
            name = image.get("name", "未命名")
            print(f"   {idx}. {name}")
    else:
        print("ℹ️  无图像")

    print("="*60 + "\n")


def print_response_summary(response: Dict[str, Any]):
    """打印响应摘要"""
    print("\n" + "="*60)
    print("📥 响应摘要")
    print("="*60)

    status = response.get("status", "UNKNOWN")
    print(f"状态: {status}")

    if status == "COMPLETED":
        print("✅ 任务成功完成")

        output = response.get("output", {})
        message = output.get("message", "")
        if message:
            print(f"消息: {message}")

        images = output.get("images", [])
        if images:
            print(f"生成的图像数量: {len(images)}")

    elif status == "FAILED":
        print("❌ 任务失败")

        error = response.get("error", "未知错误")
        print(f"错误: {error}")

        details = response.get("details", [])
        if details:
            print("详细信息:")
            for detail in details:
                print(f"  - {detail}")
    else:
        print(f"⚠️  未知状态: {status}")

    print("="*60 + "\n")


def save_response(response: Dict[str, Any], output_file: str):
    """保存响应到文件"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(response, f, indent=2, ensure_ascii=False)
        print(f"💾 响应已保存到: {output_file}")
    except Exception as e:
        print(f"⚠️  保存响应失败: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="测试ComfyUI Worker的视频上传功能",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--workflow",
        default="example-request.json",
        help="Workflow JSON文件路径 (默认: example-request.json)"
    )

    parser.add_argument(
        "--video-url",
        help="视频URL（与--video-base64互斥）"
    )

    parser.add_argument(
        "--video-base64",
        help="Base64编码的视频数据（与--video-url互斥）"
    )

    parser.add_argument(
        "--video-name",
        default="input_video.mp4",
        help="视频文件名 (默认: input_video.mp4)"
    )

    parser.add_argument(
        "--image-url",
        help="图像URL"
    )

    parser.add_argument(
        "--image-name",
        help="图像文件名"
    )

    parser.add_argument(
        "--endpoint",
        help="RunPod端点URL（也可通过环境变量RUNPOD_ENDPOINT设置）"
    )

    parser.add_argument(
        "--api-key",
        help="RunPod API密钥（也可通过环境变量RUNPOD_API_KEY设置）"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="请求超时时间（秒，默认: 300）"
    )

    parser.add_argument(
        "--output",
        help="保存响应的文件路径（可选）"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅构建请求payload但不发送（用于调试）"
    )

    args = parser.parse_args()

    # 验证参数
    if args.video_url and args.video_base64:
        print("❌ 错误: --video-url 和 --video-base64 不能同时使用")
        sys.exit(1)

    # 获取端点
    endpoint = args.endpoint or os.getenv("RUNPOD_ENDPOINT")
    api_key = args.api_key or os.getenv("RUNPOD_API_KEY")

    if not args.dry_run and not endpoint:
        print("❌ 错误: 必须提供端点URL（通过--endpoint参数或RUNPOD_ENDPOINT环境变量）")
        sys.exit(1)

    # 加载workflow
    print(f"📂 加载workflow: {args.workflow}")
    workflow = load_workflow(args.workflow)
    print(f"✅ Workflow加载成功")

    # 构建图像列表（如果提供）
    images = None
    if args.image_url and args.image_name:
        images = [{"name": args.image_name, "url": args.image_url}]

    # 构建请求payload
    payload = build_request_payload(
        workflow=workflow,
        video_url=args.video_url,
        video_name=args.video_name,
        video_base64=args.video_base64,
        images=images
    )

    # 打印请求摘要
    print_request_summary(payload)

    # Dry run模式
    if args.dry_run:
        print("🔍 Dry run模式 - 仅显示payload，不发送请求\n")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    # 发送请求
    response = send_request(
        endpoint=endpoint,
        payload=payload,
        api_key=api_key,
        timeout=args.timeout
    )

    # 打印响应摘要
    print_response_summary(response)

    # 保存响应（如果指定）
    if args.output:
        save_response(response, args.output)

    # 返回状态码
    status = response.get("status", "UNKNOWN")
    if status == "COMPLETED":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

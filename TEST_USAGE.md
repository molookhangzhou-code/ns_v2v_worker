# 测试脚本使用说明

## 概述

`test_video_upload.py` 是一个用于测试ComfyUI Worker视频上传功能的Python脚本。它可以加载workflow JSON文件并测试视频的URL或Base64上传。

## 前置要求

```bash
pip install requests
```

或者如果你使用 `requirements.txt`:

```bash
pip install -r requirements.txt
```

## 基础使用

### 1. 最简单的测试（Dry Run）

不发送实际请求，只查看构建的payload：

```bash
python test_video_upload.py --dry-run
```

### 2. 使用默认workflow测试

使用 `example-request.json` 作为workflow：

```bash
python test_video_upload.py \
  --endpoint "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync" \
  --video-url "https://example.com/video.mp4"
```

### 3. 使用自定义workflow文件

```bash
python test_video_upload.py \
  --workflow example-video-workflow.json \
  --video-url "https://example.com/sample.mp4" \
  --endpoint "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync"
```

### 4. 指定视频名称

```bash
python test_video_upload.py \
  --workflow example-video-workflow.json \
  --video-url "https://cdn.example.com/video.mp4" \
  --video-name "my_input_video.mp4" \
  --endpoint "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync"
```

### 5. 使用Base64编码的视频

```bash
python test_video_upload.py \
  --workflow example-video-workflow.json \
  --video-base64 "data:video/mp4;base64,AAAAIGZ0eXBpc29tAA..." \
  --endpoint "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync"
```

### 6. 使用API密钥

如果你的端点需要API密钥：

```bash
python test_video_upload.py \
  --workflow example-video-workflow.json \
  --video-url "https://example.com/video.mp4" \
  --endpoint "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync" \
  --api-key "YOUR_API_KEY"
```

### 7. 保存响应到文件

```bash
python test_video_upload.py \
  --workflow example-video-workflow.json \
  --video-url "https://example.com/video.mp4" \
  --endpoint "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync" \
  --output response.json
```

### 8. 设置超时时间

对于长时间运行的任务：

```bash
python test_video_upload.py \
  --workflow example-video-workflow.json \
  --video-url "https://example.com/large-video.mp4" \
  --endpoint "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync" \
  --timeout 600
```

## 使用环境变量

你可以通过环境变量设置端点和API密钥，避免在命令行中重复输入：

```bash
export RUNPOD_ENDPOINT="https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync"
export RUNPOD_API_KEY="YOUR_API_KEY"

# 然后直接运行
python test_video_upload.py \
  --workflow example-video-workflow.json \
  --video-url "https://example.com/video.mp4"
```

或者在Linux/Mac上一次性使用：

```bash
RUNPOD_ENDPOINT="https://..." \
RUNPOD_API_KEY="your-key" \
python test_video_upload.py --video-url "https://example.com/video.mp4"
```

## 命令行参数完整列表

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--workflow` | Workflow JSON文件路径 | `example-request.json` |
| `--video-url` | 视频URL（与--video-base64互斥） | 无 |
| `--video-base64` | Base64编码的视频数据 | 无 |
| `--video-name` | 视频文件名 | `input_video.mp4` |
| `--endpoint` | RunPod端点URL | 从环境变量读取 |
| `--api-key` | RunPod API密钥 | 从环境变量读取 |
| `--timeout` | 请求超时时间（秒） | 300 |
| `--output` | 保存响应的文件路径 | 不保存 |
| `--dry-run` | 只构建payload不发送请求 | False |

## Workflow文件格式

### 格式1: 包含input包装

```json
{
  "input": {
    "workflow": {
      "1": {
        "inputs": {...},
        "class_type": "NodeType"
      }
    }
  }
}
```

### 格式2: 纯workflow（脚本会自动包装）

```json
{
  "1": {
    "inputs": {...},
    "class_type": "NodeType"
  }
}
```

两种格式都支持，脚本会自动处理。

## 输出示例

### 成功的输出

```
📂 加载workflow: example-video-workflow.json
✅ Workflow加载成功

============================================================
📋 请求摘要
============================================================
✅ Workflow节点数: 2
🎬 视频数量: 1
   1. input_video.mp4 (URL: https://example.com/video.mp4)
ℹ️  无图像
============================================================

📤 发送请求到: https://api.runpod.ai/v2/xxx/runsync
⏱️  超时时间: 300秒

============================================================
📥 响应摘要
============================================================
状态: COMPLETED
✅ 任务成功完成
消息: Job completed successfully
生成的图像数量: 10
============================================================

💾 响应已保存到: response.json
```

### 失败的输出

```
============================================================
📥 响应摘要
============================================================
状态: FAILED
❌ 任务失败
错误: Some videos failed to upload
详细信息:
  - Error downloading video from URL for input_video.mp4: 404 Not Found
============================================================
```

## 实际使用案例

### 案例1: 测试视频处理workflow

```bash
# 1. 首先dry run检查payload
python test_video_upload.py \
  --workflow my-video-workflow.json \
  --video-url "https://storage.example.com/test-video.mp4" \
  --dry-run

# 2. 确认无误后发送实际请求
python test_video_upload.py \
  --workflow my-video-workflow.json \
  --video-url "https://storage.example.com/test-video.mp4" \
  --endpoint "$RUNPOD_ENDPOINT" \
  --output test-result.json
```

### 案例2: 批量测试不同视频

```bash
#!/bin/bash

VIDEOS=(
  "https://cdn.example.com/video1.mp4"
  "https://cdn.example.com/video2.mp4"
  "https://cdn.example.com/video3.mp4"
)

for i in "${!VIDEOS[@]}"; do
  echo "Testing video $((i+1))..."
  python test_video_upload.py \
    --workflow my-workflow.json \
    --video-url "${VIDEOS[$i]}" \
    --endpoint "$RUNPOD_ENDPOINT" \
    --output "result_$((i+1)).json"
done
```

### 案例3: 本地视频转Base64测试

```bash
# 将本地视频转为base64
VIDEO_BASE64=$(base64 -i my-video.mp4)

# 测试
python test_video_upload.py \
  --workflow my-workflow.json \
  --video-base64 "data:video/mp4;base64,$VIDEO_BASE64" \
  --endpoint "$RUNPOD_ENDPOINT"
```

## 故障排除

### 问题1: 找不到workflow文件

```
❌ 错误: 找不到文件 my-workflow.json
```

**解决方案**: 检查文件路径是否正确，使用绝对路径或相对路径。

### 问题2: JSON格式错误

```
❌ 错误: JSON解析失败 - Expecting property name enclosed in double quotes
```

**解决方案**: 使用JSON验证工具检查workflow文件格式。

### 问题3: 请求超时

```
❌ 错误: 请求超时（超过300秒）
```

**解决方案**: 使用 `--timeout` 参数增加超时时间。

### 问题4: 端点未设置

```
❌ 错误: 必须提供端点URL
```

**解决方案**: 通过 `--endpoint` 参数或设置 `RUNPOD_ENDPOINT` 环境变量。

## 进阶技巧

### 1. 结合jq处理响应

```bash
python test_video_upload.py \
  --workflow my-workflow.json \
  --video-url "https://example.com/video.mp4" \
  --output response.json

# 提取状态
cat response.json | jq -r '.status'

# 提取错误信息
cat response.json | jq -r '.error'
```

### 2. 监控日志

如果你的端点支持日志流，可以在另一个终端查看：

```bash
# 终端1: 发送请求
python test_video_upload.py --workflow my-workflow.json --video-url "..."

# 终端2: 查看日志
runpodctl logs YOUR_POD_ID --follow
```

### 3. 创建测试配置文件

创建 `test-config.sh`:

```bash
export RUNPOD_ENDPOINT="https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync"
export RUNPOD_API_KEY="your-api-key"
export DEFAULT_WORKFLOW="example-video-workflow.json"
export DEFAULT_TIMEOUT=600
```

使用：

```bash
source test-config.sh
python test_video_upload.py \
  --workflow "$DEFAULT_WORKFLOW" \
  --video-url "https://example.com/video.mp4" \
  --timeout "$DEFAULT_TIMEOUT"
```

## 帮助信息

查看完整的帮助信息：

```bash
python test_video_upload.py --help
```

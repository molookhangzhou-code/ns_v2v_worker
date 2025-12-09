# 测试脚本快速开始

## 快速测试

### 1. 查看脚本会生成什么请求（不实际发送）

```bash
python test_video_upload.py --dry-run
```

### 2. 使用示例workflow测试视频上传

```bash
python test_video_upload.py \
  --workflow example-video-workflow.json \
  --video-url "https://example.com/video.mp4" \
  --endpoint "YOUR_RUNPOD_ENDPOINT" \
  --dry-run
```

### 3. 实际发送请求

```bash
export RUNPOD_ENDPOINT="https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync"

python test_video_upload.py \
  --workflow example-video-workflow.json \
  --video-url "https://example.com/video.mp4"
```

## 文件说明

- `test_video_upload.py` - 主测试脚本
- `example-request.json` - 空的workflow示例
- `example-video-workflow.json` - 视频处理workflow示例
- `TEST_USAGE.md` - 完整使用文档
- `API_DOCUMENTATION.md` - API接口文档

## 更多信息

查看完整文档：`TEST_USAGE.md`

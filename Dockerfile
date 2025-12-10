FROM runpod/worker-comfyui:5.5.1-base

# 调整 handler 配置
RUN sed -i \
    -e 's/^COMFY_API_AVAILABLE_INTERVAL_MS = [0-9]\+/COMFY_API_AVAILABLE_INTERVAL_MS = 500/' \
    -e 's/^COMFY_API_AVAILABLE_MAX_RETRIES = [0-9]\+/COMFY_API_AVAILABLE_MAX_RETRIES = 2000/' \
    /handler.py

# 固定时区，避免 tzdata 交互
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    TRITON_CACHE_DIR=/opt/triton-cache \
    TORCHINDUCTOR_CACHE_DIR=/opt/inductor-cache

# install custom nodes into comfyui
RUN comfy-node-install comfyui_essentials
RUN comfy-node-install https://github.com/kijai/ComfyUI-KJNodes
RUN comfy-node-install https://github.com/1038lab/ComfyUI-RMBG
RUN comfy-node-install https://github.com/yolain/ComfyUI-Easy-Use
RUN comfy-node-install https://github.com/kijai/ComfyUI-GIMM-VFI
RUN comfy-node-install https://github.com/Stability-AI/stability-ComfyUI-nodes
RUN comfy-node-install https://github.com/WASasquatch/was-node-suite-comfyui
RUN comfy-node-install https://github.com/cubiq/ComfyUI_essentials
RUN comfy-node-install https://github.com/chflame163/ComfyUI_LayerStyle
RUN comfy-node-install https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite
RUN comfy-node-install https://github.com/kijai/ComfyUI-WanVideoWrapper
RUN comfy-node-install https://github.com/kijai/ComfyUI-WanAnimatePreprocess
RUN comfy-node-install https://github.com/filliptm/ComfyUI_Fill-Nodes
RUN comfy-node-install https://github.com/9nate-drake/Comfyui-SecNodes

# 修改 handler.py 以支持 video 通过 URL 上传
COPY modify_handler.py /tmp/modify_handler.py
RUN python3 /tmp/modify_handler.py && rm /tmp/modify_handler.py

# 复制额外模型路径配置
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml

# 在原 start.sh 前插入模型路径链接逻辑
RUN sed -i '1a\
# 链接 HuggingFace 缓存到 /runpod-volume/hf-models\n\
CACHE_HUB="/runpod-volume/huggingface-cache/hub"\n\
CACHE_BASE=$(find "${CACHE_HUB}" -maxdepth 1 -type d -name "models--*" 2>/dev/null | head -n 1)\n\
if [ -n "${CACHE_BASE}" ]; then\n\
    SNAPSHOT_DIR=$(find "${CACHE_BASE}/snapshots" -maxdepth 1 -type d ! -name snapshots 2>/dev/null | head -n 1)\n\
    if [ -n "${SNAPSHOT_DIR}" ]; then\n\
        ln -sfn "${SNAPSHOT_DIR}" /runpod-volume/hf-models\n\
        echo "Linked /runpod-volume/hf-models -> ${SNAPSHOT_DIR}"\n\
        ls -la /runpod-volume/hf-models/\n\
    fi\n\
fi\n\
' /start.sh

# 模型通过 RunPod 的 Model URL 功能从 HuggingFace 仓库加载:
# https://huggingface.co/zzl1183635474/v2v

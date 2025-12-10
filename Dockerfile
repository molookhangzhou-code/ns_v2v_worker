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

# 启动脚本 - 直接把整个 models 目录指向 HuggingFace 缓存
RUN echo '#!/bin/bash\n\
CACHE_HUB="/runpod-volume/huggingface-cache/hub"\n\
CACHE_BASE=$(find "${CACHE_HUB}" -maxdepth 1 -type d -name "models--*" 2>/dev/null | head -n 1)\n\
if [ -n "${CACHE_BASE}" ]; then\n\
    SNAPSHOT_DIR=$(find "${CACHE_BASE}/snapshots" -maxdepth 1 -type d ! -name snapshots 2>/dev/null | head -n 1)\n\
    if [ -n "${SNAPSHOT_DIR}" ]; then\n\
        rm -rf /comfyui/models\n\
        ln -sf "${SNAPSHOT_DIR}" /comfyui/models\n\
        echo "Linked /comfyui/models -> ${SNAPSHOT_DIR}"\n\
    fi\n\
fi\n\
exec "$@"\n\
' > /start.sh && chmod +x /start.sh

ENTRYPOINT ["/start.sh"]
CMD ["python", "-u", "/handler.py"]

# 模型通过 RunPod 的 Model URL 功能从 HuggingFace 仓库加载:
# https://huggingface.co/zzl1183635474/v2v

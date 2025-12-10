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

# 添加 ComfyUI 额外模型路径配置
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml

# 预创建模型目录结构，RunPod 启动时会自动链接 HuggingFace 仓库
# 删除默认的空目录，这样 RunPod 可以创建符号链接
RUN rm -rf /comfyui/models/clip_vision && mkdir -p /comfyui/models/clip_vision

# 创建启动脚本 - 补充 RunPod 没有自动链接的目录
RUN echo '#!/bin/bash\n\
# 等待 RunPod 完成模型链接\n\
sleep 2\n\
\n\
# 如果 clip_vision 是空目录，链接到 clip 目录\n\
if [ -d /comfyui/models/clip ] && [ -z "$(ls -A /comfyui/models/clip_vision 2>/dev/null)" ]; then\n\
    rm -rf /comfyui/models/clip_vision\n\
    ln -sf /comfyui/models/clip /comfyui/models/clip_vision\n\
    echo "Linked clip_vision -> clip"\n\
fi\n\
\n\
# 启动主程序\n\
exec "$@"\n\
' > /start.sh && chmod +x /start.sh

ENTRYPOINT ["/start.sh"]
CMD ["python", "-u", "/handler.py"]

# 模型通过 RunPod 的 Model URL 功能从 HuggingFace 仓库加载:
# https://huggingface.co/zzl1183635474/v2v

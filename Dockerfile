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

# download models into comfyui
RUN comfy model download --url https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors --relative-path models/vae --filename wan_2.1_vae.safetensors
RUN comfy model download --url https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LoRAs/Wan22_relight/WanAnimate_relight_lora_fp16_resized_from_128_to_dynamic_22.safetensors --relative-path models/loras --filename WanAnimate_relight_lora_fp16_resized_from_128_to_dynamic_22.safetensors
RUN comfy model download --url https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/Wan22Animate/Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors --relative-path models/unet --filename Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors
RUN comfy model download --url https://huggingface.co/lightx2v/Wan2.2-Distill-Loras/resolve/main/wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors --relative-path models/loras --filename wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors
RUN comfy model download --url https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Pusa/Wan22_PusaV1_lora_LOW_resized_dynamic_avg_rank_98_bf16.safetensors --relative-path models/loras --filename Wan22_PusaV1_lora_LOW_resized_dynamic_avg_rank_98_bf16.safetensors
RUN comfy model download --url https://huggingface.co/alibaba-pai/Wan2.2-Fun-Reward-LoRAs/resolve/main/Wan2.2-Fun-A14B-InP-low-noise-HPS2.1.safetensors --relative-path models/loras --filename Wan2.2-Fun-A14B-InP-low-noise-HPS2.1.safetensors
RUN comfy model download --url https://huggingface.co/VeryAladeen/Sec-4B/resolve/main/SeC-4B-fp16.safetensors?download=true --relative-path models/sams --filename Sec-4B-fp16.safetensors
RUN comfy model download --url https://huggingface.co/Kijai/vitpose_comfy/resolve/ae68f4e542151cebec0995b8469c70b07b8c3df4/onnx/vitpose_h_wholebody_model.onnx --relative-path models/detection --filename vitpose_h_wholebody_model.onnx
RUN comfy model download --url https://huggingface.co/Kijai/vitpose_comfy/resolve/ae68f4e542151cebec0995b8469c70b07b8c3df4/onnx/vitpose_h_wholebody_data.bin --relative-path models/detection --filename vitpose_h_wholebody_data.bin
RUN comfy model download --url https://huggingface.co/Wan-AI/Wan2.2-Animate-14B/resolve/main/process_checkpoint/det/yolov10m.onnx --relative-path models/detection --filename yolov10m.onnx
RUN comfy model download --url https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors --relative-path models/clip --filename CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors
RUN comfy model download --url https://huggingface.co/Bingsu/adetailer/resolve/main/face_yolov8n.pt --relative-path models/ultralytics/bbox --filename face_yolov8n.pt
RUN comfy model download --url https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors --relative-path models/text_encoders --filename umt5_xxl_fp8_e4m3fn_scaled.safetensors

# copy all input data (like images or videos) into comfyui (uncomment and adjust if needed)
# COPY input/ /comfyui/input/
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

# 修复模型路径问题 - 创建 wan/ 子目录的符号链接
# workflow 中的模型路径带有 wan/ 前缀，需要创建对应的目录结构
RUN mkdir -p /comfyui/models/diffusion_models/wan && \
    ln -sf /comfyui/models/unet/Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors /comfyui/models/diffusion_models/wan/Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors

RUN mkdir -p /comfyui/models/loras/wan && \
    ln -sf /comfyui/models/loras/WanAnimate_relight_lora_fp16_resized_from_128_to_dynamic_22.safetensors /comfyui/models/loras/wan/WanAnimate_relight_lora_fp16_resized_from_128_to_dynamic_22.safetensors && \
    ln -sf /comfyui/models/loras/wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors /comfyui/models/loras/wan/wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors && \
    ln -sf /comfyui/models/loras/Wan22_PusaV1_lora_LOW_resized_dynamic_avg_rank_98_bf16.safetensors /comfyui/models/loras/wan/Wan22_PusaV1_lora_LOW_resized_dynamic_avg_rank_98_bf16.safetensors && \
    ln -sf /comfyui/models/loras/Wan2.2-Fun-A14B-InP-low-noise-HPS2.1.safetensors /comfyui/models/loras/wan/Wan2.2-Fun-A14B-InP-low-noise-HPS2.1.safetensors

# CLIP Vision 模型需要放到 clip_vision 目录
RUN mkdir -p /comfyui/models/clip_vision && \
    ln -sf /comfyui/models/clip/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors /comfyui/models/clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors

# NSFW LoRA 模型
RUN comfy model download --url https://huggingface.co/zzl1183635474/MyModel/resolve/main/bounce_test_LowNoise-000005.safetensors --relative-path models/loras/wan --filename bounce_test_LowNoise-000005.safetensors
RUN comfy model download --url https://huggingface.co/rahul7star/wan2.2Lora/resolve/main/NSFW-22-L-e8.safetensors --relative-path models/loras/wan --filename NSFW-22-L-e8.safetensors

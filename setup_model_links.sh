#!/bin/bash
# 从 runpod cached models 创建符号链接到 ComfyUI models 目录
# 这个脚本在容器启动时运行

set -e

# runpod cached models 的基础路径
CACHE_HUB="/runpod-volume/huggingface-cache/hub"

echo "Scanning for cached models at: ${CACHE_HUB}"

# 检查缓存目录是否存在
if [ ! -d "${CACHE_HUB}" ]; then
    echo "WARNING: Cache directory not found: ${CACHE_HUB}"
    echo "Make sure you have configured Model URL in runpod endpoint settings"
    exit 0
fi

# 自动发现第一个 models-- 开头的目录
CACHE_BASE=$(find "${CACHE_HUB}" -maxdepth 1 -type d -name "models--*" | head -n 1)

if [ -z "${CACHE_BASE}" ]; then
    echo "WARNING: No models--* directory found in ${CACHE_HUB}"
    ls -la "${CACHE_HUB}" || true
    exit 0
fi

echo "Found model cache: ${CACHE_BASE}"

# 找到 snapshots 目录下的版本哈希目录
SNAPSHOT_DIR=$(find "${CACHE_BASE}/snapshots" -maxdepth 1 -type d ! -name snapshots | head -n 1)

if [ -z "${SNAPSHOT_DIR}" ]; then
    echo "WARNING: No snapshot directory found in ${CACHE_BASE}/snapshots"
    ls -la "${CACHE_BASE}/snapshots" || true
    exit 0
fi

echo "Found snapshot directory: ${SNAPSHOT_DIR}"

# ComfyUI models 目录
COMFY_MODELS="/comfyui/models"

# 创建所需的目录结构
mkdir -p "${COMFY_MODELS}/vae"
mkdir -p "${COMFY_MODELS}/loras/wan"
mkdir -p "${COMFY_MODELS}/unet"
mkdir -p "${COMFY_MODELS}/sams"
mkdir -p "${COMFY_MODELS}/detection"
mkdir -p "${COMFY_MODELS}/clip"
mkdir -p "${COMFY_MODELS}/clip_vision"
mkdir -p "${COMFY_MODELS}/ultralytics/bbox"
mkdir -p "${COMFY_MODELS}/text_encoders"
mkdir -p "${COMFY_MODELS}/diffusion_models/wan"

# 创建符号链接的函数
link_model() {
    local src="$1"
    local dst="$2"

    if [ -f "${src}" ]; then
        if [ -L "${dst}" ]; then
            rm "${dst}"
        fi
        ln -sf "${src}" "${dst}"
        echo "Linked: ${dst} -> ${src}"
    else
        echo "WARNING: Source file not found: ${src}"
    fi
}

# 链接所有模型文件
# VAE
link_model "${SNAPSHOT_DIR}/vae/wan_2.1_vae.safetensors" "${COMFY_MODELS}/vae/wan_2.1_vae.safetensors"

# LoRAs (根目录)
link_model "${SNAPSHOT_DIR}/loras/WanAnimate_relight_lora_fp16_resized_from_128_to_dynamic_22.safetensors" "${COMFY_MODELS}/loras/WanAnimate_relight_lora_fp16_resized_from_128_to_dynamic_22.safetensors"
link_model "${SNAPSHOT_DIR}/loras/wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors" "${COMFY_MODELS}/loras/wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors"
link_model "${SNAPSHOT_DIR}/loras/Wan22_PusaV1_lora_LOW_resized_dynamic_avg_rank_98_bf16.safetensors" "${COMFY_MODELS}/loras/Wan22_PusaV1_lora_LOW_resized_dynamic_avg_rank_98_bf16.safetensors"
link_model "${SNAPSHOT_DIR}/loras/Wan2.2-Fun-A14B-InP-low-noise-HPS2.1.safetensors" "${COMFY_MODELS}/loras/Wan2.2-Fun-A14B-InP-low-noise-HPS2.1.safetensors"

# LoRAs (wan 子目录)
link_model "${SNAPSHOT_DIR}/loras/wan/bounce_test_LowNoise-000005.safetensors" "${COMFY_MODELS}/loras/wan/bounce_test_LowNoise-000005.safetensors"
link_model "${SNAPSHOT_DIR}/loras/wan/NSFW-22-L-e8.safetensors" "${COMFY_MODELS}/loras/wan/NSFW-22-L-e8.safetensors"

# 同时链接到 loras 根目录（兼容不同的 workflow）
link_model "${SNAPSHOT_DIR}/loras/wan/bounce_test_LowNoise-000005.safetensors" "${COMFY_MODELS}/loras/bounce_test_LowNoise-000005.safetensors"
link_model "${SNAPSHOT_DIR}/loras/wan/NSFW-22-L-e8.safetensors" "${COMFY_MODELS}/loras/NSFW-22-L-e8.safetensors"

# 同时在 wan/ 子目录创建其他 lora 的链接（workflow 可能使用 wan/ 前缀）
link_model "${SNAPSHOT_DIR}/loras/WanAnimate_relight_lora_fp16_resized_from_128_to_dynamic_22.safetensors" "${COMFY_MODELS}/loras/wan/WanAnimate_relight_lora_fp16_resized_from_128_to_dynamic_22.safetensors"
link_model "${SNAPSHOT_DIR}/loras/wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors" "${COMFY_MODELS}/loras/wan/wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors"
link_model "${SNAPSHOT_DIR}/loras/Wan22_PusaV1_lora_LOW_resized_dynamic_avg_rank_98_bf16.safetensors" "${COMFY_MODELS}/loras/wan/Wan22_PusaV1_lora_LOW_resized_dynamic_avg_rank_98_bf16.safetensors"
link_model "${SNAPSHOT_DIR}/loras/Wan2.2-Fun-A14B-InP-low-noise-HPS2.1.safetensors" "${COMFY_MODELS}/loras/wan/Wan2.2-Fun-A14B-InP-low-noise-HPS2.1.safetensors"

# UNET
link_model "${SNAPSHOT_DIR}/unet/Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors" "${COMFY_MODELS}/unet/Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors"

# Diffusion Models (wan 子目录 - 同时链接)
link_model "${SNAPSHOT_DIR}/unet/Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors" "${COMFY_MODELS}/diffusion_models/wan/Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors"

# SAMs
link_model "${SNAPSHOT_DIR}/sams/Sec-4B-fp16.safetensors" "${COMFY_MODELS}/sams/Sec-4B-fp16.safetensors"

# Detection
link_model "${SNAPSHOT_DIR}/detection/vitpose_h_wholebody_model.onnx" "${COMFY_MODELS}/detection/vitpose_h_wholebody_model.onnx"
link_model "${SNAPSHOT_DIR}/detection/vitpose_h_wholebody_data.bin" "${COMFY_MODELS}/detection/vitpose_h_wholebody_data.bin"
link_model "${SNAPSHOT_DIR}/detection/yolov10m.onnx" "${COMFY_MODELS}/detection/yolov10m.onnx"

# CLIP
link_model "${SNAPSHOT_DIR}/clip/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors" "${COMFY_MODELS}/clip/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"

# CLIP Vision (同时链接到 clip_vision 目录)
link_model "${SNAPSHOT_DIR}/clip/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors" "${COMFY_MODELS}/clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"

# Ultralytics
link_model "${SNAPSHOT_DIR}/ultralytics/bbox/face_yolov8n.pt" "${COMFY_MODELS}/ultralytics/bbox/face_yolov8n.pt"

# Text Encoders
link_model "${SNAPSHOT_DIR}/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors" "${COMFY_MODELS}/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"

echo "Model linking completed!"
echo "Listing linked models:"
find "${COMFY_MODELS}" -type l -exec ls -la {} \;

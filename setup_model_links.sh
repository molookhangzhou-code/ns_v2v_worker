#!/bin/bash
# 从 runpod cached models 创建符号链接到 ComfyUI models 目录
# HuggingFace 仓库: https://huggingface.co/zzl1183635474/v2v
# 仓库目录结构已经和 ComfyUI 需要的一致

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
echo "Contents:"
ls -la "${SNAPSHOT_DIR}"

# ComfyUI models 目录
COMFY_MODELS="/comfyui/models"

# 直接链接仓库中的目录到 ComfyUI models 目录
# 仓库结构已经和 ComfyUI 需要的一致

link_dir() {
    local src="$1"
    local dst="$2"

    if [ -d "${src}" ]; then
        # 如果目标已存在，先删除
        if [ -L "${dst}" ]; then
            rm "${dst}"
        elif [ -d "${dst}" ]; then
            rm -rf "${dst}"
        fi
        ln -sf "${src}" "${dst}"
        echo "Linked directory: ${dst} -> ${src}"
    else
        echo "WARNING: Source directory not found: ${src}"
    fi
}

link_file() {
    local src="$1"
    local dst="$2"

    if [ -f "${src}" ]; then
        mkdir -p "$(dirname "${dst}")"
        if [ -L "${dst}" ]; then
            rm "${dst}"
        fi
        ln -sf "${src}" "${dst}"
        echo "Linked: ${dst} -> ${src}"
    else
        echo "WARNING: Source file not found: ${src}"
    fi
}

# 链接整个目录 (仓库结构已经正确)
link_dir "${SNAPSHOT_DIR}/vae" "${COMFY_MODELS}/vae"
link_dir "${SNAPSHOT_DIR}/loras" "${COMFY_MODELS}/loras"
link_dir "${SNAPSHOT_DIR}/diffusion_models" "${COMFY_MODELS}/diffusion_models"
link_dir "${SNAPSHOT_DIR}/sams" "${COMFY_MODELS}/sams"
link_dir "${SNAPSHOT_DIR}/detection" "${COMFY_MODELS}/detection"
link_dir "${SNAPSHOT_DIR}/clip" "${COMFY_MODELS}/clip"
link_dir "${SNAPSHOT_DIR}/clip_vision" "${COMFY_MODELS}/clip_vision"
link_dir "${SNAPSHOT_DIR}/text_encoders" "${COMFY_MODELS}/text_encoders"
link_dir "${SNAPSHOT_DIR}/ultralytics" "${COMFY_MODELS}/ultralytics"

# CLIPLoader 需要在 clip 目录找到 text encoder
# 如果 text_encoders 目录存在，链接其中的文件到 clip 目录
if [ -d "${SNAPSHOT_DIR}/text_encoders" ]; then
    # 确保 clip 目录存在（可能是链接）
    if [ -L "${COMFY_MODELS}/clip" ]; then
        # 如果是链接，需要在实际目录中创建文件链接
        CLIP_DIR=$(readlink -f "${COMFY_MODELS}/clip")
    else
        CLIP_DIR="${COMFY_MODELS}/clip"
        mkdir -p "${CLIP_DIR}"
    fi

    for f in "${SNAPSHOT_DIR}/text_encoders"/*.safetensors; do
        if [ -f "$f" ]; then
            link_file "$f" "${CLIP_DIR}/$(basename "$f")"
        fi
    done
fi

echo ""
echo "Model linking completed!"
echo "Listing linked models:"
find "${COMFY_MODELS}" -maxdepth 3 -type l 2>/dev/null | head -20 || true

#!/bin/bash
# 批量下载ComfyUI模型，用于推送到HuggingFace
# 使用方法: ./download_models.sh [选项]
#
# 选项:
#   -p, --proxy URL     设置代理 (例如: http://127.0.0.1:7890)
#   -x, --threads NUM   每个下载的线程数 (默认: 16)
#   -r, --retries NUM   重试次数 (默认: 10)
#   -h, --help          显示帮助信息

set -e

# 默认配置
TARGET_DIR="comfyui-models"
PROXY=""
THREADS=16
RETRIES=10
RETRY_WAIT=5
SPLIT=16  # aria2 分片数

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--proxy)
            PROXY="$2"
            shift 2
            ;;
        -x|--threads)
            THREADS="$2"
            shift 2
            ;;
        -r|--retries)
            RETRIES="$2"
            shift 2
            ;;
        -h|--help)
            echo "使用方法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  -p, --proxy URL     设置代理 (例如: http://127.0.0.1:7890 或 socks5://127.0.0.1:1080)"
            echo "  -x, --threads NUM   每个下载的线程数 (默认: 16)"
            echo "  -r, --retries NUM   重试次数 (默认: 10)"
            echo "  -h, --help          显示帮助信息"
            echo ""
            echo "示例:"
            echo "  $0 -p http://127.0.0.1:7890"
            echo "  $0 --proxy socks5://127.0.0.1:1080 --threads 32"
            exit 0
            ;;
        *)
            echo -e "${RED}未知选项: $1${NC}"
            exit 1
            ;;
    esac
done

# 检查 aria2 是否安装
if ! command -v aria2c &> /dev/null; then
    echo -e "${RED}错误: aria2 未安装${NC}"
    echo "请先安装 aria2:"
    echo "  macOS:   brew install aria2"
    echo "  Ubuntu:  sudo apt install aria2"
    echo "  CentOS:  sudo yum install aria2"
    exit 1
fi

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}      ComfyUI 模型下载脚本 (aria2)       ${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo -e "目标目录: ${GREEN}${TARGET_DIR}${NC}"
echo -e "线程数: ${GREEN}${THREADS}${NC}"
echo -e "重试次数: ${GREEN}${RETRIES}${NC}"
if [ -n "$PROXY" ]; then
    echo -e "代理: ${GREEN}${PROXY}${NC}"
fi
echo ""

echo "Creating directory structure..."
mkdir -p "${TARGET_DIR}/vae"
mkdir -p "${TARGET_DIR}/loras/wan"
mkdir -p "${TARGET_DIR}/unet"
mkdir -p "${TARGET_DIR}/sams"
mkdir -p "${TARGET_DIR}/detection"
mkdir -p "${TARGET_DIR}/clip"
mkdir -p "${TARGET_DIR}/ultralytics/bbox"
mkdir -p "${TARGET_DIR}/text_encoders"

# 下载函数，使用 aria2 多线程下载
download() {
    local url="$1"
    local output="$2"
    local filename=$(basename "$output")
    local dir=$(dirname "$output")

    if [ -f "$output" ]; then
        # 检查文件是否完整（aria2 会留下 .aria2 文件表示未完成）
        if [ ! -f "${output}.aria2" ]; then
            echo -e "${YELLOW}[SKIP]${NC} $filename already exists"
            return 0
        else
            echo -e "${YELLOW}[RESUME]${NC} $filename 继续下载未完成的文件..."
        fi
    fi

    echo -e "${BLUE}[DOWN]${NC} $filename"
    echo -e "       URL: ${url}"

    # 构建 aria2c 命令
    local aria2_opts=(
        --max-connection-per-server="$THREADS"
        --split="$SPLIT"
        --min-split-size=1M
        --max-tries="$RETRIES"
        --retry-wait="$RETRY_WAIT"
        --connect-timeout=60
        --timeout=600
        --continue=true
        --auto-file-renaming=false
        --allow-overwrite=true
        --console-log-level=notice
        --summary-interval=5
        --show-console-readout=true
        --human-readable=true
        --download-result=full
        --dir="$dir"
        --out="$filename"
    )

    # 如果设置了代理
    if [ -n "$PROXY" ]; then
        aria2_opts+=(--all-proxy="$PROXY")
    fi

    # 执行下载
    local attempt=1
    local max_outer_retries=3

    while [ $attempt -le $max_outer_retries ]; do
        if aria2c "${aria2_opts[@]}" "$url"; then
            echo -e "${GREEN}[DONE]${NC} $filename"
            return 0
        else
            echo -e "${RED}[FAIL]${NC} $filename 下载失败 (尝试 $attempt/$max_outer_retries)"
            if [ $attempt -lt $max_outer_retries ]; then
                echo -e "${YELLOW}[RETRY]${NC} 等待 ${RETRY_WAIT} 秒后重试..."
                sleep $RETRY_WAIT
            fi
            ((attempt++))
        fi
    done

    echo -e "${RED}[ERROR]${NC} $filename 下载失败，已达最大重试次数"
    return 1
}

# 记录失败的下载
FAILED_DOWNLOADS=()

# 安全下载函数（记录失败但不退出）
safe_download() {
    if ! download "$1" "$2"; then
        FAILED_DOWNLOADS+=("$2")
    fi
}

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Downloading VAE models...${NC}"
echo -e "${BLUE}=========================================${NC}"
safe_download "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors" \
         "${TARGET_DIR}/vae/wan_2.1_vae.safetensors"

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Downloading LoRA models...${NC}"
echo -e "${BLUE}=========================================${NC}"
safe_download "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LoRAs/Wan22_relight/WanAnimate_relight_lora_fp16_resized_from_128_to_dynamic_22.safetensors" \
         "${TARGET_DIR}/loras/WanAnimate_relight_lora_fp16_resized_from_128_to_dynamic_22.safetensors"

safe_download "https://huggingface.co/lightx2v/Wan2.2-Distill-Loras/resolve/main/wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors" \
         "${TARGET_DIR}/loras/wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors"

safe_download "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Pusa/Wan22_PusaV1_lora_LOW_resized_dynamic_avg_rank_98_bf16.safetensors" \
         "${TARGET_DIR}/loras/Wan22_PusaV1_lora_LOW_resized_dynamic_avg_rank_98_bf16.safetensors"

safe_download "https://huggingface.co/alibaba-pai/Wan2.2-Fun-Reward-LoRAs/resolve/main/Wan2.2-Fun-A14B-InP-low-noise-HPS2.1.safetensors" \
         "${TARGET_DIR}/loras/Wan2.2-Fun-A14B-InP-low-noise-HPS2.1.safetensors"

safe_download "https://huggingface.co/zzl1183635474/MyModel/resolve/main/bounce_test_LowNoise-000005.safetensors" \
         "${TARGET_DIR}/loras/wan/bounce_test_LowNoise-000005.safetensors"

safe_download "https://huggingface.co/rahul7star/wan2.2Lora/resolve/main/NSFW-22-L-e8.safetensors" \
         "${TARGET_DIR}/loras/wan/NSFW-22-L-e8.safetensors"

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Downloading UNET model (large file ~14GB)...${NC}"
echo -e "${BLUE}=========================================${NC}"
safe_download "https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/Wan22Animate/Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors" \
         "${TARGET_DIR}/unet/Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors"

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Downloading SAM models...${NC}"
echo -e "${BLUE}=========================================${NC}"
safe_download "https://huggingface.co/VeryAladeen/Sec-4B/resolve/main/SeC-4B-fp16.safetensors" \
         "${TARGET_DIR}/sams/Sec-4B-fp16.safetensors"

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Downloading Detection models...${NC}"
echo -e "${BLUE}=========================================${NC}"
safe_download "https://huggingface.co/Kijai/vitpose_comfy/resolve/ae68f4e542151cebec0995b8469c70b07b8c3df4/onnx/vitpose_h_wholebody_model.onnx" \
         "${TARGET_DIR}/detection/vitpose_h_wholebody_model.onnx"

safe_download "https://huggingface.co/Kijai/vitpose_comfy/resolve/ae68f4e542151cebec0995b8469c70b07b8c3df4/onnx/vitpose_h_wholebody_data.bin" \
         "${TARGET_DIR}/detection/vitpose_h_wholebody_data.bin"

safe_download "https://huggingface.co/Wan-AI/Wan2.2-Animate-14B/resolve/main/process_checkpoint/det/yolov10m.onnx" \
         "${TARGET_DIR}/detection/yolov10m.onnx"

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Downloading CLIP models...${NC}"
echo -e "${BLUE}=========================================${NC}"
safe_download "https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors" \
         "${TARGET_DIR}/clip/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Downloading Ultralytics models...${NC}"
echo -e "${BLUE}=========================================${NC}"
safe_download "https://huggingface.co/Bingsu/adetailer/resolve/main/face_yolov8n.pt" \
         "${TARGET_DIR}/ultralytics/bbox/face_yolov8n.pt"

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Downloading Text Encoder models (large file ~4GB)...${NC}"
echo -e "${BLUE}=========================================${NC}"
safe_download "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors" \
         "${TARGET_DIR}/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"

echo ""
echo -e "${BLUE}=========================================${NC}"
if [ ${#FAILED_DOWNLOADS[@]} -eq 0 ]; then
    echo -e "${GREEN}Download complete! All files downloaded successfully.${NC}"
else
    echo -e "${YELLOW}Download complete with some failures:${NC}"
    for failed in "${FAILED_DOWNLOADS[@]}"; do
        echo -e "  ${RED}✗${NC} $failed"
    done
    echo ""
    echo -e "${YELLOW}可以重新运行脚本来重试失败的下载${NC}"
fi
echo -e "${BLUE}=========================================${NC}"
echo ""
echo -e "${GREEN}Directory structure:${NC}"
find "${TARGET_DIR}" -type f -exec ls -lh {} \; 2>/dev/null || true
echo ""
echo -e "${GREEN}Total size:${NC}"
du -sh "${TARGET_DIR}" 2>/dev/null || echo "N/A"
echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}To upload to HuggingFace:${NC}"
echo -e "${BLUE}=========================================${NC}"
echo "  cd ${TARGET_DIR}"
echo "  huggingface-cli login"
echo "  huggingface-cli upload YOUR_USERNAME/comfyui-models . --repo-type model"
echo ""

# 如果有失败的下载，返回非零状态码
if [ ${#FAILED_DOWNLOADS[@]} -gt 0 ]; then
    exit 1
fi

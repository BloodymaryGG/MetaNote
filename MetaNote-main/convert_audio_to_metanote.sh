#!/bin/bash
# convert_audio_to_metanote.sh
# 将纯音频文件转换为MetaNote可处理的MP4文件

# 检查是否提供了输入文件
if [ -z "$1" ]; then
    echo "使用方法: $0 <音频文件>"
    echo "示例: $0 我的录音.mp3"
    exit 1
fi

INPUT_AUDIO="$1"
OUTPUT_VIDEO="${INPUT_AUDIO%.*}_for_metanote.mp4"

echo "正在处理: $INPUT_AUDIO"

# 检查ffmpeg是否安装
if ! command -v ffmpeg &> /dev/null; then
    echo "错误: ffmpeg未安装，请先安装ffmpeg"
    echo "安装命令: brew install ffmpeg (macOS) 或 sudo apt install ffmpeg (Linux)"
    exit 1
fi

# 获取脚本所在目录，用于存放dummy.jpg
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DUMMY_IMAGE="$SCRIPT_DIR/dummy.jpg"

# 生成一个2x2的黑色图片（如果不存在）
if [ ! -f "$DUMMY_IMAGE" ]; then
    echo "正在生成静态图片..."
    ffmpeg -f lavfi -i color=c=black:s=2x2:r=1 -frames:v 1 -y "$DUMMY_IMAGE" 2>/dev/null
fi

# 转换音频为MP4
echo "正在转换音频为MP4格式..."
ffmpeg -loop 1 -i "$DUMMY_IMAGE" -i "$INPUT_AUDIO" \
       -c:v libx264 -tune stillimage -c:a aac -b:a 128k \
       -shortest -pix_fmt yuv420p \
       -vf "scale=640:480" \
       "$OUTPUT_VIDEO"

# 检查转换是否成功
if [ $? -eq 0 ] && [ -f "$OUTPUT_VIDEO" ]; then
    echo "✅ 转换完成: $OUTPUT_VIDEO"
    echo "现在可以上传到MetaNote进行处理"
    echo "文件大小:" $(du -h "$OUTPUT_VIDEO" | cut -f1)
else
    echo "❌ 转换失败，请检查错误信息"
    exit 1
fi

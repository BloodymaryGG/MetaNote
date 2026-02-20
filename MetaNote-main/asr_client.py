"""
ASR客户端模块
用于与ASR服务通信，处理音频文件的语音识别
"""

import os
import json
import logging
import requests
import subprocess
from typing import Dict, Any, List, Optional
import re
logger = logging.getLogger(__name__)

class ASRClient:
    """ASR客户端类"""
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        """
        初始化ASR客户端
        
        Args:
            server_url: ASR服务器URL
        """
        self.server_url = server_url.rstrip('/')
    
    def check_health(self) -> bool:
        """
        检查ASR服务健康状态
        
        Returns:
            服务是否健康
        """
        try:
            response = requests.get(f"{self.server_url}/health")
            if response.status_code == 200:
                data = response.json()
                logger.info(f"服务状态: {data['status']}")
                logger.info(f"模型已加载: {data['model_loaded']}")
                return data['model_loaded']
            else:
                logger.error(f"服务检查失败: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            logger.error("无法连接到ASR服务，请确保服务正在运行")
            return False
        except Exception as e:
            logger.error(f"检查服务健康状态时出错: {str(e)}")
            return False
    
    def recognize_audio(self, audio_path: str) -> Optional[Dict[str, Any]]:
        """
        调用ASR API进行语音识别
        
        Args:
            audio_path: 音频文件路径
        
        Returns:
            识别结果，失败时返回None
        """
        # 检查文件是否存在
        if not os.path.exists(audio_path):
            logger.error(f"文件不存在: {audio_path}")
            return None
        
        # 准备文件
        files = {
            'file': (os.path.basename(audio_path), open(audio_path, 'rb'))
        }
        
        try:
            # 发送请求
            logger.info(f"正在识别音频文件: {audio_path}")
            response = requests.post(f"{self.server_url}/asr/recognize", files=files)
            
            # 关闭文件
            files['file'][1].close()
            
            # 处理响应
            if response.status_code == 200:
                result = response.json()
                logger.info(f"识别成功!")
                logger.info(f"文件名: {result['filename']}")
                logger.info(f"处理时间: {result.get('processing_time', 'N/A')}")
                return result
            else:
                logger.error(f"识别失败: {response.status_code}")
                logger.error(f"错误信息: {response.text}")
                return None
                
        except requests.exceptions.ConnectionError:
            logger.error("无法连接到ASR服务，请确保服务正在运行")
            return None
        except Exception as e:
            logger.error(f"识别时发生错误: {str(e)}")
            # 确保文件句柄被关闭
            try:
                files['file'][1].close()
            except:
                pass
            return None
    
    def process_video(self, video_path: str, extract_audio_func=None) -> Optional[Dict[str, Any]]:
        """
        处理视频文件的音频
        
        Args:
            video_path: 视频文件路径
            extract_audio_func: 提取音频的函数，需要接受视频路径并返回音频路径
            
        Returns:
            识别结果，失败时返回None
        """
        if not extract_audio_func:
            logger.error("未提供提取音频函数")
            return None
            
        try:
            # 提取音频
            audio_path = extract_audio_func(video_path)
            if not audio_path:
                logger.error("从视频提取音频失败")
                return None
                
            # 识别音频
            result = self.recognize_audio(audio_path)
            
            # 清理临时音频文件
            if os.path.exists(audio_path):
                try:
                    os.unlink(audio_path)
                except Exception as e:
                    logger.warning(f"清理临时音频文件失败: {str(e)}")
            
            return result
            
        except Exception as e:
            logger.error(f"处理视频时出错: {str(e)}")
            return None

    def recognize_multiple_files(self, audio_files: List[str]) -> List[Dict[str, Any]]:
        """
        批量识别多个音频文件
        
        Args:
            audio_files: 音频文件路径列表
        
        Returns:
            识别结果列表
        """
        results = []
        for audio_file in audio_files:
            logger.info(f"\n正在处理文件: {audio_file}")
            result = self.recognize_audio(audio_file)
            if result:
                results.append({
                    "file": audio_file,
                    "result": result
                })
        return results
    
class LocalASRClient:
    """本地 whisper.cpp ASR 客户端类"""
    
    def __init__(self, whisper_cli_path: str, model_path: str):
        """
        初始化本地 ASR 客户端
        
        Args:
            whisper_cli_path: whisper-cli 可执行文件路径
            model_path: ggml 模型文件路径
        """
        self.whisper_cli_path = whisper_cli_path
        self.model_path = model_path
    
    def check_health(self) -> bool:
        """
        检查本地 ASR 是否就绪（检查文件是否存在）
        
        Returns:
            模型和可执行文件是否存在
        """
        return os.path.exists(self.whisper_cli_path) and os.path.exists(self.model_path)
    
    def recognize_audio(self, audio_path: str) -> Optional[Dict[str, Any]]:
        # ... 前面的代码（命令构建等）保持不变 ...
        command = [
            self.whisper_cli_path,
            "-m", self.model_path,
            "-f", audio_path,
            "-otxt",
            "-l", "zh",  # 如果是中文课程视频
            "-pc"
        ]
        logger.info(f"执行命令: {' '.join(command)}")
        # 注意：这里暂时去掉 encoding='utf-8' 参数，先获取原始字节
        # ===== 设置动态库路径（使用绝对路径） =====
        # 将 whisper_cli_path 转换为绝对路径
        abs_cli_path = os.path.abspath(self.whisper_cli_path)
        cli_dir = os.path.dirname(abs_cli_path)          # .../build/bin
        build_dir = os.path.dirname(cli_dir)              # .../build
    
        # 列出所有可能的库目录（绝对路径）
        possible_lib_dirs = [
            os.path.join(build_dir, "src"),                       # .../build/src
            os.path.join(build_dir, "ggml", "src"),               # .../build/ggml/src
            os.path.join(build_dir, "ggml", "src", "ggml-blas"),  # .../build/ggml/src/ggml-blas
            os.path.join(build_dir, "ggml", "src", "ggml-metal"), # .../build/ggml/src/ggml-metal
        ]
    
        # 只保留实际存在的目录
        existing_lib_dirs = [d for d in possible_lib_dirs if os.path.exists(d)]
    
        env = os.environ.copy()
        if existing_lib_dirs:
            # 用冒号拼接所有库目录
            lib_path = ":".join(existing_lib_dirs)
            existing_dyld = env.get('DYLD_LIBRARY_PATH', '')
            if existing_dyld:
                env['DYLD_LIBRARY_PATH'] = lib_path + ":" + existing_dyld
            else:
                env['DYLD_LIBRARY_PATH'] = lib_path
            logger.info(f"设置 DYLD_LIBRARY_PATH={env['DYLD_LIBRARY_PATH']}")
        # ================================
    
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                check=False,
                timeout=120,
                env=env  # 传入环境变量
            )

            # 1. 首先，无论成功与否，都记录原始返回码和输出大小
            logger.info(f"命令执行完成，返回码: {result.returncode}")
            logger.info(f"标准输出原始字节长度: {len(result.stdout)}")
            logger.info(f"标准错误原始字节长度: {len(result.stderr)}")
            
            # 2. 尝试安全地解码输出（优先使用utf-8，失败则用错误忽略策略）
            stdout_text = ""
            stderr_text = ""
            try:
                stdout_text = result.stdout.decode('utf-8')
            except UnicodeDecodeError:
                # 如果utf-8解码失败，使用错误忽略模式，确保得到部分文本
                stdout_text = result.stdout.decode('utf-8', errors='ignore')
                logger.warning("标准输出包含非UTF-8字符，已忽略。")
            
            try:
                stderr_text = result.stderr.decode('utf-8')
            except UnicodeDecodeError:
                stderr_text = result.stderr.decode('utf-8', errors='ignore')
            # ========== 新增：去除 ANSI 转义序列 ==========
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            stdout_text = ansi_escape.sub('', stdout_text)
            # =============================================

            # 继续解析段落（使用清理后的文本）
            segments = []
            lines = stdout_text.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('[') and '-->' in line:
                    try:
                        time_part, text = line.split(']', 1)
                        time_part = time_part.strip('[')
                        start_time, end_time = time_part.split('-->')
                        segments.append({
                            "start": start_time.strip(),
                            "end": end_time.strip(),
                            "text": text.strip()   # text 现在已不含 ANSI 码
                        })
                    except Exception as parse_error:
                        logger.warning(f"解析行时出错（已跳过）: {line[:100]}... 错误: {parse_error}")
            # 3. 记录解码后的文本（前500字符）
            if stderr_text:
                logger.info(f"标准错误 (解码后): {stderr_text[:500]}")
            
            # 4. 判断是否成功：返回码为0通常意味着成功
            if result.returncode == 0:
                # 成功！现在 stdout_text 应该包含带时间戳的转录文本
                logger.info(f"语音识别成功！输出文本长度: {len(stdout_text)} 字符")
                
                # ========== 解析 whisper-cli 的输出文本 ==========
                segments = []
                lines = stdout_text.strip().split('\n')
                
                for line in lines:
                    line = line.strip()
                    # 匹配类似 "[00:00:00.000 --> 00:00:10.500]  这里是文本" 的行
                    if line.startswith('[') and '-->' in line:
                        try:
                            # 分割时间戳和文本
                            time_part, text = line.split(']', 1)
                            time_part = time_part.strip('[')  # 移除开头的'['
                            start_time, end_time = time_part.split('-->')
                            
                            segments.append({
                                "start": start_time.strip(),
                                "end": end_time.strip(),
                                "text": text.strip()
                            })
                        except Exception as parse_error:
                            # 如果某一行解析失败，记录警告但继续处理其他行
                            logger.warning(f"解析行时出错（已跳过）: {line[:100]}... 错误: {parse_error}")
                
                logger.info(f"成功解析出 {len(segments)} 个文本段落")
                # ========== 解析结束 ==========
                
                # 返回解析后的结果字典
                return {
                    "status": "success",
                    "filename": os.path.basename(audio_path),
                    "segments": segments,  # 使用上面解析出来的段落列表
                    "full_text": stdout_text,  # 完整的原始输出文本
                    "processing_time": None,
                    "model": "whisper.cpp-ggml-base"
                }
            else:
                # 命令执行失败（返回非零码）
                logger.error(f"whisper-cli 执行失败，返回码: {result.returncode}")
                logger.error(f"错误详情 (stderr): {stderr_text[:1000]}")  # 显示前1000字符
                return None
                
        except subprocess.TimeoutExpired:
            logger.error(f"命令执行超时（超过120秒）")
            return None
        except FileNotFoundError:
            logger.error(f"找不到命令或文件: {self.whisper_cli_path}")
            return None
        except Exception as e:
            logger.error(f"执行命令时发生未知错误: {str(e)}", exc_info=True)
            return None
    
    # 以下方法可以保持与原 ASRClient 相同的接口，内部调用 recognize_audio
    def process_video(self, video_path: str, extract_audio_func=None) -> Optional[Dict[str, Any]]:
        """处理视频文件的音频（接口兼容）"""
        # 这里可以复用原 ASRClient 的 process_video 逻辑，只需替换 recognize_audio 调用
        # 或者直接调用原 ASRClient 的 process_video 方法，但需要稍作调整
        pass

# 便捷函数
def recognize_audio(audio_path: str, server_url: str = "http://localhost:8000") -> Optional[Dict[str, Any]]:
    """
    识别音频文件的便捷函数
    
    Args:
        audio_path: 音频文件路径
        server_url: ASR服务器URL
        
    Returns:
        识别结果，失败时返回None
    """
    client = ASRClient(server_url)
    return client.recognize_audio(audio_path)


if __name__ == "__main__":
    import argparse
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="ASR客户端")
    parser.add_argument("--server", default="http://localhost:8000", help="ASR服务器URL")
    parser.add_argument("--file", help="要识别的音频文件路径")
    parser.add_argument("--check", action="store_true", help="检查服务健康状态")
    
    args = parser.parse_args()
    
    # 创建客户端
    client = ASRClient(args.server)
    
    # 检查服务
    if args.check:
        health = client.check_health()
        print(f"服务健康状态: {'正常' if health else '异常'}")
    
    # 识别文件
    if args.file:
        if not os.path.exists(args.file):
            print(f"文件不存在: {args.file}")
            exit(1)
            
        result = client.recognize_audio(args.file)
        if result:
            print("\n识别结果:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("识别失败")
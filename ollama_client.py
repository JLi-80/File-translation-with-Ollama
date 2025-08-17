#!/usr/bin/env python3
"""
ollama_client.py
负责与Ollama API通讯交互的独立模块，包含异常处理和重试机制。
"""

import sys
import time
import json
import subprocess
import platform
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

import requests


class OllamaClientError(Exception):
    """Ollama客户端异常基类"""
    pass


class OllamaConnectionError(OllamaClientError):
    """连接相关异常"""
    pass


class OllamaAPIError(OllamaClientError):
    """API调用异常"""
    pass


class OllamaTimeoutError(OllamaClientError):
    """超时异常"""
    pass


class OllamaServiceError(OllamaClientError):
    """Ollama服务相关异常"""
    pass


class OllamaClient:
    """
    Ollama API客户端类，负责与Ollama服务进行通讯交互
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Ollama客户端
        
        Args:
            config: 包含Ollama配置的字典
        """
        self.url = config["url"]
        self.model_name = config["model_name"]
        self.temperature = config["temperature"]
        self.top_p = config["top_p"]
        self.repeat_penalty = config["repeat_penalty"]
        self.timeout = config["timeout"]
        self.retries = config["retries"]
        
    def _create_payload(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        """
        创建API请求的payload
        
        Args:
            prompt: 用户输入的提示
            system_prompt: 系统提示
            
        Returns:
            包含请求参数的字典
        """
        return {
            "model": self.model_name,
            "system": system_prompt,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "top_p": self.top_p,
                "repeat_penalty": self.repeat_penalty
            },
        }
    
    def _handle_response(self, response: requests.Response) -> Tuple[str, list]:
        """
        处理API响应
        
        Args:
            response: requests响应对象
            
        Returns:
            (响应文本, 上下文信息)
            
        Raises:
            OllamaAPIError: 当API返回错误时
        """
        try:
            response.raise_for_status()
            json_resp = response.json()
            return json_resp["response"].strip(), json_resp.get("context", [])
        except requests.exceptions.HTTPError as e:
            raise OllamaAPIError(f"HTTP错误: {e.response.status_code} - {e.response.text}")
        except json.JSONDecodeError as e:
            raise OllamaAPIError(f"JSON解析错误: {e}")
        except KeyError as e:
            raise OllamaAPIError(f"响应格式错误，缺少字段: {e}")
    
    def _make_request(self, payload: Dict[str, Any]) -> Tuple[str, list]:
        """
        发送API请求
        
        Args:
            payload: 请求参数
            
        Returns:
            (响应文本, 上下文信息)
            
        Raises:
            OllamaConnectionError: 连接错误
            OllamaTimeoutError: 超时错误
            OllamaAPIError: API错误
        """
        try:
            response = requests.post(
                self.url, 
                json=payload, 
                timeout=self.timeout
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            raise OllamaConnectionError(f"连接失败: {e}")
        except requests.exceptions.Timeout as e:
            raise OllamaTimeoutError(f"请求超时: {e}")
        except requests.exceptions.RequestException as e:
            raise OllamaConnectionError(f"请求异常: {e}")
    
    def translate(self, text: str, system_prompt: str, retries: Optional[int] = None) -> Tuple[str, list]:
        """
        翻译文本片段
        
        Args:
            text: 待翻译的文本
            system_prompt: 系统提示
            retries: 重试次数，如果为None则使用默认配置
            
        Returns:
            (翻译后的文本, 上下文信息)
            
        Raises:
            OllamaClientError: 当所有重试都失败时
        """
        if retries is None:
            retries = self.retries
            
        payload = self._create_payload(text, system_prompt)
        
        last_exception = None
        for attempt in range(1, retries + 1):
            try:
                return self._make_request(payload)
            except (OllamaConnectionError, OllamaTimeoutError, OllamaAPIError) as e:
                last_exception = e
                print(f"[WARN] 第 {attempt} 次尝试失败: {e}", file=sys.stderr)
                
                if attempt < retries:
                    # 指数退避策略
                    sleep_time = min(2 ** attempt, 30)  # 最大等待30秒
                    print(f"[INFO] 等待 {sleep_time} 秒后重试...", file=sys.stderr)
                    time.sleep(sleep_time)
        
        # 所有重试都失败了
        raise OllamaClientError(f"翻译失败，已重试 {retries} 次。最后一次错误: {last_exception}")
    
    def test_connection(self) -> bool:
        """
        测试与Ollama服务的连接
        
        Returns:
            True如果连接成功，False否则
        """
        try:
            # 发送一个简单的测试请求
            test_payload = {
                "model": self.model_name,
                "prompt": "Hello",
                "stream": False
            }
            response = requests.post(self.url, json=test_payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[ERROR] 连接测试失败: {e}", file=sys.stderr)
            return False
    
    def _get_ollama_command(self) -> str:
        """
        获取Ollama命令，根据操作系统返回适当的命令
        
        Returns:
            Ollama命令字符串
        """
        if platform.system() == "Windows":
            return "ollama"
        else:
            return "ollama"
    
    def _get_start_command(self) -> str:
        """
        获取启动Ollama服务的命令
        
        Returns:
            启动命令字符串
        """
        if platform.system() == "Windows":
            return f"{self._get_ollama_command()} serve"
        else:
            return f"{self._get_ollama_command()} serve"
    
    def stop_service(self, timeout: int = 30) -> bool:
        """
        停止Ollama服务
        
        Args:
            timeout: 等待停止的超时时间（秒）
            
        Returns:
            True如果成功停止，False否则
            
        Raises:
            OllamaServiceError: 当停止服务失败时
        """
        try:
            print("[INFO] 正在停止Ollama服务...", file=sys.stderr)
            cmd = f"{self._get_ollama_command()} stop"
            
            # 在Windows上使用shell=True，在其他系统上不使用
            shell = platform.system() == "Windows"
            result = subprocess.run(cmd, shell=shell, timeout=timeout, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("[INFO] Ollama服务已停止", file=sys.stderr)
                return True
            else:
                print(f"[WARN] 停止Ollama服务时出现警告: {result.stderr}", file=sys.stderr)
                # 即使有警告，也认为停止成功
                return True
                
        except subprocess.TimeoutExpired:
            raise OllamaServiceError(f"停止Ollama服务超时（{timeout}秒）")
        except subprocess.CalledProcessError as e:
            raise OllamaServiceError(f"停止Ollama服务失败: {e}")
        except Exception as e:
            raise OllamaServiceError(f"停止Ollama服务时发生未知错误: {e}")
    
    def start_service(self, timeout: int = 60) -> bool:
        """
        启动Ollama服务
        
        Args:
            timeout: 等待启动的超时时间（秒）
            
        Returns:
            True如果成功启动，False否则
            
        Raises:
            OllamaServiceError: 当启动服务失败时
        """
        try:
            print("[INFO] 正在启动Ollama服务...", file=sys.stderr)
            cmd = self._get_start_command()
            
            # 在Windows上使用start命令后台启动
            if platform.system() == "Windows":
                cmd = f"start /B {cmd}"
                shell = True
            else:
                shell = False
            
            # 启动服务（不等待完成）
            process = subprocess.Popen(cmd, shell=shell)
            
            # 等待服务启动
            print("[INFO] 等待Ollama服务启动...", file=sys.stderr)
            time.sleep(5)  # 先等待5秒
            
            # 检查服务是否启动成功
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.test_connection():
                    print("[INFO] Ollama服务启动成功", file=sys.stderr)
                    return True
                time.sleep(2)
            
            # 如果超时仍未启动成功
            raise OllamaServiceError(f"启动Ollama服务超时（{timeout}秒）")
            
        except subprocess.CalledProcessError as e:
            raise OllamaServiceError(f"启动Ollama服务失败: {e}")
        except Exception as e:
            raise OllamaServiceError(f"启动Ollama服务时发生未知错误: {e}")
    
    def restart_service(self, stop_timeout: int = 30, start_timeout: int = 60) -> bool:
        """
        重启Ollama服务
        
        Args:
            stop_timeout: 停止服务的超时时间（秒）
            start_timeout: 启动服务的超时时间（秒）
            
        Returns:
            True如果成功重启，False否则
            
        Raises:
            OllamaServiceError: 当重启服务失败时
        """
        try:
            print("[INFO] 开始重启Ollama服务...", file=sys.stderr)
            
            # 1. 停止服务
            self.stop_service(stop_timeout)
            
            # 2. 等待一段时间确保服务完全停止
            time.sleep(2)
            
            # 3. 启动服务
            return self.start_service(start_timeout)
            
        except OllamaServiceError as e:
            raise OllamaServiceError(f"重启Ollama服务失败: {e}")
        except Exception as e:
            raise OllamaServiceError(f"重启Ollama服务时发生未知错误: {e}")
    
    def check_service_status(self) -> Dict[str, Any]:
        """
        检查Ollama服务状态
        
        Returns:
            包含服务状态信息的字典
        """
        status = {
            "running": False,
            "connectable": False,
            "error": None
        }
        
        try:
            # 测试连接
            status["connectable"] = self.test_connection()
            status["running"] = status["connectable"]
        except Exception as e:
            status["error"] = str(e)
        
        return status


def create_ollama_client(config: Dict[str, Any]) -> OllamaClient:
    """
    创建Ollama客户端实例的工厂函数
    
    Args:
        config: 配置字典
        
    Returns:
        OllamaClient实例
    """
    return OllamaClient(config)


def load_ollama_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    加载Ollama配置
    
    Args:
        config_path: 配置文件路径，如果为None则使用默认路径
        
    Returns:
        配置字典
    """
    if config_path is None:
        config_path = Path(__file__).parent / "settings.json"
    
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get("ollama", {})
        except (json.JSONDecodeError, IOError) as e:
            print(f"警告: 无法读取配置文件 {config_path}: {e}", file=sys.stderr)
            print("使用默认配置", file=sys.stderr)
    
    # 默认配置
    return {
        "url": "http://localhost:11434/api/generate",
        "model_name": "gemma3:latest",
        "temperature": 0.1,
        "top_p": 0.9,
        "repeat_penalty": 1.2,
        "timeout": 240,
        "retries": 3
    }

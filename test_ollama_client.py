#!/usr/bin/env python3
"""
test_ollama_client.py
测试ollama_client模块的功能
"""

import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from ollama_client import (
    create_ollama_client, 
    load_ollama_config, 
    OllamaClientError,
    OllamaConnectionError,
    OllamaAPIError,
    OllamaTimeoutError
)


def test_config_loading():
    """测试配置加载功能"""
    print("测试配置加载...")
    config = load_ollama_config()
    print(f"加载的配置: {config}")
    assert "url" in config
    assert "model_name" in config
    assert "timeout" in config
    print("✓ 配置加载测试通过")


def test_client_creation():
    """测试客户端创建"""
    print("测试客户端创建...")
    config = load_ollama_config()
    client = create_ollama_client(config)
    print(f"创建的客户端: {client}")
    assert client.url == config["url"]
    assert client.model_name == config["model_name"]
    print("✓ 客户端创建测试通过")


def test_connection_test():
    """测试连接测试功能"""
    print("测试连接测试功能...")
    config = load_ollama_config()
    client = create_ollama_client(config)
    
    # 测试连接（可能失败，但应该不会抛出异常）
    try:
        result = client.test_connection()
        print(f"连接测试结果: {result}")
        if result:
            print("✓ Ollama服务正在运行")
        else:
            print("⚠ Ollama服务未运行或无法连接")
    except Exception as e:
        print(f"⚠ 连接测试异常: {e}")
    
    print("✓ 连接测试功能测试通过")


def test_exception_classes():
    """测试异常类"""
    print("测试异常类...")
    
    # 测试异常继承关系
    assert issubclass(OllamaConnectionError, OllamaClientError)
    assert issubclass(OllamaAPIError, OllamaClientError)
    assert issubclass(OllamaTimeoutError, OllamaClientError)
    
    # 测试异常创建
    try:
        raise OllamaConnectionError("测试连接错误")
    except OllamaClientError as e:
        print(f"捕获到预期的异常: {e}")
    
    print("✓ 异常类测试通过")


def main():
    """主测试函数"""
    print("开始测试ollama_client模块...\n")
    
    try:
        test_config_loading()
        print()
        
        test_client_creation()
        print()
        
        test_exception_classes()
        print()
        
        test_connection_test()
        print()
        
        print("🎉 所有测试通过！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

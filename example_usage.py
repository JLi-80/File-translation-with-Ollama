#!/usr/bin/env python3
"""
example_usage.py
展示如何使用ollama_client模块的示例
"""

import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from ollama_client import (
    create_ollama_client, 
    load_ollama_config,
    OllamaClientError
)


def example_basic_usage():
    """基本使用示例"""
    print("=== 基本使用示例 ===")
    
    # 1. 加载配置
    config = load_ollama_config()
    print(f"加载的配置: {config}")
    
    # 2. 创建客户端
    client = create_ollama_client(config)
    print(f"创建的客户端: {client}")
    
    # 3. 测试连接
    if client.test_connection():
        print("✓ Ollama服务连接正常")
    else:
        print("✗ 无法连接到Ollama服务")
        return
    
    # 4. 进行翻译
    system_prompt = "You are a professional translator. Translate the following text into natural, fluent simplified Chinese. DO NOT translate or remove any formating tags. Return ONLY the Chinese translation."
    text_to_translate = "Hello, this is a test message for translation."
    
    try:
        translated_text, context = client.translate(text_to_translate, system_prompt)
        print(f"原文: {text_to_translate}")
        print(f"译文: {translated_text}")
        print(f"上下文: {context}")
    except OllamaClientError as e:
        print(f"翻译失败: {e}")


def example_custom_config():
    """自定义配置示例"""
    print("\n=== 自定义配置示例 ===")
    
    # 自定义配置
    custom_config = {
        "url": "http://localhost:11434/api/generate",
        "model_name": "qwen3:4b-instruct-2507-q8_0",
        "temperature": 0.2,  # 稍微增加随机性
        "top_p": 0.95,
        "repeat_penalty": 1.1,
        "timeout": 120,  # 减少超时时间
        "retries": 2     # 减少重试次数
    }
    
    print(f"自定义配置: {custom_config}")
    
    # 创建客户端
    client = create_ollama_client(custom_config)
    
    # 测试连接
    if client.test_connection():
        print("✓ 使用自定义配置连接成功")
    else:
        print("✗ 使用自定义配置连接失败")


def example_error_handling():
    """错误处理示例"""
    print("\n=== 错误处理示例 ===")
    
    # 使用错误的URL测试错误处理
    bad_config = {
        "url": "http://localhost:9999/api/generate",  # 错误的端口
        "model_name": "test-model",
        "temperature": 0.1,
        "top_p": 0.9,
        "repeat_penalty": 1.2,
        "timeout": 5,  # 短超时
        "retries": 1   # 只重试一次
    }
    
    client = create_ollama_client(bad_config)
    
    try:
        result = client.test_connection()
        print(f"连接测试结果: {result}")
    except Exception as e:
        print(f"预期的连接错误: {e}")
    
    # 测试翻译错误处理
    try:
        translated_text, context = client.translate(
            "Test text", 
            "Translate to Chinese"
        )
    except OllamaClientError as e:
        print(f"预期的翻译错误: {e}")


def main():
    """主函数"""
    print("Ollama客户端模块使用示例\n")
    
    try:
        example_basic_usage()
        example_custom_config()
        example_error_handling()
        
        print("\n🎉 所有示例执行完成！")
        
    except Exception as e:
        print(f"\n❌ 示例执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
translate_with_ollama.py
Split UTF-8 text into approximately 1024 token segments by sentence boundaries,
call the local ollama (http://localhost:11434) to translate into the specified language, and merge the output after translation.

Supported input types (must be UTF-8 plain text):
- txt
- html / htm / xhtml
- md / markdown
- rst (reStructuredText)
- tex / latex
- adoc (AsciiDoc)
- xml (such as DocBook, XHTML, etc.)
- srt / vtt (subtitles, maintaining paragraph block order)

Available but use with caution (may break structure or key names): csv / tsv, yaml / yml, ini / conf / properties, json
Not supported: binary documents such as doc/docx/pdf (please export to plain text or Markdown first)
"""

import argparse
import os
import sys
import time
import subprocess
import json
from pathlib import Path

# 导入文字切片处理模块
from text_slicer import TextSlicer, count_tokens, join_paragraphs_with_separator, split_by_separator
# 导入Ollama客户端模块
from ollama_client import create_ollama_client, load_ollama_config, OllamaClientError, OllamaServiceError

default_translation_settings={
    "target_tokens_per_slice": 1024,
    "target_language": "simplified Chinese",
    "system_prompt": "You are a professional translator. Translate the following text into natural, fluent {target_language} if it's not already in {target_language}. DO NOT translate or remove any formating tags, including HTML/markdown/latex tags such as <table>, <figure>, <equation>, <reference>, etc. DO NOT translate people names, acronyms, equations, hyperlinks, or references. Return ONLY the {target_language} translation, do not include any thinking/reasoning, explanation or note.",
    "para_sep": "<段落分隔符>"
}

def load_settings():
    """
    加载配置文件 settings.json
    返回配置字典，如果文件不存在则使用默认配置
    """
    settings_path = Path(__file__).parent / "settings.json"
    if settings_path.exists():
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 确保配置包含所有必要的部分
                if "ollama" not in config:
                    config["ollama"] = load_ollama_config(settings_path)
                if "translation" not in config:
                    config["translation"] = default_translation_settings
                if "general" not in config:
                    config["general"] = {
                        "skip_connection_test": False, 
                        "timeout": 240,
                        "retries": 3}
                
                # 确保ollama配置包含timeout和retries参数
                config["ollama"]["timeout"] = config["general"]["timeout"]
                config["ollama"]["retries"] = config["general"]["retries"]
                    
                return config
        except (json.JSONDecodeError, IOError) as e:
            print(f"警告: 无法读取配置文件 {settings_path}: {e}", file=sys.stderr)
            print("使用默认配置", file=sys.stderr)
    
    # 默认配置
    default_ollama_config = load_ollama_config(settings_path)
    default_ollama_config["timeout"] = 240
    default_ollama_config["retries"] = 3
    
    return {
        "ollama": default_ollama_config,
        "translation": default_translation_settings,
        "general": {"skip_connection_test": False,
                    "timeout": 240, 
                    "retries": 3}
    }

def get_system_prompt():
    """
    获取处理后的 system prompt，将占位符替换为实际的目标语言
    """
    system_prompt = SETTINGS["translation"]["system_prompt"]
    target_language = SETTINGS["translation"]["target_language"]
    return system_prompt.format(target_language=target_language)

# 加载配置
SETTINGS = load_settings()

# 创建Ollama客户端实例
OLLAMA_CLIENT = create_ollama_client(SETTINGS["ollama"])

# ------------------------------------------------------------------ #

# 调用 ollama 进行翻译
def translate_segment(segment: str, retries: int = None) -> tuple[str, list]:
    """
    调用本地 Ollama API 翻译指定文本片段。
    参数：
        segment: 需要翻译的文本片段
        retries: 失败重试次数，如果为None则使用配置文件中的值
    返回：
        (翻译后的文本, 上下文信息)
    """
    try:
        return OLLAMA_CLIENT.translate(segment, get_system_prompt(), retries)
    except OllamaClientError as e:
        print(f"[ERROR] 翻译失败: {e}", file=sys.stderr)
        raise

def process_empty_group(output_file):
    """
    处理空段落组，直接写入两个换行符。
    """
    output_file.write("\n\n")

def process_long_paragraph_slices(slices, output_file):
    """
    处理长段落切片：分别翻译每个切片后合并。
    参数：
        slices: 长段落切片列表
        output_file: 输出文件对象
    """
    translated = ""
    for seg in slices:
        t, _ = translate_segment(seg)
        translated += t
    output_file.write(translated.strip() + "\n\n")

def process_normal_group(group, output_file):
    """
    处理普通段落组：合并为一段，用分隔符连接，整体翻译后再按分隔符拆分写入。
    参数：
        group: 段落列表
        output_file: 输出文件对象
    """
    para_sep = SETTINGS["translation"]["para_sep"]
    joined = join_paragraphs_with_separator(group, para_sep)
    translated, _ = translate_segment(joined)
    # 按分隔符拆分
    translated_paragraphs = split_by_separator(translated, para_sep)
    for para in translated_paragraphs:
        output_file.write(para + "\n\n")

def main():
    """
    主程序入口：
    1. 解析命令行参数，读取输入文件。
    2. 测试Ollama连接。
    3. 使用TextSlicer进行文本切片处理。
    4. 逐组翻译并写入输出文件。
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input_file",
        help="待翻译的UTF-8 文本文件路径（txt/html/htm/xhtml/md/markdown/rst/tex/latex/adoc/xml/srt/vtt 等）"
    )

    args = parser.parse_args()

    src_path = Path(args.input_file).expanduser().resolve()
    if not src_path.exists():
        sys.exit(f"File does not exist: {src_path}")

    out_path = src_path.with_stem(src_path.stem + "-translated")

    # 测试Ollama连接
    if not SETTINGS["general"]["skip_connection_test"]:
        print("Testing Ollama connection...", file=sys.stderr)
        if not OLLAMA_CLIENT.test_connection():
            sys.exit("Error: Cannot connect to Ollama service. Please ensure Ollama is running.")
        print("Ollama connection test passed", file=sys.stderr)

    # 读取原文
    text = src_path.read_text(encoding="utf-8")

    # 创建文本切片器
    slicer = TextSlicer(
        target_tokens=SETTINGS["translation"]["target_tokens_per_slice"],
        para_separator=SETTINGS["translation"]["para_sep"]
    )
    
    # 处理文本切片
    slices = slicer.process_text(text)
    print(f"Generated {len(slices)} slices", file=sys.stderr)

    # 翻译并边写入
    with out_path.open("w", encoding="utf-8") as output_file:
        total_slices = len(slices)
        for i, slice_info in enumerate(slices):
            # Report progress BEFORE translating the slice
            progress = int(i * 100 / total_slices) if total_slices > 0 else 0
            progress_msg = f"Translating: {progress}% complete ({i}/{total_slices} slices)"
            print(progress_msg, file=sys.stderr)
            
            try:
                if slice_info['type'] == 'empty':
                    process_empty_group(output_file)
                elif slice_info['type'] == 'long_paragraph_slice':
                    # 长段落切片直接翻译
                    translated, _ = translate_segment(slice_info['content'])
                    output_file.write(translated.strip() + "\n\n")
                elif slice_info['type'] == 'normal':
                    process_normal_group(slice_info['content'], output_file)
            except OllamaClientError as e:
                print(f"\n[ERROR] Failed to translate slice: {e}", file=sys.stderr)
                print(f"Slice content: {slice_info['content'][:100]}...", file=sys.stderr)
                sys.exit(1)
        
        # Report final progress (100%)
        if total_slices > 0:
            progress_msg = f"Translating: 100% complete ({total_slices}/{total_slices} slices)"
            print(progress_msg, file=sys.stderr)




if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
translate_with_ollama.py
将英文 txt / md 文本按句子边界切成约1024 token 的片段，
调用本地 ollama (http://localhost:11434) 翻译为中文后合并输出。
"""

import argparse
import os
import sys
import time
import subprocess
import json
from pathlib import Path

import requests
from tqdm import tqdm

# 导入文字切片处理模块
from text_slicer import TextSlicer, count_tokens, join_paragraphs_with_separator, split_by_separator

def load_settings():
    """
    加载配置文件 settings.json
    返回配置字典，如果文件不存在则使用默认配置
    """
    settings_path = Path(__file__).parent / "settings.json"
    if settings_path.exists():
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"警告: 无法读取配置文件 {settings_path}: {e}", file=sys.stderr)
            print("使用默认配置", file=sys.stderr)
    
    # 默认配置
    return {
        "ollama": {
            "url": "http://localhost:11434/api/generate",
            "model_name": "gemma3:latest",
            "temperature": 0.1,
            "top_p": 0.9,
            "repeat_penalty": 1.2,
            "timeout": 240,
            "retries": 3
        },
        "translation": {
            "target_tokens_per_slice": 1024,
            "target_language": "simplified Chinese",
            "system_prompt": "You are a professional translator. Translate the following text into natural, fluent {target_language} if it's not already in {target_language}. DO NOT translate or remove any formating tags, such as HTML/markdown/latex tags. DO NOT translate people names, acronyms, equations, hyperlinks, or references. Return ONLY the {target_language} translation, do not include any thinking/reasoning, explanation or note.",
            "para_sep": "<段落分隔符>"
        }
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

# ------------------------------------------------------------------ #
# 重启 ollama（未启用，保留作参考）
"""
def restart_ollama():
      subprocess.run('ollama stop', shell=True)
      time.sleep(2)
      subprocess.Popen('start /B ollama serve', shell=True)
      time.sleep(10)  # 等待服务启动
"""

# 调用 ollama 进行翻译
def translate_segment(segment: str, retries: int = None) -> tuple[str, list]:
    """
    调用本地 Ollama API 翻译指定文本片段。
    参数：
        segment: 需要翻译的英文文本片段
        retries: 失败重试次数，如果为None则使用配置文件中的值
    返回：
        (翻译后的中文文本, 上下文信息)
    """
    if retries is None:
        retries = SETTINGS["ollama"]["retries"]
    
    payload = {
        "model": SETTINGS["ollama"]["model_name"],
        "system": get_system_prompt(),
        "prompt": segment,
        "stream": False,
        "options": {
            "temperature": SETTINGS["ollama"]["temperature"], 
            "top_p": SETTINGS["ollama"]["top_p"], 
            "repeat_penalty": SETTINGS["ollama"]["repeat_penalty"]
        },
    }

    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(SETTINGS["ollama"]["url"], json=payload, timeout=SETTINGS["ollama"]["timeout"])
            resp.raise_for_status()
            json_resp = resp.json()
            return json_resp["response"].strip(), json_resp.get("context", [])
        except Exception as e:
            print(f"[WARN] attempt {attempt} failed: {e}", file=sys.stderr)
            if attempt == retries:
                raise
            time.sleep(2 ** attempt)
    return "", []

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
    2. 使用TextSlicer进行文本切片处理。
    3. 逐组翻译并写入输出文件。
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="英文 txt/html/md 文件路径")
    args = parser.parse_args()

    src_path = Path(args.input_file).expanduser().resolve()
    if not src_path.exists():
        sys.exit(f"文件不存在: {src_path}")

    out_path = src_path.with_stem(src_path.stem + "-chn")

    # 读取原文
    text = src_path.read_text(encoding="utf-8")

    # 创建文本切片器
    slicer = TextSlicer(
        target_tokens=SETTINGS["translation"]["target_tokens_per_slice"],
        para_separator=SETTINGS["translation"]["para_sep"]
    )
    
    # 处理文本切片
    slices = slicer.process_text(text)
    print(f"共生成 {len(slices)} 个切片")

    # 翻译并边写入
    with out_path.open("w", encoding="utf-8") as output_file:
        for slice_info in tqdm(slices, desc="Translating", unit="slice"):
            if slice_info['type'] == 'empty':
                process_empty_group(output_file)
            elif slice_info['type'] == 'long_paragraph_slice':
                # 长段落切片直接翻译
                translated, _ = translate_segment(slice_info['content'])
                output_file.write(translated.strip() + "\n\n")
            elif slice_info['type'] == 'normal':
                process_normal_group(slice_info['content'], output_file)
    print(f"翻译完成，已保存为: {out_path}")


if __name__ == "__main__":
    main()
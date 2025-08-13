#!/usr/bin/env python3
"""
translate_with_ollama.py
将英文 txt / md 文本按句子边界切成约512 token 的片段，
调用本地 ollama (http://localhost:11434) 翻译为中文后合并输出。
"""

import argparse
import os
import sys
import time
import re
import subprocess
import json
from pathlib import Path

import requests
import nltk
from nltk.tokenize import sent_tokenize
from tqdm import tqdm

# 首次运行需下载 punkt 分句模型
try:
    nltk.data.find("tokenizers/punkt")    # 检查 punkt 分句模型是否已下载
except LookupError:
    nltk.download("punkt")                 # 若未下载则自动下载

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
            "target_tokens_per_slice": 512,
            "system_prompt": "You are a professional translator. Translate the following English text into natural, fluent simplified Chinese. DO NOT translate or remove any formating tags, such as HTML/markdown/latex tags. DO NOT translate people names, acronyms, equations, hyperlinks, or references. Return ONLY the Chinese translation, do not include any thinking/reasoning, explanation or note.",
            "para_sep": "<段落分隔符>"
        }
    }

# 加载配置
SETTINGS = load_settings()

# ------------------------------------------------------------------ #
# 工具：粗略估算 token 数（对英文文本足够）
def count_tokens(text: str) -> int:
    """
    粗略估算文本的 token 数。
    以 utf-8 编码后每 4 字节算作 1 token。
    适用于英文文本的近似估算。
    """
    return len(text.encode("utf-8")) // 4


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
        "system": SETTINGS["translation"]["system_prompt"],
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


# ------------------------------------------------------------------ #
# 新的分段合并切片逻辑

def group_paragraphs(paragraphs, max_tokens=None):
    """
    合并多个短段为一组，长段单独为一组，返回 [[para1, para2, ...], ...]
    参数：
        paragraphs: 段落列表
        max_tokens: 每组最大 token 数，如果为None则使用配置文件中的值
    返回：
        分组后的段落列表，每组为一个 list
    """
    if max_tokens is None:
        max_tokens = SETTINGS["translation"]["target_tokens_per_slice"]
    
    groups = []
    current = []
    current_len = 0
    for para in paragraphs:
        para = para.strip()
        if not para:
            # 空段落直接单独成组
            if current:
                groups.append(current)
                current = []
                current_len = 0
            groups.append([""])
            continue
        para_len = count_tokens(para)
        if para_len > max_tokens:
            # 长段落单独成组
            if current:
                groups.append(current)
                current = []
                current_len = 0
            groups.append([para])
            continue
        if current_len + para_len > max_tokens and current:
            groups.append(current)
            current = []
            current_len = 0
        current.append(para)
        current_len += para_len
    if current:
        groups.append(current)
    return groups

def process_empty_group(output_file):
    """
    处理空段落组，直接写入两个换行符。
    """
    output_file.write("\n\n")

def process_long_paragraph(group, output_file):
    """
    处理超长段落：按句子切片，每片不超过目标 token 数，分别翻译后合并。
    参数：
        group: 仅含一个长段落的列表
        output_file: 输出文件对象
    """
    para = group[0]
    target_tokens = SETTINGS["translation"]["target_tokens_per_slice"]
    # 按句切片
    sentences = sent_tokenize(para)
    slices = []
    current = []
    current_len = 0
    for sent in sentences:
        sent_len = count_tokens(sent)
        if sent_len > target_tokens:
            # 超长句单独成片
            if current:
                slices.append(" ".join(current))
                current = []
                current_len = 0
            slices.append(sent)
            continue
        if current_len + sent_len > target_tokens and current:
            slices.append(" ".join(current))
            current = []
            current_len = 0
        current.append(sent)
        current_len += sent_len
    if current:
        slices.append(" ".join(current))
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
    joined = f"\n{para_sep}\n".join(group)
    translated, _ = translate_segment(joined)
    # 按分隔符拆分
    translated_paragraphs = [p.strip() for p in translated.split(para_sep)]
    for para in translated_paragraphs:
        output_file.write(para + "\n\n")

def main():
    """
    主程序入口：
    1. 解析命令行参数，读取输入文件。
    2. 按段落分割并分组。
    3. 逐组翻译并写入输出文件。
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="英文 txt / md 文件路径")
    args = parser.parse_args()

    src_path = Path(args.input_file).expanduser().resolve()
    if not src_path.exists():
        sys.exit(f"文件不存在: {src_path}")

    out_path = src_path.with_stem(src_path.stem + "-chn")

    # 读取原文
    text = src_path.read_text(encoding="utf-8")

    # 按段落分割
    paragraphs = re.split(r'\n\s*\n', text)
    groups = group_paragraphs(paragraphs)
    print(f"共分组 {len(groups)} 组")

    # 翻译并边写入
    with out_path.open("w", encoding="utf-8") as output_file:
        for group in tqdm(groups, desc="Translating", unit="group"):
            if all(not para.strip() for para in group):
                process_empty_group(output_file)
                continue
            if len(group) == 1 and count_tokens(group[0]) > SETTINGS["translation"]["target_tokens_per_slice"]:
                process_long_paragraph(group, output_file)
                continue
            process_normal_group(group, output_file)
    print(f"翻译完成，已保存为: {out_path}")


if __name__ == "__main__":
    main()
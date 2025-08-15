#!/usr/bin/env python3
"""
text_slicer.py
文字切片处理模块，负责将文本按段落和句子进行智能切片，
确保每个切片在指定的token数量范围内。
"""

import re
import nltk
from nltk.tokenize import sent_tokenize
from typing import List, Tuple

# 首次运行需下载 punkt 分句模型
try:
    nltk.data.find("tokenizers/punkt")    # 检查 punkt 分句模型是否已下载
except LookupError:
    nltk.download("punkt")                 # 若未下载则自动下载


def count_tokens(text: str) -> int:
    """
    粗略估算文本的 token 数。
    以 utf-8 编码后每 4 字节算作 1 token。
    适用于英文文本的近似估算。
    
    参数：
        text: 要估算token数的文本
    返回：
        估算的token数量
    """
    return len(text.encode("utf-8")) // 4


def split_into_paragraphs(text: str) -> List[str]:
    """
    将文本按段落分割。
    
    参数：
        text: 原始文本
    返回：
        段落列表
    """
    return re.split(r'\n\s*\n', text)


def group_paragraphs(paragraphs: List[str], max_tokens: int) -> List[List[str]]:
    """
    合并多个短段为一组，长段单独为一组，返回 [[para1, para2, ...], ...]
    
    参数：
        paragraphs: 段落列表
        max_tokens: 每组最大 token 数
    返回：
        分组后的段落列表，每组为一个 list
    """
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


def slice_long_paragraph(paragraph: str, target_tokens: int) -> List[str]:
    """
    将长段落按句子切片，每片不超过目标 token 数。
    
    参数：
        paragraph: 长段落文本
        target_tokens: 目标token数量
    返回：
        切片后的文本片段列表
    """
    # 按句切片
    sentences = sent_tokenize(paragraph)
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
        
    return slices


def is_empty_group(group: List[str]) -> bool:
    """
    判断段落组是否为空（所有段落都是空白）。
    
    参数：
        group: 段落组
    返回：
        是否为空组
    """
    return all(not para.strip() for para in group)


def is_long_paragraph_group(group: List[str], max_tokens: int) -> bool:
    """
    判断段落组是否为长段落组（只有一个段落且超过最大token数）。
    
    参数：
        group: 段落组
        max_tokens: 最大token数
    返回：
        是否为长段落组
    """
    return len(group) == 1 and count_tokens(group[0]) > max_tokens


def join_paragraphs_with_separator(paragraphs: List[str], separator: str) -> str:
    """
    使用分隔符连接多个段落。
    
    参数：
        paragraphs: 段落列表
        separator: 分隔符
    返回：
        连接后的文本
    """
    return f"\n{separator}\n".join(paragraphs)


def split_by_separator(text: str, separator: str) -> List[str]:
    """
    按分隔符拆分文本。
    
    参数：
        text: 要拆分的文本
        separator: 分隔符
    返回：
        拆分后的段落列表
    """
    return [p.strip() for p in text.split(separator)]


class TextSlicer:
    """
    文本切片器类，提供完整的文本切片功能。
    """
    
    def __init__(self, target_tokens: int = 1024, para_separator: str = "<段落分隔符>"):
        """
        初始化文本切片器。
        
        参数：
            target_tokens: 目标token数量
            para_separator: 段落分隔符
        """
        self.target_tokens = target_tokens
        self.para_separator = para_separator
    
    def process_text(self, text: str) -> List[dict]:
        """
        处理文本，返回切片信息。
        
        参数：
            text: 原始文本
        返回：
            切片信息列表，每个元素包含：
            - type: 切片类型 ('empty', 'long_paragraph', 'normal')
            - content: 切片内容
            - needs_translation: 是否需要翻译
        """
        # 按段落分割
        paragraphs = split_into_paragraphs(text)
        
        # 分组
        groups = group_paragraphs(paragraphs, self.target_tokens)
        
        slices = []
        for group in groups:
            if is_empty_group(group):
                slices.append({
                    'type': 'empty',
                    'content': group,
                    'needs_translation': False
                })
            elif is_long_paragraph_group(group, self.target_tokens):
                # 长段落需要进一步切片
                long_para_slices = slice_long_paragraph(group[0], self.target_tokens)
                for slice_content in long_para_slices:
                    slices.append({
                        'type': 'long_paragraph_slice',
                        'content': slice_content,
                        'needs_translation': True
                    })
            else:
                # 普通段落组
                slices.append({
                    'type': 'normal',
                    'content': group,
                    'needs_translation': True
                })
        
        return slices

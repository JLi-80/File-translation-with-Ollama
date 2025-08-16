# Ollama 翻译器

这是一个使用本地 Ollama 模型将文本翻译为指定语言的工具。

## 配置文件

程序使用 `settings.json` 文件来管理配置参数，用户可以在不修改源代码的情况下灵活调整设置。

### 配置文件结构

```json
{
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
        "target_language": "simplified Chinese",
        "system_prompt": "You are a professional translator. Translate the following text into natural, fluent {target_language} if it's not already in {target_language}. DO NOT translate or remove any formating tags, such as HTML/markdown/latex tags. DO NOT translate people names, acronyms, equations, hyperlinks, or references. Return ONLY the {target_language} translation, do not include any thinking/reasoning, explanation or note.",
        "para_sep": "<段落分隔符>"
    }
}
```

### 配置参数说明

#### Ollama 设置
- `url`: Ollama API 地址
- `model_name`: 使用的模型名称
- `temperature`: 生成温度，控制输出的随机性 (0.0-1.0)
- `top_p`: 核采样参数 (0.0-1.0)
- `repeat_penalty`: 重复惩罚参数
- `timeout`: 请求超时时间（秒）
- `retries`: 翻译失败重试次数

#### 翻译设置
- `target_tokens_per_slice`: 每个分片的目标最大 token 数。过大的token数导致更大的运算开销，并可能导致每分片返回翻译结果不完整；更小的token数可能导致翻译结果碎片化。
- `target_language`: **翻译目标语言**。用户可以通过修改此参数来指定翻译的目标语言，例如：
  - `"simplified Chinese"` - 简体中文（默认）
  - `"English"` - 英文
  - `"Japanese"` - 日文
  - `"Korean"` - 韩文
  - `"French"` - 法文
  - `"German"` - 德文
  - 等等...
- `system_prompt`: 翻译系统提示词。支持使用 `{target_language}` 占位符，程序会自动将其替换为实际的目标语言。
- `para_sep`: 段落分隔符，用于在翻译时保持段落结构

### 使用方法

1. 确保 Ollama 服务正在运行
2. 根据需要修改 `settings.json` 文件中的参数
3. 运行翻译程序：
   ```bash
   python translate_with_ollama.py input.txt
   ```

## 支持的输入文件类型

程序按 UTF-8 文本整体读取，不做扩展名硬限制。常见可直接处理（推荐）的纯文本与轻量标记格式：

- 文本与轻量标记
  - txt
  - html / htm / xhtml
  - md / markdown
  - rst（reStructuredText）
  - tex / latex
  - adoc（AsciiDoc）
  - xml（如 DocBook、XHTML 等）
- 字幕
  - srt / vtt（按段落块处理并保持块顺序）

可用但需谨慎（可能破坏结构或键名/值）：csv / tsv、yaml / yml、ini / conf / properties、json  
不支持：doc / docx / pdf 等二进制文档（请先导出为纯文本或 Markdown）

### 多语言翻译示例

要翻译为不同语言，只需修改 `settings.json` 中的 `target_language` 参数：

**翻译为英文：**
```json
{
    "translation": {
        "target_language": "English",
        // ... 其他设置
    }
}
```

**翻译为日文：**
```json
{
    "translation": {
        "target_language": "Japanese",
        // ... 其他设置
    }
}
```

**翻译为法文：**
```json
{
    "translation": {
        "target_language": "French",
        // ... 其他设置
    }
}
```

### 注意事项

- 如果 `settings.json` 文件不存在或读取失败，程序将使用默认配置
- 修改配置文件后无需重启程序，每次运行都会重新加载配置
- 建议根据使用的模型调整 `temperature` 和 `top_p` 参数以获得最佳翻译效果
- `target_language` 参数会影响 `system_prompt` 中的占位符替换，确保翻译指令与目标语言一致
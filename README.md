# Ollama 翻译器

这是一个使用本地 Ollama 模型将文本翻译为指定语言的工具。支持多种语言之间的翻译。

## 项目结构

```
ollama_translator/
├── translate_with_ollama.py  # 主程序入口
├── ollama_client.py          # Ollama API客户端模块
├── text_slicer.py            # 文本切片处理模块
├── test_ollama_client.py     # 客户端模块测试脚本
├── example_usage.py          # 使用示例脚本
├── settings.json             # 配置文件
├── REFACTORING_SUMMARY.md    # 重构总结文档
└── README.md                 # 项目说明文档
```

### 模块说明

- **`translate_with_ollama.py`**: 主程序，负责文件处理、文本切片和翻译流程控制
- **`ollama_client.py`**: 独立的Ollama API客户端模块，负责与Ollama服务的通讯交互和异常处理
- **`text_slicer.py`**: 文本切片处理模块，负责将长文本分割为适合翻译的片段
- **`test_ollama_client.py`**: 测试脚本，用于验证Ollama客户端模块的功能
- **`example_usage.py`**: 使用示例脚本，展示如何使用Ollama客户端模块
- **`REFACTORING_SUMMARY.md`**: 重构总结文档，记录了项目的重构过程和架构改进详情

## 配置文件

程序使用 `settings.json` 文件来管理配置参数，用户可以在不修改源代码的情况下灵活调整设置。如果配置文件不存在或读取失败，程序将使用内置的默认配置。配置文件采用JSON格式，结构清晰，易于理解和修改。用户可以根据不同的使用场景创建多个配置文件，或者通过环境变量覆盖特定配置。配置文件支持注释和格式化，便于维护。配置文件的修改会立即生效，无需重启程序。配置文件的结构经过精心设计，确保参数之间的逻辑关系清晰。所有配置参数都有合理的默认值，确保程序能够正常运行。

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
        "target_tokens_per_slice": 1024,
        "target_language": "simplified Chinese",
        "system_prompt": "You are a professional translator. Translate the following text into natural, fluent {target_language} if it's not already in {target_language}. DO NOT translate or remove any formating tags, including HTML/markdown/latex tags such as <table>, <figure>, <equation>, <reference>, etc. DO NOT translate people names, acronyms, equations, hyperlinks, or references. Return ONLY the {target_language} translation, do not include any thinking/reasoning, explanation or note.",
        "para_sep": "<段落分隔符>"
    },
    "general": {
        "skip_connection_test": false
    }
}
```

### 配置参数说明

配置参数分为三个部分：Ollama设置、翻译设置和通用设置。每个部分都有其特定的功能和参数，用户可以根据需要调整相应的配置。所有参数都有合理的默认值，用户可以根据实际需求进行自定义。配置文件的修改会立即生效，无需重启程序。建议在修改配置前备份原始配置文件。参数调整会影响翻译质量和性能。建议根据实际使用情况优化参数设置。每个参数都有详细的说明和推荐值。参数之间的关系经过精心设计，确保配置的合理性。

#### Ollama 设置
- `url`: Ollama API 地址（默认：http://localhost:11434/api/generate）
- `model_name`: 使用的模型名称（默认：gemma3:latest，当前配置文件中使用：qwen3:4b-instruct-2507-q8_0）
- `temperature`: 生成温度，控制输出的随机性 (0.0-1.0，默认0.1)
- `top_p`: 核采样参数 (0.0-1.0，默认0.9)
- `repeat_penalty`: 重复惩罚参数（默认1.2）
- `timeout`: 请求超时时间（秒，默认240）
- `retries`: 翻译失败重试次数（默认3）

#### 通用设置
- `skip_connection_test`: 是否跳过启动时的Ollama连接测试（默认：false）。设置为true可以跳过连接测试，适用于已知Ollama服务正在运行的情况。

#### 翻译设置
- `target_tokens_per_slice`: 每个分片的目标最大 token 数（默认1024）。过大的token数导致更大的运算开销，并可能导致每分片返回翻译结果不完整；更小的token数可能导致翻译结果碎片化。建议根据使用的模型和文本特点调整此参数。
- `target_language`: **翻译目标语言**。用户可以通过修改此参数来指定翻译的目标语言，例如：
  - `"simplified Chinese"` - 简体中文（默认）
  - `"English"` - 英文
  - `"Japanese"` - 日文
  - `"Korean"` - 韩文
  - `"French"` - 法文
  - `"German"` - 德文
  - `"Spanish"` - 西班牙文
  - `"Italian"` - 意大利文
  - `"Portuguese"` - 葡萄牙文
  - `"Russian"` - 俄文
  - 等等...
- `system_prompt`: 翻译系统提示词。支持使用 `{target_language}` 占位符，程序会自动将其替换为实际的目标语言。提示词会指导模型保持格式标签、不翻译人名、缩写、公式、超链接等。
- `para_sep`: 段落分隔符，用于在翻译时保持段落结构（默认：`<段落分隔符>`）

### 依赖要求

项目依赖以下Python包：
- `requests`: HTTP请求库
- `tqdm`: 进度条显示
- `nltk`: 自然语言处理工具包（用于文本分句）

安装依赖：
```bash
pip install requests tqdm nltk
```

## 使用方法

### 基本使用

1. 确保 Ollama 服务正在运行
2. 根据需要修改 `settings.json` 文件中的参数
3. 运行翻译程序：
   ```bash
   python translate_with_ollama.py input.txt
   ```

翻译完成后，程序会在原文件同目录下生成 `{原文件名}-translated.{原扩展名}` 的输出文件。

**示例：**
```bash
# 翻译英文文档
python translate_with_ollama.py document.txt

# 翻译Markdown文件
python translate_with_ollama.py README.md

# 翻译HTML文件
python translate_with_ollama.py webpage.html

# 翻译字幕文件
python translate_with_ollama.py subtitle.srt

# 翻译LaTeX文档
python translate_with_ollama.py paper.tex

# 翻译AsciiDoc文档
python translate_with_ollama.py manual.adoc

# 翻译reStructuredText文档
python translate_with_ollama.py docs.rst

# 翻译XML文档
python translate_with_ollama.py config.xml

# 翻译YAML配置文件
python translate_with_ollama.py config.yaml
```

#### 连接测试控制

程序默认会在启动时测试Ollama连接。可以通过修改 `settings.json` 中的 `general.skip_connection_test` 参数来控制是否跳过连接测试：

```json
{
    "general": {
        "skip_connection_test": true
    }
}
```

如果连接测试失败，程序会提示错误并退出。确保Ollama服务正在运行且可访问。如果确定服务正在运行，可以设置 `skip_connection_test` 为 `true` 跳过连接测试。连接测试会验证Ollama服务的可用性和模型的可访问性。建议在首次使用或更换模型后运行连接测试。连接测试失败时，请检查Ollama服务状态和网络连接。连接测试成功后会显示"Ollama连接测试通过"的提示。连接测试是确保翻译过程顺利进行的重要步骤。连接测试会检查Ollama服务的响应时间和模型的可访问性。

#### 测试客户端模块

运行测试脚本验证Ollama客户端模块功能：
```bash
python test_ollama_client.py
```

测试脚本包含：
- 配置加载测试
- 客户端创建测试
- 异常类测试
- 连接测试功能验证

测试结果会显示每个测试项的通过状态。如果所有测试都通过，会显示"🎉 所有测试通过！"的提示。测试脚本可以帮助用户验证Ollama客户端模块的功能是否正常。建议在安装或更新后运行测试脚本。如果测试失败，请检查依赖包是否正确安装。测试脚本会验证配置加载、客户端创建、异常处理等功能。测试脚本是确保系统正常运行的重要工具。测试脚本会检查所有关键功能模块。

#### 查看使用示例

运行示例脚本查看如何使用Ollama客户端模块：
```bash
python example_usage.py
```

示例脚本包含：
- 基本使用示例：展示如何加载配置、创建客户端、进行翻译
- 自定义配置示例：展示如何使用自定义配置参数
- 错误处理示例：展示如何处理连接错误和异常情况

运行示例脚本可以快速了解如何使用Ollama客户端模块的各种功能。示例脚本提供了完整的使用场景，可以作为开发参考。建议新用户先运行示例脚本了解基本用法。示例脚本中的代码可以直接复制和修改使用。示例脚本会展示如何创建客户端、进行翻译、处理错误等操作。示例脚本是学习和理解系统功能的最佳方式。示例脚本包含了实际的使用场景和最佳实践。

## 支持的输入文件类型

程序按 UTF-8 文本整体读取，不做扩展名硬限制。支持多种文本格式，但建议使用纯文本或轻量标记格式以获得最佳翻译效果。程序会保持原始文件的格式结构，确保翻译后的文件格式与原文一致。对于结构化文档，程序会尽量保持原有的格式和结构。翻译过程中会保持段落分隔和文本层次。程序会自动识别和处理不同的文件格式。支持的文件类型包括但不限于（按推荐程度排序）：

- 文本与轻量标记
  - txt
  - html / htm / xhtml
  - md / markdown
  - rst（reStructuredText）
  - tex / latex
  - adoc（AsciiDoc）
  - xml（如 DocBook、XHTML 等）
- 字幕
  - srt / vtt（字幕，保持段落块顺序）

可用但需谨慎（可能破坏结构或键名）：csv / tsv、yaml / yml、ini / conf / properties、json  
不支持：doc / docx / pdf 等二进制文档（请先导出为纯文本或 Markdown）

### 多语言翻译示例

要翻译为不同语言，只需修改 `settings.json` 中的 `target_language` 参数。程序会自动将系统提示词中的 `{target_language}` 占位符替换为实际的目标语言。支持的语言包括但不限于（具体支持的语言取决于使用的模型）。建议使用标准的语言名称，如"English"、"Chinese"、"Japanese"等。翻译质量会因模型和语言组合而异。不同的模型对不同语言的支持程度可能不同。建议根据目标语言选择合适的模型。翻译质量也会受到原文质量和复杂度的影响：

**翻译为英文：**
```json
{
    "translation": {
        "target_language": "English"
    }
}
```

**翻译为日文：**
```json
{
    "translation": {
        "target_language": "Japanese"
    }
}
```

**翻译为法文：**
```json
{
    "translation": {
        "target_language": "French"
    }
}
```

**翻译为德文：**
```json
{
    "translation": {
        "target_language": "German"
    }
}
```

### 注意事项

- 如果 `settings.json` 文件不存在或读取失败，程序将使用默认配置
- 修改配置文件后无需重启程序，每次运行都会重新加载配置
- 建议根据使用的模型调整 `temperature` 和 `top_p` 参数以获得最佳翻译效果
- `target_language` 参数会影响 `system_prompt` 中的占位符替换，确保翻译指令与目标语言一致
- 首次运行时会自动下载nltk的punkt分句模型，需要网络连接
- 翻译过程中会显示进度条，显示当前翻译进度
- 如果翻译过程中出现错误，程序会显示错误信息并退出
- 程序会自动处理长文本的切片，确保每个切片在指定的token数量范围内
- 翻译过程中会保持段落的完整性，避免翻译结果的碎片化
- 程序会自动处理空段落和特殊格式，确保输出文件的格式正确
- 翻译质量取决于使用的模型，建议选择适合翻译任务的模型
- 程序支持批量处理，可以连续翻译多个文件
- 翻译过程中会显示详细的进度信息，包括当前处理的切片和总体进度
- 程序会自动处理各种异常情况，提供清晰的错误提示和恢复建议
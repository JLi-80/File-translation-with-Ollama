# Ollama 翻译器

这是一个使用本地 Ollama 模型将英文文本翻译为中文的工具。

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
        "system_prompt": "You are a professional translator...",
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
- `target_tokens_per_slice`: 每个分片的目标最大 token 数
- `system_prompt`: 翻译系统提示词
- `para_sep`: 段落分隔符，用于在翻译时保持段落结构

### 使用方法

1. 确保 Ollama 服务正在运行
2. 根据需要修改 `settings.json` 文件中的参数
3. 运行翻译程序：
   ```bash
   python translate_with_ollama.py input.txt
   ```

### 注意事项

- 如果 `settings.json` 文件不存在或读取失败，程序将使用默认配置
- 修改配置文件后无需重启程序，每次运行都会重新加载配置
- 建议根据使用的模型调整 `temperature` 和 `top_p` 参数以获得最佳翻译效果 
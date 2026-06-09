# Developer Handoff: Gemma 4 12B Unified (MLX Implementation)

## Overview
This document details the environment setup and architectural "gotchas" for running the **Gemma 4 12B Unified** model locally using Apple's MLX framework.

**Model ID:** `mlx-community/gemma-4-12B-it-OptiQ-4bit`
**Architecture:** `gemma4_unified` (Encoder-free Multimodal Decoder)

---

## 1. Environment Setup
The model requires the latest MLX primitives. A virtual environment is highly recommended to isolate the source-patched version of `mlx-lm`.

```bash
# Initialize Environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# Install latest MLX stack
pip install -U mlx-lm mlx-vlm
```

---

## 2. Critical Troubleshooting: The `gemma4_unified` Patch
As of early June 2026, the PyPI release of `mlx-lm` may recognize the `gemma4` family but fail to map the `gemma4_unified` alias found in the Hugging Face `config.json`.

**The Error:** `ValueError: Model type gemma4_unified not supported.`

### The Fix:
You must manually add the mapping to the `MODEL_REMAPPING` dictionary in your site-packages.

**File:** `venv/lib/python3.13/site-packages/mlx_lm/utils.py`
**Change:**
```python
# Around line 90
MODEL_REMAPPING = {
    ...
    "iquestcoder": "llama",
    "gemma4_unified": "gemma4", # <--- Add this line
}
```

---

## 3. Implementation Details

### Chat Templates & Control Tokens
Gemma 4 12B uses a specific set of control tokens for its "Thinking" and "Channel" features. **Do not use raw string prompts.** Use the `apply_chat_template` method to ensure the model enters the correct state.

### Thinking Mode (Chain-of-Thought)
This model is trained with an explicit internal reasoning channel.
- **Behavior:** The model will output `<|channel>thought` followed by its reasoning before the final answer.
- **Requirement:** Ensure `max_tokens` is set high enough (e.g., `2000+`) as the reasoning phase can consume several hundred tokens before the actual response begins.

### Performance Benchmarks (Mac Studio M2 Ultra/M3 Max)
- **Peak Memory:** ~9.31 GB
- **Prompt Processing:** ~110 tokens/sec
- **Generation Speed:** ~25 tokens/sec

---

## 4. Sample Boilerplate
```python
from mlx_lm import load, generate

# Load with the patched mapping
model, tokenizer = load("mlx-community/gemma-4-12B-it-OptiQ-4bit")

messages = [{"role": "user", "content": "Your technical prompt here"}]
prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

# Generate with verbose=True to stream the thought channel
response = generate(
    model, tokenizer,
    prompt=prompt,
    max_tokens=2000,
    verbose=True
)
```

---

## 5. Future-Proofing
- **Multimodal:** To utilize the vision/audio capabilities of this unified architecture, transition from `mlx-lm` to `mlx-vlm` once the unified loader is fully stabilized in the VLM package.
- **Quantization:** The `OptiQ` variant uses Per-Layer Embeddings (PLE). If converting your own weights, ensure you are using `mlx-lm >= 0.31.0` to avoid PLE table corruption.

from mlx_lm import load, generate

model, tokenizer = load("mlx-community/gemma-4-12B-it-OptiQ-4bit")

messages = [{"role": "user", "content": "Explain quantum information theory and why it is important to understand in simple terms."}]
prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

response = generate(
    model, tokenizer,
    prompt=prompt,
    max_tokens=2000,
    verbose=True,
)

from dataclasses import dataclass, field

@dataclass
class SentinelConfig:
    protected_paths: list[str] = field(default_factory=list)
    auto_approve_paths: list[str] = field(default_factory=list)
    model_id: str = "mlx-community/gemma-4-12B-it-OptiQ-4bit"

c = SentinelConfig(protected_paths=None)
print(f"protected_paths: {c.protected_paths}")
try:
    for p in c.protected_paths:
        print(p)
except TypeError as e:
    print(f"Error iterating: {e}")

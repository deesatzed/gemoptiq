from dataclasses import dataclass, field
from pathlib import Path
import yaml

@dataclass
class SentinelConfig:
    protected_paths: list[str] = field(default_factory=list)
    auto_approve_paths: list[str] = field(default_factory=list)
    model_id: str = "mlx-community/gemma-4-12B-it-OptiQ-4bit"

def load_config(path_str: str) -> SentinelConfig:
    path = Path(path_str)
    if not path.exists():
        return SentinelConfig()
    
    try:
        with path.open('r') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError:
        return SentinelConfig()
    
    if not isinstance(data, dict):
        return SentinelConfig()
        
    # Expand home directory for path lists
    for key in ['protected_paths', 'auto_approve_paths']:
        if key in data and isinstance(data[key], list):
            data[key] = [
                str(Path(p).expanduser()) if isinstance(p, str) else p 
                for p in data[key]
            ]
    
    # Filter config to only include valid SentinelConfig fields
    valid_fields = SentinelConfig.__dataclass_fields__.keys()
    filtered_config = {
        k: v for k, v in data.items() if k in valid_fields
    }
    
    return SentinelConfig(**filtered_config)

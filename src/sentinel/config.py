from dataclasses import dataclass, field
from pathlib import Path
import yaml
import os

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
            config_dict = yaml.safe_load(f)
    except yaml.YAMLError:
        return SentinelConfig()
    
    if not isinstance(config_dict, dict):
        return SentinelConfig()
        
    # Expand home expansion for protected_paths
    if 'protected_paths' in config_dict and isinstance(config_dict['protected_paths'], list):
        config_dict['protected_paths'] = [
            os.path.expanduser(p) if isinstance(p, str) else p 
            for p in config_dict['protected_paths']
        ]
    
    # Filter config_dict to only include fields present in SentinelConfig
    valid_fields = {k for k in SentinelConfig.__dataclass_fields__}
    filtered_config = {
        k: v for k, v in config_dict.items() if k in valid_fields
    }
    
    return SentinelConfig(**filtered_config)

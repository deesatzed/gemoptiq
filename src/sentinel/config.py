from dataclasses import dataclass, field
from typing import List
import yaml
import os

@dataclass
class SentinelConfig:
    protected_paths: List[str] = field(default_factory=list)
    auto_approve_paths: List[str] = field(default_factory=list)
    model_id: str = "mlx-community/gemma-4-12B-it-OptiQ-4bit"

def load_config(path: str) -> SentinelConfig:
    if not os.path.exists(path):
        return SentinelConfig()
    
    with open(path, 'r') as f:
        config_dict = yaml.safe_load(f)
    
    if config_dict is None:
        return SentinelConfig()
        
    return SentinelConfig(
        protected_paths=config_dict.get('protected_paths', []),
        auto_approve_paths=config_dict.get('auto_approve_paths', []),
        model_id=config_dict.get('model_id', "mlx-community/gemma-4-12B-it-OptiQ-4bit")
    )

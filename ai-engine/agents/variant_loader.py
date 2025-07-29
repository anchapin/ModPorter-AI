"""
Module for loading different agent configurations based on experiment variants.
"""

from typing import Dict, Any, Optional
import json
import os
from utils.logging_config import get_agent_logger

logger = get_agent_logger("variant_loader")


class VariantLoader:
    """Loader for experiment variant configurations."""
    
    def __init__(self, base_config_path: str = "config"):
        self.base_config_path = base_config_path
        self.variant_configs = {}
    
    def load_variant_config(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """
        Load configuration for a specific experiment variant.
        
        Args:
            variant_id: The ID of the experiment variant
            
        Returns:
            Configuration dictionary for the variant, or None if not found
        """
        # Check if we've already loaded this variant
        if variant_id in self.variant_configs:
            return self.variant_configs[variant_id]
        
        # Try to load from file
        config_file = os.path.join(self.base_config_path, f"variant_{variant_id}.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                self.variant_configs[variant_id] = config
                logger.info(f"Loaded configuration for variant {variant_id}")
                return config
            except Exception as e:
                logger.error(f"Failed to load configuration for variant {variant_id}: {e}")
                return None
        
        # Try to load from environment variables
        env_config = os.getenv(f"VARIANT_{variant_id.upper()}_CONFIG")
        if env_config:
            try:
                config = json.loads(env_config)
                self.variant_configs[variant_id] = config
                logger.info(f"Loaded configuration for variant {variant_id} from environment")
                return config
            except Exception as e:
                logger.error(f"Failed to parse environment configuration for variant {variant_id}: {e}")
                return None
        
        logger.warning(f"No configuration found for variant {variant_id}")
        return None
    
    def get_agent_config(self, variant_id: str, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific agent within a variant.
        
        Args:
            variant_id: The ID of the experiment variant
            agent_name: Name of the agent to get configuration for
            
        Returns:
            Agent configuration dictionary, or None if not found
        """
        variant_config = self.load_variant_config(variant_id)
        if not variant_config:
            return None
        
        return variant_config.get("agents", {}).get(agent_name)
    
    def get_all_agent_configs(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get configurations for all agents within a variant.
        
        Args:
            variant_id: The ID of the experiment variant
            
        Returns:
            Dictionary of agent configurations, or None if variant not found
        """
        variant_config = self.load_variant_config(variant_id)
        if not variant_config:
            return None
        
        return variant_config.get("agents", {})


# Global instance
variant_loader = VariantLoader()
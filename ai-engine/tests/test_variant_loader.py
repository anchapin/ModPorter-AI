
import json
from unittest.mock import patch, mock_open
from agents.variant_loader import VariantLoader

class TestVariantLoader:
    def test_load_variant_config_from_file(self):
        loader = VariantLoader(base_config_path="/tmp")
        variant_id = "test_variant"
        config_data = {"agents": {"agent1": {"key": "value"}}}
        
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=json.dumps(config_data))):
            config = loader.load_variant_config(variant_id)
            
        assert config == config_data
        assert loader.variant_configs[variant_id] == config_data

    def test_load_variant_config_from_env(self):
        loader = VariantLoader(base_config_path="/tmp")
        variant_id = "env_variant"
        config_data = {"agents": {"agent2": {"key": "env_value"}}}
        
        with patch("os.path.exists", return_value=False), \
             patch("os.getenv", return_value=json.dumps(config_data)):
            config = loader.load_variant_config(variant_id)
            
        assert config == config_data

    def test_load_variant_config_not_found(self):
        loader = VariantLoader(base_config_path="/tmp")
        variant_id = "missing_variant"
        
        with patch("os.path.exists", return_value=False), \
             patch("os.getenv", return_value=None):
            config = loader.load_variant_config(variant_id)
            
        assert config is None

    def test_load_variant_config_path_traversal(self):
        loader = VariantLoader(base_config_path="/tmp")
        variant_id = "../evil"
        
        config = loader.load_variant_config(variant_id)
        assert config is None

    def test_get_agent_config(self):
        loader = VariantLoader(base_config_path="/tmp")
        variant_id = "test_v"
        config_data = {"agents": {"agent1": {"setting": "ok"}}}
        
        loader.variant_configs[variant_id] = config_data
        
        config = loader.get_agent_config(variant_id, "agent1")
        assert config == {"setting": "ok"}
        
        config = loader.get_agent_config(variant_id, "agent2")
        assert config is None

    def test_get_all_agent_configs(self):
        loader = VariantLoader(base_config_path="/tmp")
        variant_id = "test_v"
        config_data = {"agents": {"agent1": {"s1": 1}, "agent2": {"s2": 2}}}
        
        loader.variant_configs[variant_id] = config_data
        
        configs = loader.get_all_agent_configs(variant_id)
        assert configs == config_data["agents"]

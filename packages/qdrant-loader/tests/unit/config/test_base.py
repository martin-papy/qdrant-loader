"""Tests for the config base module."""

import pytest
from typing import Any

from qdrant_loader.config.base import (
    BaseConfig,
    BaseSourceConfig,
    ConfigProtocol,
    SourceConfigProtocol,
)


class TestConfigProtocol:
    """Test cases for ConfigProtocol."""

    def test_config_protocol_structure(self):
        """Test that ConfigProtocol defines the expected interface."""
        # Check that the protocol has the expected method
        assert hasattr(ConfigProtocol, 'to_dict')
        
        # The protocol should be a typing.Protocol
        from typing import get_origin
        assert get_origin(ConfigProtocol) is not None or hasattr(ConfigProtocol, '_is_protocol')


class TestSourceConfigProtocol:
    """Test cases for SourceConfigProtocol."""

    def test_source_config_protocol_structure(self):
        """Test that SourceConfigProtocol defines the expected interface."""
        # Check that the protocol has the expected method
        assert hasattr(SourceConfigProtocol, 'validate')
        
        # The protocol should be a typing.Protocol
        from typing import get_origin
        assert get_origin(SourceConfigProtocol) is not None or hasattr(SourceConfigProtocol, '_is_protocol')


class TestBaseConfig:
    """Test cases for BaseConfig."""

    def test_base_config_initialization(self):
        """Test BaseConfig can be initialized."""
        config = BaseConfig()
        assert config is not None

    def test_base_config_to_dict(self):
        """Test BaseConfig.to_dict() method."""
        config = BaseConfig()
        result = config.to_dict()
        
        assert isinstance(result, dict)

    def test_base_config_implements_config_protocol(self):
        """Test that BaseConfig properly implements ConfigProtocol."""
        config = BaseConfig()
        
        # Should have to_dict method
        assert hasattr(config, 'to_dict')
        assert callable(config.to_dict)
        
        # Method should return a dict
        result = config.to_dict()
        assert isinstance(result, dict)

    def test_base_config_with_data(self):
        """Test BaseConfig with custom data."""
        class TestConfig(BaseConfig):
            def __init__(self, **data):
                super().__init__(**data)
        
        config = TestConfig(test_field="test_value")
        result = config.to_dict()
        
        assert isinstance(result, dict)
        # Pydantic should include the extra field due to extra="allow"
        assert "test_field" in result
        assert result["test_field"] == "test_value"


class TestBaseSourceConfig:
    """Test cases for BaseSourceConfig."""

    def test_base_source_config_initialization(self):
        """Test BaseSourceConfig can be initialized."""
        config = BaseSourceConfig()
        assert config is not None

    def test_base_source_config_validate(self):
        """Test BaseSourceConfig.validate() method."""
        config = BaseSourceConfig()
        
        # The base validate method should not raise any exceptions
        try:
            config.validate()
        except Exception as e:
            pytest.fail(f"BaseSourceConfig.validate() raised an exception: {e}")

    def test_base_source_config_implements_protocols(self):
        """Test that BaseSourceConfig implements both protocols."""
        config = BaseSourceConfig()
        
        # Should implement ConfigProtocol (inherited from BaseConfig)
        assert hasattr(config, 'to_dict')
        assert callable(config.to_dict)
        
        # Should implement SourceConfigProtocol
        assert hasattr(config, 'validate')
        assert callable(config.validate)

    def test_base_source_config_inheritance(self):
        """Test BaseSourceConfig inheritance from BaseConfig."""
        config = BaseSourceConfig()
        
        # Should be instance of BaseConfig
        assert isinstance(config, BaseConfig)
        
        # Should have to_dict method from parent
        result = config.to_dict()
        assert isinstance(result, dict)

    def test_base_source_config_with_custom_validation(self):
        """Test BaseSourceConfig with custom validation logic."""
        class CustomSourceConfig(BaseSourceConfig):
            def __init__(self, required_field: str = None, **data):
                super().__init__(**data)
                self.required_field = required_field
            
            def validate(self) -> None:
                """Custom validation logic."""
                if not self.required_field:
                    raise ValueError("required_field is mandatory")
        
        # Test valid config
        valid_config = CustomSourceConfig(required_field="test")
        valid_config.validate()  # Should not raise
        
        # Test invalid config
        invalid_config = CustomSourceConfig()
        with pytest.raises(ValueError, match="required_field is mandatory"):
            invalid_config.validate()

    def test_base_source_config_model_config(self):
        """Test that BaseSourceConfig inherits proper model configuration."""
        config = BaseSourceConfig()
        
        # Should allow arbitrary types and extra fields (inherited from BaseConfig)
        assert hasattr(config, 'model_config')
        # model_config might be a dict or ConfigDict, so check appropriately
        if hasattr(config.model_config, 'arbitrary_types_allowed'):
            assert config.model_config.arbitrary_types_allowed is True
            assert config.model_config.extra == "allow"
        else:
            # If it's a dict, check dict keys
            assert config.model_config.get('arbitrary_types_allowed') is True
            assert config.model_config.get('extra') == "allow"
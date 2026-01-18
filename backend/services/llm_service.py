"""
Centralized LLM Service
Single source of truth for all AI/LLM operations in the platform
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import logging

from core.database import Database
from core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    Centralized service for all LLM operations.
    
    All AI features (deal confidence, field mapping, chat) must use this service
    instead of directly accessing environment variables or hardcoded configs.
    """
    
    _config_cache = None
    _cache_time = None
    _cache_ttl = 300  # 5 minutes
    
    @staticmethod
    async def get_config() -> Dict[str, Any]:
        """
        Get centralized LLM configuration from system_config.
        
        Returns:
            Dictionary with provider, api_key, models, features, etc.
        """
        # Check cache
        now = datetime.now(timezone.utc)
        if LLMService._config_cache and LLMService._cache_time:
            age = (now - LLMService._cache_time).total_seconds()
            if age < LLMService._cache_ttl:
                return LLMService._config_cache
        
        # Fetch from database
        db = Database.get_db()
        system_config = await db.system_config.find_one({}, {"_id": 0})
        
        if not system_config or not system_config.get("llm"):
            # Return defaults if not configured
            default_config = {
                "provider": "openai",
                "api_key": settings.EMERGENT_LLM_KEY or "",
                "base_url": "https://api.openai.com/v1",
                "default_model": "gpt-4",
                "models": {
                    "chat": "gpt-4-turbo",
                    "analysis": "gpt-4",
                    "embeddings": "text-embedding-3-small"
                },
                "features": {
                    "deal_confidence": {"enabled": True, "model": "gpt-4"},
                    "field_mapping": {"enabled": True, "model": "gpt-4"},
                    "chat": {"enabled": True, "model": "gpt-4-turbo"},
                    "data_quality": {"enabled": True, "model": "gpt-4"}
                }
            }
            
            logger.warning("LLM config not found in system_config, using defaults")
            return default_config
        
        llm_config = system_config["llm"]
        
        # Cache it
        LLMService._config_cache = llm_config
        LLMService._cache_time = now
        
        return llm_config
    
    @staticmethod
    async def call_llm(feature: str, prompt: str, **kwargs) -> str:
        """
        Call LLM using centralized configuration.
        
        Args:
            feature: Feature name (deal_confidence, field_mapping, chat, data_quality)
            prompt: User prompt/context
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
        
        Returns:
            LLM response text
        """
        config = await LLMService.get_config()
        
        # Check if feature is enabled
        feature_config = config.get("features", {}).get(feature, {})
        if not feature_config.get("enabled", True):
            raise ValueError(f"LLM feature '{feature}' is not enabled in system config")
        
        # Get model for this feature
        model = feature_config.get("model") or config.get("default_model", "gpt-4")
        api_key = config.get("api_key")
        provider = config.get("provider", "openai")
        
        if not api_key:
            raise ValueError("LLM API key not configured in system config")
        
        # Use emergentintegrations for LLM calls
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            chat = LlmChat(
                api_key=api_key,
                session_id=f"{feature}-{datetime.now().timestamp()}"
            ).with_model(provider, model)
            
            # Set parameters from kwargs
            if kwargs.get("temperature"):
                chat = chat.with_temperature(kwargs["temperature"])
            
            message = UserMessage(text=prompt)
            response = await chat.send_message(message)
            
            # Log usage
            await LLMService._log_usage(feature, model, len(prompt), len(response))
            
            return response
            
        except Exception as e:
            logger.error(f"LLM call failed for feature {feature}: {e}")
            raise
    
    @staticmethod
    async def _log_usage(feature: str, model: str, input_tokens: int, output_tokens: int):
        """Log LLM usage for monitoring and billing"""
        db = Database.get_db()
        
        try:
            await db.llm_usage.insert_one({
                "feature": feature,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "timestamp": datetime.now(timezone.utc)
            })
        except Exception as e:
            logger.warning(f"Failed to log LLM usage: {e}")
    
    @staticmethod
    async def update_config(updates: Dict[str, Any]) -> bool:
        """
        Update LLM configuration.
        
        Args:
            updates: Dictionary with config updates
        
        Returns:
            True if successful
        """
        db = Database.get_db()
        
        # Update system_config
        result = await db.system_config.update_one(
            {},
            {"$set": {"llm": updates}},
            upsert=True
        )
        
        # Clear cache
        LLMService._config_cache = None
        LLMService._cache_time = None
        
        logger.info(f"LLM config updated: {updates.get('provider', 'unknown')} / {updates.get('default_model', 'unknown')}")
        
        return result.modified_count > 0 or result.upserted_id is not None
    
    @staticmethod
    def clear_cache():
        """Clear configuration cache (useful for testing)"""
        LLMService._config_cache = None
        LLMService._cache_time = None

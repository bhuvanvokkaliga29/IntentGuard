"""
Unit tests for enterprise secrets management providers.
"""

import os
import pytest
from backend.security.secrets import (
    EnvSecretsProvider,
    AWSSecretsManagerProvider,
    VaultSecretsProvider,
    get_secrets_provider,
    get_secret,
)


def test_env_secrets_provider(monkeypatch):
    monkeypatch.setenv("TEST_KEY_SECRET", "super_secret_value_123")
    provider = EnvSecretsProvider()
    assert provider.provider_name == "env"
    assert provider.get_secret("TEST_KEY_SECRET") == "super_secret_value_123"
    assert provider.get_secret("NON_EXISTENT_KEY", "default_val") == "default_val"


def test_aws_secrets_manager_fallback(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fallback_gemini_key")
    provider = AWSSecretsManagerProvider()
    assert provider.provider_name == "aws_secrets_manager"
    # When AWS is unconfigured in local test, it falls back to environment
    val = provider.get_secret("GEMINI_API_KEY")
    assert val == "fallback_gemini_key"


def test_vault_secrets_fallback(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "fallback_xai_key")
    provider = VaultSecretsProvider()
    assert provider.provider_name == "hashicorp_vault"
    # When Vault is unconfigured in local test, it falls back to environment
    val = provider.get_secret("XAI_API_KEY")
    assert val == "fallback_xai_key"


def test_get_secret_helper(monkeypatch):
    monkeypatch.setenv("APP_SECRET_TOKEN", "token_xyz_99")
    val = get_secret("APP_SECRET_TOKEN")
    assert val == "token_xyz_99"

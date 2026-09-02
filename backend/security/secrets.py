"""
IntentGuard — Enterprise Secrets Management Layer

Provides a pluggable secrets provider supporting:
1. Local Environment Variables (.env / os.environ) — Default / Development
2. AWS Secrets Manager — Enterprise Cloud Deployment
3. HashiCorp Vault — Zero-Trust Infrastructure

Implements a resilient fallback hierarchy so production clusters can pull
from secure enterprise vaults with graceful local fallback.
"""

import abc
import json
import logging
import os
from typing import Dict, Optional

logger = logging.getLogger("intentguard.security.secrets")


class SecretsProvider(abc.ABC):
    """Abstract interface for enterprise secrets providers."""

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Name of the secrets provider."""
        ...

    @abc.abstractmethod
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve a secret string by key name."""
        ...


class EnvSecretsProvider(SecretsProvider):
    """Retrieves secrets from environment variables (.env / os.environ)."""

    @property
    def provider_name(self) -> str:
        return "env"

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return os.environ.get(key, default)


class AWSSecretsManagerProvider(SecretsProvider):
    """
    Retrieves secrets from AWS Secrets Manager using boto3.
    Includes in-memory caching and graceful simulated fallback if AWS credentials are unconfigured.
    """

    def __init__(
        self,
        secret_name: str = "intentguard/production/secrets",
        region_name: str = "ap-south-1",
    ):
        self._secret_name = secret_name
        self._region_name = region_name
        self._cache: Dict[str, str] = {}
        self._client = None
        self._initialized = False

    @property
    def provider_name(self) -> str:
        return "aws_secrets_manager"

    def _init_client(self):
        if self._initialized:
            return
        self._initialized = True
        try:
            import boto3
            self._client = boto3.client("secretsmanager", region_name=self._region_name)
            logger.info(f"[SECRETS] Initialized AWS Secrets Manager in {self._region_name}")
        except Exception as e:
            logger.warning(
                f"[SECRETS] AWS Secrets Manager client initialization skipped ({e}). "
                f"Operating in resilient hybrid mode."
            )
            self._client = None

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        self._init_client()
        # Check in-memory cache first
        if key in self._cache:
            return self._cache[key]

        if self._client:
            try:
                response = self._client.get_secret_value(SecretId=self._secret_name)
                if "SecretString" in response:
                    secrets_dict = json.loads(response["SecretString"])
                    self._cache.update(secrets_dict)
                    if key in self._cache:
                        return self._cache[key]
            except Exception as e:
                logger.warning(f"[SECRETS] Failed to fetch '{key}' from AWS Secrets Manager: {e}")

        # Fallback to local environment variable
        return os.environ.get(key, default)


class VaultSecretsProvider(SecretsProvider):
    """
    Retrieves secrets from HashiCorp Vault (AppRole / Token auth).
    Includes in-memory caching and graceful simulated fallback.
    """

    def __init__(
        self,
        vault_addr: Optional[str] = None,
        vault_path: str = "secret/data/intentguard",
    ):
        self._vault_addr = vault_addr or os.environ.get("VAULT_ADDR", "http://127.0.0.1:8200")
        self._vault_path = vault_path
        self._cache: Dict[str, str] = {}
        self._client = None
        self._initialized = False

    @property
    def provider_name(self) -> str:
        return "hashicorp_vault"

    def _init_client(self):
        if self._initialized:
            return
        self._initialized = True
        try:
            import hvac
            vault_token = os.environ.get("VAULT_TOKEN")
            if vault_token:
                self._client = hvac.Client(url=self._vault_addr, token=vault_token)
                logger.info(f"[SECRETS] Initialized HashiCorp Vault client at {self._vault_addr}")
        except Exception as e:
            logger.warning(
                f"[SECRETS] HashiCorp Vault client initialization skipped ({e}). "
                f"Operating in resilient hybrid mode."
            )
            self._client = None

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        self._init_client()
        if key in self._cache:
            return self._cache[key]

        if self._client and self._client.is_authenticated():
            try:
                read_response = self._client.secrets.kv.v2.read_secret_version(path=self._vault_path)
                data = read_response.get("data", {}).get("data", {})
                self._cache.update(data)
                if key in self._cache:
                    return self._cache[key]
            except Exception as e:
                logger.warning(f"[SECRETS] Failed to fetch '{key}' from HashiCorp Vault: {e}")

        # Fallback to local environment variable
        return os.environ.get(key, default)


# ── Global Secrets Manager Factory ───────────────────────────
_ACTIVE_PROVIDER: Optional[SecretsProvider] = None


def get_secrets_provider() -> SecretsProvider:
    """
    Factory function returning the configured SecretsProvider.
    Selected via SECRETS_BACKEND environment variable:
      - 'env' (default)
      - 'aws'
      - 'vault'
    """
    global _ACTIVE_PROVIDER
    if _ACTIVE_PROVIDER is not None:
        return _ACTIVE_PROVIDER

    backend_type = os.environ.get("SECRETS_BACKEND", "env").lower().strip()

    if backend_type in ("aws", "aws_secrets_manager"):
        _ACTIVE_PROVIDER = AWSSecretsManagerProvider()
    elif backend_type in ("vault", "hashicorp_vault"):
        _ACTIVE_PROVIDER = VaultSecretsProvider()
    else:
        _ACTIVE_PROVIDER = EnvSecretsProvider()

    logger.info(f"[SECRETS] Active secrets provider: {_ACTIVE_PROVIDER.provider_name}")
    return _ACTIVE_PROVIDER


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Convenience helper to retrieve a secret from the active secrets provider."""
    return get_secrets_provider().get_secret(key, default)

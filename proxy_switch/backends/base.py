"""Abstract base class for all proxy backends."""

from abc import ABC, abstractmethod
from typing import Dict, Optional


class Backend(ABC):
    """Interface that every proxy backend must implement.

    Each backend manages proxy configuration for one tool
    (e.g., git, apt, docker).
    """

    @staticmethod
    @abstractmethod
    def name() -> str:
        """Human-readable name, e.g. 'git', 'apt'."""
        ...

    @staticmethod
    @abstractmethod
    def description() -> str:
        """Short description of what this backend configures."""
        ...

    @staticmethod
    @abstractmethod
    def can_apply(executor=None) -> bool:
        """Return True if this tool is installed on the system.

        Args:
            executor: Optional SSH executor for remote checks.
                      If None, check locally.
        """
        ...

    @staticmethod
    @abstractmethod
    def needs_sudo() -> bool:
        """Return True if operations require root privileges."""
        ...

    @abstractmethod
    def enable(self, proxy_config: Dict[str, str], executor=None) -> Dict:
        """Write proxy configuration for this tool.

        Args:
            proxy_config: Dict with keys like http_proxy, https_proxy, etc.
            executor: Optional SSH executor for remote execution.
                      If None, operate locally.

        Returns:
            Dict with keys:
                success (bool): True if operation succeeded.
                message (str): Status message.
                details (str): Extra output/errors.
        """
        ...

    @abstractmethod
    def disable(self, executor=None) -> Dict:
        """Remove proxy configuration for this tool.

        Args:
            executor: Optional SSH executor for remote execution.

        Returns:
            Dict with keys: success, message, details.
        """
        ...

    @abstractmethod
    def status(self, executor=None) -> Dict:
        """Check current proxy state.

        Args:
            executor: Optional SSH executor for remote checks.

        Returns:
            Dict with keys:
                enabled (bool): Whether proxy is configured.
                proxy (str or None): The proxy URL if set.
                config_file (str or None): Path to config file.
                notes (str): Additional info.
        """
        ...

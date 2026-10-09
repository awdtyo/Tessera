"""Module interface. Every analysis is a plug-in behind this interface.

Adding a module must not require editing core code: drop a file in
tessera/modules/ implementing Module and it is auto-discovered.
"""

from abc import ABC, abstractmethod

from tessera.core.claim import Claim
from tessera.core.finding import Applicability, Finding
from tessera.core.media import Media, MediaType


class Module(ABC):
    """Plug-in contract for one forensic signal."""

    id: str
    name: str
    media_types: tuple[MediaType, ...]
    requires_network: bool = False

    @abstractmethod
    def applicable(self, media: Media, claim: Claim) -> Applicability:
        """Return whether this module applies. Must not raise on odd input."""
        raise NotImplementedError

    @abstractmethod
    def run(self, media: Media, claim: Claim) -> Finding:
        """Run the check and return a Finding. May raise (runner isolates)."""
        raise NotImplementedError

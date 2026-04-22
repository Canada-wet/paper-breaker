"""Shared base for paper-breaker tools.

beeai-framework's `Tool` ABC requires `_create_emitter`; every paper-breaker
tool wants the same implementation, so provide it once here.
"""
from __future__ import annotations

from beeai_framework.emitter import Emitter
from beeai_framework.tools import Tool as _BeeAITool


class Tool(_BeeAITool):
    """Project-wide Tool base with the default emitter already wired."""

    def _create_emitter(self) -> Emitter:
        return Emitter.root().child(namespace=["tool", self.name], creator=self)

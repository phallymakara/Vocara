"""Inference engine adapters package."""

from vocara.infrastructure.inference.base import BaseInferenceEngine
from vocara.infrastructure.inference.fake_engine import FakeInferenceEngine
from vocara.infrastructure.inference.modal_engine import ModalInferenceEngine

__all__ = [
    "BaseInferenceEngine",
    "FakeInferenceEngine",
    "ModalInferenceEngine",
]

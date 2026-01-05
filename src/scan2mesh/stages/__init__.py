"""Pipeline stages for scan2mesh.

This module provides the stage implementations for the scan2mesh pipeline.
"""

from scan2mesh.stages.capture import RGBDCapture
from scan2mesh.stages.init import ProjectInitializer
from scan2mesh.stages.optimize import AssetOptimizer
from scan2mesh.stages.package import Packager
from scan2mesh.stages.plan import CapturePlanner
from scan2mesh.stages.preprocess import Preprocessor
from scan2mesh.stages.reconstruct import Reconstructor
from scan2mesh.stages.report import QualityReporter


__all__ = [
    "AssetOptimizer",
    "CapturePlanner",
    "Packager",
    "Preprocessor",
    "ProjectInitializer",
    "QualityReporter",
    "RGBDCapture",
    "Reconstructor",
]

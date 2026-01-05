"""Quality threshold definitions.

This module defines the threshold values used by quality gates.
"""

from enum import Enum
from typing import Final


class QualityStatus(str, Enum):
    """Quality assessment status."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


# Capture quality thresholds
CAPTURE_MIN_FRAMES: Final[int] = 30
CAPTURE_MIN_COVERAGE: Final[float] = 0.8
CAPTURE_MAX_BLUR_SCORE: Final[float] = 100.0
CAPTURE_MIN_DEPTH_VALID_RATIO: Final[float] = 0.7

# Reconstruction quality thresholds
RECON_MIN_INLIER_RATIO: Final[float] = 0.6
RECON_MAX_REPROJECTION_ERROR: Final[float] = 2.0
RECON_MIN_POINTS: Final[int] = 10000

# Asset quality thresholds
ASSET_MAX_POLYGONS_LOD0: Final[int] = 100000
ASSET_MAX_POLYGONS_LOD1: Final[int] = 50000
ASSET_MAX_POLYGONS_LOD2: Final[int] = 10000
ASSET_MIN_TEXTURE_SIZE: Final[int] = 512
ASSET_MAX_TEXTURE_SIZE: Final[int] = 4096
ASSET_MAX_FILE_SIZE_MB: Final[float] = 50.0


class QualityThresholds:
    """Container for quality threshold configuration.

    Provides access to threshold values with the ability to
    customize for different use cases.
    """

    def __init__(
        self,
        capture_min_frames: int = CAPTURE_MIN_FRAMES,
        capture_min_coverage: float = CAPTURE_MIN_COVERAGE,
        capture_max_blur: float = CAPTURE_MAX_BLUR_SCORE,
        recon_min_inlier_ratio: float = RECON_MIN_INLIER_RATIO,
        recon_max_reproj_error: float = RECON_MAX_REPROJECTION_ERROR,
        asset_max_polygons: int = ASSET_MAX_POLYGONS_LOD0,
    ) -> None:
        """Initialize QualityThresholds.

        Args:
            capture_min_frames: Minimum number of captured frames
            capture_min_coverage: Minimum coverage ratio
            capture_max_blur: Maximum blur score
            recon_min_inlier_ratio: Minimum inlier ratio for pose estimation
            recon_max_reproj_error: Maximum reprojection error in pixels
            asset_max_polygons: Maximum polygon count for LOD0
        """
        self.capture_min_frames = capture_min_frames
        self.capture_min_coverage = capture_min_coverage
        self.capture_max_blur = capture_max_blur
        self.recon_min_inlier_ratio = recon_min_inlier_ratio
        self.recon_max_reproj_error = recon_max_reproj_error
        self.asset_max_polygons = asset_max_polygons

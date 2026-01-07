"""Application configuration models."""

from pydantic import BaseModel, Field


class DefaultPreset(BaseModel):
    """Default output preset configuration."""

    coordinate_system: str = "Z-up"
    units: str = "meter"
    texture_resolution: int = 2048
    lod_triangle_limits: list[int] = Field(
        default_factory=lambda: [100000, 30000, 10000]
    )


class QualityThresholds(BaseModel):
    """Quality gate thresholds."""

    depth_valid_ratio_warn: float = 0.7
    depth_valid_ratio_fail: float = 0.5
    blur_score_warn: float = 0.6
    blur_score_fail: float = 0.4
    coverage_warn: float = 0.7
    coverage_fail: float = 0.5
    min_keyframes: int = 10


class AppConfig(BaseModel):
    """Application-wide configuration."""

    profiles_dir: str = "profiles"
    projects_dir: str = "projects"
    output_dir: str = "output"
    log_level: str = "INFO"
    default_preset: DefaultPreset = Field(default_factory=DefaultPreset)
    quality_thresholds: QualityThresholds = Field(default_factory=QualityThresholds)
    language: str = "ja"

"""Frame preprocessing stage.

This module provides the Preprocessor class for preparing captured frames.
"""

from pathlib import Path

from scan2mesh.exceptions import NotImplementedStageError


class Preprocessor:
    """Preprocess captured frames for reconstruction.

    This stage handles:
    - Keyframe selection based on quality and coverage
    - Background removal and masking
    - Frame filtering and enhancement

    Attributes:
        project_dir: Path to the project directory
    """

    def __init__(self, project_dir: Path) -> None:
        """Initialize Preprocessor.

        Args:
            project_dir: Path to the project directory
        """
        self.project_dir = project_dir

    def select_keyframes(self) -> None:
        """Select optimal keyframes from captured frames.

        Raises:
            NotImplementedStageError: This stage is not yet implemented
        """
        raise NotImplementedStageError("Preprocessor.select_keyframes")

    def create_masks(self) -> None:
        """Create background masks for keyframes.

        Raises:
            NotImplementedStageError: This stage is not yet implemented
        """
        raise NotImplementedStageError("Preprocessor.create_masks")

    def preprocess(self) -> None:
        """Run full preprocessing pipeline.

        Raises:
            NotImplementedStageError: This stage is not yet implemented
        """
        raise NotImplementedStageError("Preprocessor.preprocess")

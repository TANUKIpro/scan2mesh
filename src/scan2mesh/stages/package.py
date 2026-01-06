"""Asset packaging stage.

This module provides the Packager class for creating distributable assets.
"""

import logging
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import ClassVar

from scan2mesh.models import (
    AssetManifest,
    FileReferences,
    PackageResult,
    Provenance,
    QualityStatus,
    ScaleInfo,
)
from scan2mesh.services import StorageService


logger = logging.getLogger("scan2mesh.stages.package")


class Packager:
    """Package optimized assets for distribution.

    This stage handles:
    - Asset manifest generation
    - Bundle structure creation
    - ZIP archive creation

    Attributes:
        project_dir: Path to the project directory
        storage: StorageService for file operations
    """

    # Files to include in the package
    ASSET_FILES: ClassVar[list[str]] = [
        "lod0.glb",
        "lod1.glb",
        "lod2.glb",
        "collision.glb",
        "preview.png",
    ]

    def __init__(
        self,
        project_dir: Path,
        storage: StorageService | None = None,
    ) -> None:
        """Initialize Packager.

        Args:
            project_dir: Path to the project directory
            storage: Optional StorageService instance
        """
        self.project_dir = project_dir
        self.storage = storage or StorageService(project_dir)

    def _build_provenance(self) -> Provenance:
        """Build provenance information for the manifest.

        Returns:
            Provenance object with device, tool version, date, and config hash
        """
        config = self.storage.load_project_config()

        return Provenance(
            device="RealSense",  # Default device
            tool_version="0.1.0",  # From pyproject.toml
            date=datetime.now().strftime("%Y-%m-%d"),
            config_hash=config.config_hash,
        )

    def _build_file_references(self) -> FileReferences:
        """Build file references for the manifest.

        Returns:
            FileReferences object with relative paths to asset files
        """
        return FileReferences(
            visual_lod0="lod0.glb",
            visual_lod1="lod1.glb",
            visual_lod2="lod2.glb",
            collision="collision.glb",
            preview="preview.png",
        )

    def _calculate_overall_status(self) -> QualityStatus:
        """Calculate overall quality status from all stage metrics.

        Aggregates gate_status from capture, recon, and asset stages.
        If any stage is 'fail', overall is fail.
        If any stage is 'warn', overall is warn.
        Otherwise, overall is pass.

        Returns:
            QualityStatus with overall status and reasons
        """
        reasons: list[str] = []
        has_fail = False
        has_warn = False

        # Load capture metrics if available
        try:
            capture_metrics = self.storage.load_capture_metrics()
            if capture_metrics.gate_status == "fail":
                has_fail = True
                reasons.extend(
                    [f"Capture: {r}" for r in capture_metrics.gate_reasons]
                )
            elif capture_metrics.gate_status == "warn":
                has_warn = True
                reasons.extend(
                    [f"Capture: {r}" for r in capture_metrics.gate_reasons]
                )
        except Exception:
            logger.debug("Capture metrics not available")

        # Load recon report if available
        try:
            recon_report = self.storage.load_recon_report()
            if recon_report.gate_status == "fail":
                has_fail = True
                reasons.extend([f"Recon: {r}" for r in recon_report.gate_reasons])
            elif recon_report.gate_status == "warn":
                has_warn = True
                reasons.extend([f"Recon: {r}" for r in recon_report.gate_reasons])
        except Exception:
            logger.debug("Recon report not available")

        # Load asset metrics (required)
        asset_metrics = self.storage.load_asset_metrics()
        if asset_metrics.gate_status == "fail":
            has_fail = True
            reasons.extend([f"Asset: {r}" for r in asset_metrics.gate_reasons])
        elif asset_metrics.gate_status == "warn":
            has_warn = True
            reasons.extend([f"Asset: {r}" for r in asset_metrics.gate_reasons])

        # Determine overall status
        if has_fail:
            status = "fail"
        elif has_warn:
            status = "warn"
        else:
            status = "pass"

        return QualityStatus(status=status, reasons=reasons)

    def _build_manifest(self) -> AssetManifest:
        """Build the complete asset manifest.

        Returns:
            AssetManifest with all metadata
        """
        config = self.storage.load_project_config()
        capture_metrics = self.storage.load_capture_metrics()
        recon_report = self.storage.load_recon_report()
        asset_metrics = self.storage.load_asset_metrics()

        provenance = self._build_provenance()
        file_refs = self._build_file_references()
        quality = self._calculate_overall_status()

        return AssetManifest(
            schema_version="1.0",
            object_name=config.object_name,
            class_id=config.class_id,
            tags=config.tags,
            units=config.output_preset.units,
            coordinate_system=config.output_preset.coordinate_system,
            scale=config.scale_info
            if config.scale_info
            else self._default_scale_info(),
            files=file_refs,
            quality=quality,
            provenance=provenance,
            capture_metrics=capture_metrics,
            recon_metrics=recon_report,
            asset_metrics=asset_metrics,
        )

    def _default_scale_info(self) -> ScaleInfo:
        """Create default scale info when not configured.

        Returns:
            ScaleInfo with RealSense depth scale method
        """
        return ScaleInfo(
            method="realsense_depth_scale",
            uncertainty="high",
        )

    def _create_bundle_structure(self) -> list[str]:
        """Create the output bundle directory and copy asset files.

        Returns:
            List of files copied to the bundle

        Raises:
            StorageError: If file operations fail
        """
        from scan2mesh.exceptions import StorageError

        # Ensure output directory exists
        output_dir = self.storage.ensure_subdirectory(self.storage.OUTPUT_DIR)
        files_copied: list[str] = []

        # Copy asset files
        for filename in self.ASSET_FILES:
            src_path = self.storage.asset_dir / filename
            dst_path = output_dir / filename

            if not src_path.exists():
                logger.warning(f"Asset file not found: {src_path}")
                continue

            try:
                shutil.copy2(src_path, dst_path)
                files_copied.append(filename)
                logger.debug(f"Copied {filename} to output directory")
            except Exception as e:
                raise StorageError(f"Failed to copy {filename}: {e}") from e

        return files_copied

    def _create_archive(self, object_name: str, class_id: int) -> tuple[Path, int]:
        """Create ZIP archive of the output directory.

        Args:
            object_name: Object name for the archive filename
            class_id: Class ID for the archive filename

        Returns:
            Tuple of (archive_path, archive_size_bytes)

        Raises:
            StorageError: If archive creation fails
        """
        from scan2mesh.exceptions import StorageError

        archive_name = f"{object_name}_{class_id}.zip"
        archive_path = self.project_dir / archive_name
        output_dir = self.storage.output_dir

        try:
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Add all files from output directory
                for file_path in output_dir.iterdir():
                    if file_path.is_file():
                        # Store with just the filename, not the full path
                        zf.write(file_path, file_path.name)
                        logger.debug(f"Added {file_path.name} to archive")

            archive_size = archive_path.stat().st_size
            logger.info(f"Created archive: {archive_path} ({archive_size} bytes)")

            return archive_path, archive_size

        except Exception as e:
            raise StorageError(f"Failed to create archive: {e}") from e

    def package(self) -> PackageResult:
        """Run the full packaging pipeline.

        Creates the asset manifest, bundle structure, and ZIP archive.

        Returns:
            PackageResult with paths and metadata

        Raises:
            ConfigError: If required metrics are missing
            StorageError: If file operations fail
        """
        logger.info(f"Starting packaging for project: {self.project_dir}")

        # Build and save manifest
        manifest = self._build_manifest()
        self.storage.save_manifest(manifest)
        logger.info("Saved asset manifest")

        # Create bundle structure (copy asset files)
        files_copied = self._create_bundle_structure()
        logger.info(f"Copied {len(files_copied)} asset files to output directory")

        # Create ZIP archive
        config = self.storage.load_project_config()
        archive_path, archive_size = self._create_archive(
            config.object_name, config.class_id
        )

        # Build result
        result = PackageResult(
            manifest_path=str(self.storage.manifest_path.relative_to(self.project_dir)),
            archive_path=str(archive_path.relative_to(self.project_dir)),
            output_dir=str(self.storage.output_dir.relative_to(self.project_dir)),
            total_size_bytes=archive_size,
            files_included=["manifest.json", *files_copied],
        )

        logger.info(f"Packaging completed: {result.archive_path}")
        return result

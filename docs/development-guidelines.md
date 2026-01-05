# 開発ガイドライン (Development Guidelines)

## コーディング規約

### 命名規則

#### 変数・関数

**Python**:
```python
# 変数: snake_case、名詞または名詞句
user_profile_data = fetch_user_profile()
capture_metrics = CaptureMetrics()
is_valid = True

# 関数: snake_case、動詞で始める
def calculate_blur_score(image: np.ndarray) -> float:
    pass

def validate_project_config(config: ProjectConfig) -> None:
    pass

# Boolean: is_, has_, should_, can_ で始める
is_keyframe = True
has_texture = False
should_retry = True
can_process = False
```

**原則**:
- 変数: snake_case、名詞または名詞句
- 関数: snake_case、動詞で始める
- 定数: UPPER_SNAKE_CASE
- Boolean: `is_`, `has_`, `should_`, `can_` で始める

#### クラス・型

```python
# クラス: PascalCase、名詞
class ProjectInitializer:
    pass

class CaptureQualityGate:
    pass

# Pydantic Model: PascalCase
class ProjectConfig(BaseModel):
    object_name: str
    class_id: int

# 型エイリアス: PascalCase
QualityStatus = Literal["pass", "warn", "fail"]
FrameList = list[FrameData]

# プロトコル（インターフェース）: PascalCase + Interface または Protocol
class StorageServiceInterface(Protocol):
    def save_frame(self, frame: FrameData) -> None: ...
```

#### 定数

```python
# UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3
DEPTH_VALID_RATIO_WARN = 0.7
DEFAULT_TEXTURE_RESOLUTION = 2048

# 設定オブジェクトの場合
DEFAULT_CONFIG = {
    "max_retry_count": 3,
    "texture_resolution": 2048,
    "voxel_size": 0.002,
}
```

#### ファイル名

```python
# モジュールファイル: snake_case
# capture.py
# storage_service.py
# quality_gate.py

# テストファイル: test_ プレフィックス
# test_capture.py
# test_storage_service.py

# 定数ファイル: snake_case
# thresholds.py
# config.py
```

### コードフォーマット

**インデント**: 4スペース（PEP 8準拠）

**行の長さ**: 最大88文字（Black準拠）

**インポート順序**:
```python
# 1. 標準ライブラリ
import json
import logging
from pathlib import Path
from typing import Optional

# 2. サードパーティ
import cv2
import numpy as np
import open3d as o3d
from pydantic import BaseModel

# 3. ローカルモジュール
from scan2mesh.models import ProjectConfig
from scan2mesh.services import StorageService
```

### 型ヒント

**基本的な型ヒント**:
```python
# 関数の型ヒント
def calculate_coverage_score(viewpoints: list[ViewPoint]) -> float:
    pass

# Optionalの使用
def find_frame(frame_id: int) -> Optional[FrameData]:
    pass

# Union型
def process_input(data: str | Path) -> None:
    pass

# ジェネリクス
def filter_items[T](items: list[T], predicate: Callable[[T], bool]) -> list[T]:
    pass
```

**Pydanticモデルでの型ヒント**:
```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class FrameData(BaseModel):
    frame_id: int = Field(..., ge=0, description="フレームID")
    timestamp: datetime
    rgb_path: str
    depth_path: str
    quality: Optional[FrameQuality] = None

    model_config = {"frozen": True}  # イミュータブル
```

### コメント規約

**関数・クラスのドキュメント（docstring）**:
```python
def calculate_blur_score(image: np.ndarray) -> float:
    """
    Laplacian分散によるブラー検出スコアを計算する。

    Args:
        image: BGR形式の入力画像

    Returns:
        ブラースコア（0.0-1.0、高いほど鮮明）

    Raises:
        ValueError: 画像が空の場合

    Example:
        >>> img = cv2.imread("sample.png")
        >>> score = calculate_blur_score(img)
        >>> print(f"Blur score: {score:.2f}")
    """
    if image is None or image.size == 0:
        raise ValueError("画像が空です")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

    # 正規化（経験的な閾値: 100未満=ぼやけ、500以上=鮮明）
    return min(1.0, max(0.0, (laplacian_var - 100) / 400))
```

**インラインコメント**:
```python
# なぜそうするかを説明
# キャッシュを無効化して最新データを取得
cache.clear()

# 複雑なロジックを説明
# RANSACで床平面を推定し、床より上のポイントのみを抽出
plane_model, inliers = pcd.segment_plane(
    distance_threshold=0.01,
    ransac_n=3,
    num_iterations=1000
)

# TODO/FIXME/HACKの使用
# TODO: キャッシュ機能を実装 (Issue #123)
# FIXME: 大量フレームでメモリ不足の可能性 (Issue #456)
# HACK: Open3Dのバグ回避、v0.19で修正予定
```

**避けるべきコメント**:
```python
# コードの内容を繰り返すだけ
i += 1  # iを1増やす  ← 不要

# 古い情報
# このコードは2024年に追加された  ← 不要

# コメントアウトされたコード  ← 削除すべき
# old_implementation()
```

### エラーハンドリング

**カスタム例外クラス**:
```python
class Scan2MeshError(Exception):
    """基底エラークラス"""
    pass


class ConfigError(Scan2MeshError):
    """設定関連エラー"""
    pass


class CameraError(Scan2MeshError):
    """カメラ関連エラー"""
    pass


class QualityGateError(Scan2MeshError):
    """品質ゲート不合格"""
    def __init__(
        self,
        message: str,
        metrics: dict,
        suggestions: list[str]
    ):
        super().__init__(message)
        self.metrics = metrics
        self.suggestions = suggestions


class ValidationError(Scan2MeshError):
    """入力検証エラー"""
    def __init__(self, message: str, field: str, value: Any):
        super().__init__(message)
        self.field = field
        self.value = value
```

**エラーハンドリングパターン**:
```python
# 適切なエラーハンドリング
async def get_frame(frame_id: int) -> FrameData:
    try:
        frame = await storage.load_frame(frame_id)

        if frame is None:
            raise NotFoundError(f"Frame not found: {frame_id}")

        return frame
    except NotFoundError:
        # 予期されるエラー: ログを出力して再送出
        logger.warning(f"フレームが見つかりません: {frame_id}")
        raise
    except IOError as e:
        # 予期しないエラー: ラップして上位に伝播
        raise StorageError(f"フレームの読み込みに失敗: {frame_id}") from e


# 悪い例: エラーを無視
async def get_frame(frame_id: int) -> Optional[FrameData]:
    try:
        return await storage.load_frame(frame_id)
    except Exception:
        return None  # エラー情報が失われる
```

**エラーメッセージ**:
```python
# 具体的で解決策を示す
raise ValidationError(
    "タイトルは1-100文字で入力してください。現在の文字数: 150",
    field="object_name",
    value=object_name
)

# 悪い例: 曖昧で役に立たない
raise ValueError("Invalid input")
```

## Git運用ルール

### ブランチ戦略

**ブランチ種別**:
- `main`: 本番環境にデプロイ可能な状態
- `develop`: 開発の最新状態
- `feature/[機能名]`: 新機能開発
- `fix/[修正内容]`: バグ修正
- `refactor/[対象]`: リファクタリング

**フロー**:
```
main
  └─ develop
      ├─ feature/turntable-support
      ├─ feature/imu-integration
      └─ fix/depth-filter
```

**運用ルール**:
- `main`: 本番リリース済みの安定版コードのみ。タグでバージョン管理
- `develop`: 次期リリースに向けた最新の開発コード。CIでの自動テスト実施
- `feature/*`, `fix/*`: developから分岐し、作業完了後にPRでdevelopへマージ
- 直接コミット禁止: すべてのブランチでPRレビューを必須

### コミットメッセージ規約

**Conventional Commits形式**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**:
- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント
- `style`: コードフォーマット
- `refactor`: リファクタリング
- `perf`: パフォーマンス改善
- `test`: テスト追加・修正
- `build`: ビルドシステム
- `ci`: CI/CD設定
- `chore`: その他

**例**:
```
feat(capture): RealSenseフレーム取得機能を実装

RealSense D400シリーズからRGB-Dフレームを取得する機能を実装しました。

実装内容:
- CameraServiceクラスを追加
- フレームごとの品質メトリクス計算
- キーフレーム選別ロジック

Closes #45
```

### プルリクエストプロセス

**作成前のチェック**:
- [ ] 全てのテストがパス (`pytest`)
- [ ] Lintエラーがない (`ruff check`)
- [ ] 型チェックがパス (`mypy`)
- [ ] フォーマット済み (`ruff format`)
- [ ] 競合が解決されている

**PRテンプレート**:
```markdown
## 概要
[変更内容の簡潔な説明]

## 変更理由
[なぜこの変更が必要か]

## 変更内容
- [変更点1]
- [変更点2]

## テスト
- [ ] ユニットテスト追加
- [ ] 統合テスト追加
- [ ] 手動テスト実施

## 関連Issue
Closes #[Issue番号]

## レビューポイント
[レビュアーに特に見てほしい点]
```

**レビュープロセス**:
1. セルフレビュー
2. 自動テスト実行（CI）
3. レビュアーアサイン
4. レビューフィードバック対応
5. 承認後マージ

## テスト戦略

### テストの種類

#### ユニットテスト

**対象**: 個別の関数・クラス

**カバレッジ目標**: 80%以上

**例**:
```python
import pytest
from scan2mesh.gates.capture import CaptureQualityGate
from scan2mesh.models import CaptureMetrics


class TestCaptureQualityGate:
    """CaptureQualityGateのテスト"""

    def test_evaluate_pass_with_good_metrics(self):
        """良好なメトリクスでPASS判定される"""
        # Given: 準備
        gate = CaptureQualityGate()
        metrics = CaptureMetrics(
            num_frames_raw=100,
            num_keyframes=28,
            depth_valid_ratio_mean=0.85,
            blur_score_mean=0.78,
            coverage_score=0.92,
        )

        # When: 実行
        status, reasons = gate.evaluate(metrics)

        # Then: 検証
        assert status == "pass"
        assert len(reasons) == 0

    def test_evaluate_fail_with_low_depth_ratio(self):
        """深度有効率が低い場合FAIL判定される"""
        # Given
        gate = CaptureQualityGate()
        metrics = CaptureMetrics(
            num_frames_raw=100,
            num_keyframes=28,
            depth_valid_ratio_mean=0.4,  # 閾値以下
            blur_score_mean=0.78,
            coverage_score=0.92,
        )

        # When
        status, reasons = gate.evaluate(metrics)

        # Then
        assert status == "fail"
        assert "depth_valid_ratio_critical" in reasons
```

#### 統合テスト

**対象**: 複数コンポーネントの連携

**例**:
```python
class TestPipelineFlow:
    """パイプライン全体フローのテスト"""

    @pytest.fixture
    def sample_project(self, tmp_path):
        """テスト用プロジェクトを作成"""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        return project_dir

    def test_init_to_plan_flow(self, sample_project):
        """init → plan のフローが正常に動作する"""
        # Given
        initializer = ProjectInitializer(sample_project)
        planner = CapturePlanner()

        # When: プロジェクト初期化
        config = initializer.initialize(
            object_name="test_ball",
            class_id=0,
            preset=OutputPreset()
        )

        # Then: 設定が保存される
        assert (sample_project / "project.json").exists()

        # When: 撮影計画生成
        plan = planner.generate_plan(CapturePlanPreset.QUICK)

        # Then: 計画が生成される
        assert len(plan.viewpoints) >= 16
        assert plan.min_required_frames > 0
```

#### E2Eテスト

**対象**: ユーザーシナリオ全体

**例**:
```python
class TestCLIWorkflow:
    """CLIワークフローのE2Eテスト"""

    def test_basic_workflow(self, tmp_path, cli_runner):
        """基本的なワークフローが完了できる"""
        # プロジェクト初期化
        result = cli_runner.invoke(
            ["init", "--name", "test_ball", "--class-id", "0"],
            cwd=tmp_path
        )
        assert result.exit_code == 0
        assert "プロジェクトを作成しました" in result.output

        # 撮影計画生成
        result = cli_runner.invoke(
            ["plan", "--preset", "quick"],
            cwd=tmp_path
        )
        assert result.exit_code == 0
        assert "撮影計画を生成しました" in result.output
```

### テスト命名規則

**パターン**: `test_[対象]_[条件]_[期待結果]`

```python
# 良い例
def test_evaluate_pass_with_good_metrics(self): ...
def test_evaluate_fail_with_low_depth_ratio(self): ...
def test_save_frame_creates_rgb_file(self): ...
def test_load_config_raises_error_when_file_not_found(self): ...

# 悪い例
def test_1(self): ...
def test_works(self): ...
def test_capture(self): ...
```

### モック・スタブの使用

**原則**:
- 外部依存（カメラ、ファイルシステム、GPU）はモック化
- ビジネスロジックは実装を使用

```python
from unittest.mock import Mock, patch

class TestRGBDCapture:
    """RGBDCaptureのテスト"""

    def test_capture_frame_returns_valid_data(self):
        """フレーム取得が正常に動作する"""
        # カメラをモック化
        mock_camera = Mock()
        mock_camera.capture_frame.return_value = Mock(
            rgb=np.zeros((1080, 1920, 3), dtype=np.uint8),
            depth=np.zeros((720, 1280), dtype=np.uint16),
        )

        # ストレージをモック化
        mock_storage = Mock()

        capture = RGBDCapture(
            camera=mock_camera,
            storage=mock_storage
        )

        # 実行
        frame = capture.capture_frame()

        # 検証
        assert frame is not None
        mock_camera.capture_frame.assert_called_once()
```

## コードレビュー基準

### レビューポイント

**機能性**:
- [ ] 要件を満たしているか
- [ ] エッジケースが考慮されているか
- [ ] エラーハンドリングが適切か

**可読性**:
- [ ] 命名が明確か
- [ ] docstringが適切か
- [ ] 複雑なロジックが説明されているか

**保守性**:
- [ ] 重複コードがないか
- [ ] 責務が明確に分離されているか
- [ ] 変更の影響範囲が限定的か

**パフォーマンス**:
- [ ] 不要な計算がないか
- [ ] メモリリークの可能性がないか
- [ ] GPU処理が適切に使用されているか

**セキュリティ**:
- [ ] 入力検証が適切か
- [ ] ファイルパスのサニタイズがされているか
- [ ] 機密情報がハードコードされていないか

### レビューコメントの書き方

**優先度の明示**:
- `[必須]`: 修正必須
- `[推奨]`: 修正推奨
- `[提案]`: 検討してほしい
- `[質問]`: 理解のための質問

**建設的なフィードバック**:
```markdown
## 良い例
[推奨] この実装だとフレーム数が増えた時にメモリ使用量が増加します。
ジェネレータを使って遅延評価することを検討してはどうでしょうか？

```python
# 現在
frames = [load_frame(i) for i in range(100)]

# 提案
def frame_generator():
    for i in range(100):
        yield load_frame(i)
```

## 悪い例
この書き方は良くないです。
```

## 開発環境セットアップ

### 必要なツール

| ツール | バージョン | インストール方法 |
|--------|-----------|-----------------|
| Docker | 24.0+ | https://docs.docker.com/get-docker/ |
| Docker Compose | 2.20+ | Dockerに同梱 |
| NVIDIA Driver | 525+ | `sudo apt install nvidia-driver-525` |
| NVIDIA Container Toolkit | 1.14+ | https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html |
| uv | 0.4+ | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

### セットアップ手順

```bash
# 1. リポジトリのクローン
git clone https://github.com/your-org/scan2mesh.git
cd scan2mesh

# 2. Docker環境の構築
cd docker
docker compose build

# 3. コンテナの起動
docker compose up -d

# 4. コンテナに入る
docker compose exec scan2mesh bash

# 5. 開発用依存関係のインストール（コンテナ内）
uv sync --dev

# 6. テストの実行
pytest

# 7. Lintの実行
ruff check .
ruff format --check .
mypy src/
```

### ローカル開発（Dockerなし）

```bash
# 1. Python環境のセットアップ
uv venv
source .venv/bin/activate

# 2. 依存関係のインストール
uv sync --dev

# 3. RealSense SDKのインストール（Ubuntu）
sudo apt install librealsense2-dkms librealsense2-utils

# 4. 開発サーバー（該当する場合）
# なし（CLIツール）

# 5. テストの実行
pytest
```

### 推奨開発ツール

- **IDE**: VSCode + Python拡張機能、Pylance
- **デバッガ**: debugpy（VSCode統合）
- **プロファイラ**: py-spy、memray（メモリプロファイリング）

### VSCode設定

```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "[python]": {
        "editor.formatOnSave": true,
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.codeActionsOnSave": {
            "source.fixAll.ruff": "explicit",
            "source.organizeImports.ruff": "explicit"
        }
    },
    "python.analysis.typeCheckingMode": "basic"
}
```

## CI/CD設定

### GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: uv run ruff check .
      - run: uv run ruff format --check .

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: uv run mypy src/

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: uv run pytest --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v4
        with:
          files: coverage.xml

  build:
    runs-on: ubuntu-latest
    needs: [lint, typecheck, test]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v5
        with:
          context: docker
          push: false
          tags: scan2mesh:test
```

### Pre-commit設定

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.9.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic]
```

```bash
# インストール
uv add --dev pre-commit
pre-commit install
```

## チェックリスト

### 実装完了前に確認

**コード品質**:
- [ ] 命名が明確で一貫している
- [ ] 関数が単一の責務を持っている
- [ ] マジックナンバーがない
- [ ] 型ヒントが適切に記載されている
- [ ] エラーハンドリングが実装されている

**セキュリティ**:
- [ ] 入力検証が実装されている
- [ ] ファイルパスがサニタイズされている
- [ ] 機密情報がハードコードされていない

**パフォーマンス**:
- [ ] 適切なデータ構造を使用している
- [ ] 不要な計算を避けている
- [ ] GPU処理が適切に使用されている

**テスト**:
- [ ] ユニットテストが書かれている
- [ ] テストがパスする
- [ ] エッジケースがカバーされている

**ドキュメント**:
- [ ] 関数・クラスにdocstringがある
- [ ] 複雑なロジックにコメントがある
- [ ] TODOやFIXMEが記載されている（該当する場合）

**ツール**:
- [ ] Lintエラーがない (`ruff check`)
- [ ] フォーマット済み (`ruff format`)
- [ ] 型チェックがパス (`mypy`)

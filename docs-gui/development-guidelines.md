# 開発ガイドライン (Development Guidelines)

## コーディング規約

### 命名規則

#### 変数・関数

**Python**:
```python
# 変数: snake_case、名詞または名詞句
user_profile_data = fetch_user_profile()
task_list = []
is_completed = True

# 関数: snake_case、動詞で始める
def fetch_user_data() -> dict:
    pass

def validate_email(email: str) -> bool:
    pass

def calculate_total_price(items: list[CartItem]) -> float:
    pass

# Boolean: is_, has_, should_, can_で始める
is_valid = True
has_permission = False
should_retry = True
can_delete = False
```

**原則**:
- 変数: snake_case、名詞または名詞句
- 関数: snake_case、動詞で始める
- 定数: UPPER_SNAKE_CASE
- Boolean: `is_`, `has_`, `should_`, `can_`で始める

#### クラス・型定義

```python
# クラス: PascalCase、名詞
class TaskManager:
    pass

class UserAuthenticationService:
    pass

# Pydanticモデル: PascalCase
class Profile(BaseModel):
    id: str
    name: str
    created_at: datetime

# 列挙型: PascalCase、値はUPPER_SNAKE_CASE
class PipelineStage(str, Enum):
    INIT = "init"
    CAPTURE = "capture"
    PREPROCESS = "preprocess"

# 型エイリアス: PascalCase
ProfileId = str
ObjectList = list[ScanObject]
```

#### ファイル名

```python
# モジュール: snake_case
# profile_service.py
# scan_object.py

# Streamlitページ: N_Page_Name.py
# 1_Dashboard.py
# 6_Capture.py

# テスト: test_[対象].py
# test_profile_service.py
```

### コードフォーマット

**インデント**: 4スペース（Pythonの標準）

**行の長さ**: 最大88文字（Ruff/Black標準）

**例**:
```python
# 長い関数呼び出し
result = some_long_function_name(
    first_argument="value",
    second_argument="another_value",
    third_argument=some_other_variable,
)

# 長いリスト
items = [
    "first_item",
    "second_item",
    "third_item",
]

# 長い条件文
if (
    condition_one
    and condition_two
    and condition_three
):
    do_something()
```

### 型ヒント

**原則**: すべての公開関数・メソッドに型ヒントを付ける

```python
from typing import Optional, Callable
from collections.abc import Iterator

# 基本的な型ヒント
def process_items(items: list[str]) -> dict[str, int]:
    return {item: len(item) for item in items}

# Optional の使用
def get_user(user_id: str) -> Optional[User]:
    return users.get(user_id)

# Callable の使用
def execute_with_callback(
    data: dict,
    on_success: Callable[[dict], None],
    on_error: Callable[[Exception], None]
) -> None:
    pass

# ジェネレーター
def iter_frames(project_path: Path) -> Iterator[FrameData]:
    for frame_file in project_path.glob("*.png"):
        yield load_frame(frame_file)
```

### コメント規約

**関数・クラスのドキュメント（docstring）**:
```python
def create_profile(
    name: str,
    description: str = "",
    tags: list[str] | None = None
) -> Profile:
    """プロファイルを作成する。

    新しいプロファイルを作成し、ストレージに保存します。

    Args:
        name: プロファイル名（1-100文字）
        description: プロファイルの説明（オプション）
        tags: タグのリスト（オプション）

    Returns:
        作成されたProfileオブジェクト

    Raises:
        ValidationError: 名前が空または100文字を超える場合
        StorageError: ストレージへの保存に失敗した場合

    Example:
        >>> profile = create_profile(
        ...     name="RoboCup 2025",
        ...     description="大会用オブジェクト",
        ...     tags=["robocup", "2025"]
        ... )
        >>> print(profile.id)
        '550e8400-e29b-41d4-a716-446655440000'
    """
    pass
```

**インラインコメント**:
```python
# 理由を説明
# キャッシュを無効化して最新データを取得
cache.clear()

# 複雑なロジックを説明
# Kadaneのアルゴリズムで最大部分配列和を計算
# 時間計算量: O(n)
max_so_far = arr[0]
max_ending_here = arr[0]

# TODO・FIXMEを活用
# TODO: キャッシュ機能を実装 (Issue #123)
# FIXME: 大量データでパフォーマンス劣化 (Issue #456)
# HACK: 一時的な回避策、後でリファクタリング必要
```

**悪いコメント**:
```python
# コードの内容を繰り返すだけ
# iを1増やす
i += 1

# 古い情報
# このコードは2020年に追加された (不要な情報)

# コメントアウトされたコード（削除すべき）
# old_implementation = lambda: ...
```

### エラーハンドリング

**原則**:
- 予期されるエラー: カスタムエラークラスを定義
- 予期しないエラー: 上位に伝播
- エラーを無視しない

**カスタムエラークラス**:
```python
class Scan2MeshGUIError(Exception):
    """GUI基底エラークラス"""
    pass

class ValidationError(Scan2MeshGUIError):
    """バリデーションエラー"""
    def __init__(self, message: str, field: str, value: Any):
        super().__init__(message)
        self.field = field
        self.value = value

class NotFoundError(Scan2MeshGUIError):
    """リソースが見つからないエラー"""
    def __init__(self, resource: str, id: str):
        super().__init__(f"{resource} not found: {id}")
        self.resource = resource
        self.id = id

class DeviceError(Scan2MeshGUIError):
    """デバイス関連エラー"""
    pass
```

**エラーハンドリングパターン**:
```python
# 適切なエラーハンドリング
async def get_profile(profile_id: str) -> Profile:
    try:
        profile = await storage.load_profile(profile_id)

        if profile is None:
            raise NotFoundError("Profile", profile_id)

        return profile
    except NotFoundError:
        # 予期されるエラー: 適切に処理
        logger.warning(f"プロファイルが見つかりません: {profile_id}")
        raise
    except Exception as e:
        # 予期しないエラー: ラップして上位に伝播
        raise StorageError(f"プロファイルの取得に失敗: {profile_id}") from e

# エラーを無視しない
async def get_profile(profile_id: str) -> Profile | None:
    try:
        return await storage.load_profile(profile_id)
    except Exception:
        return None  # エラー情報が失われる
```

### Streamlit固有の規約

#### セッション状態の管理

```python
# セッション状態の初期化は utils/session.py に集約
def init_session_state():
    """セッション状態を初期化"""
    defaults = {
        "current_profile_id": None,
        "current_object_id": None,
        "capture_running": False,
        "last_error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# セッション状態へのアクセスはヘルパー関数経由
def get_current_profile() -> Optional[Profile]:
    """現在選択中のプロファイルを取得"""
    profile_id = st.session_state.get("current_profile_id")
    if profile_id is None:
        return None
    return profile_service.get_profile(profile_id)

def set_current_profile(profile_id: str) -> None:
    """現在のプロファイルを設定"""
    st.session_state.current_profile_id = profile_id
```

#### コンポーネントの設計

```python
# components/metrics_display.py

def render_quality_badge(status: QualityStatus) -> None:
    """品質バッジを描画"""
    colors = {
        QualityStatus.PASS: "green",
        QualityStatus.WARN: "orange",
        QualityStatus.FAIL: "red",
        QualityStatus.PENDING: "gray",
    }
    color = colors.get(status, "gray")
    st.markdown(
        f'<span style="color: {color}; font-weight: bold;">'
        f'{status.value.upper()}</span>',
        unsafe_allow_html=True
    )

def render_metrics_table(
    metrics: dict[str, Any],
    thresholds: dict[str, tuple[float, float]]
) -> None:
    """メトリクステーブルを描画

    Args:
        metrics: メトリクス辞書
        thresholds: 各メトリクスの (warn閾値, fail閾値)
    """
    pass
```

#### ページの構造

```python
# pages/6_Capture.py
import streamlit as st
from components.camera_preview import render_camera_preview
from components.quality_badge import render_quality_badge
from services.pipeline_service import PipelineService
from utils.session import get_current_object, require_object_selected

def main():
    st.title("Capture")

    # 前提条件のチェック
    obj = require_object_selected()
    if obj is None:
        return

    # メインコンテンツ
    render_capture_controls(obj)
    render_preview_section()
    render_quality_section()

def render_capture_controls(obj: ScanObject) -> None:
    """撮影コントロールを描画"""
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Start Capture", disabled=st.session_state.capture_running):
            start_capture(obj)

    with col2:
        if st.button("Stop", disabled=not st.session_state.capture_running):
            stop_capture()

    with col3:
        if st.button("Reset"):
            reset_capture(obj)

if __name__ == "__main__":
    main()
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
      ├─ feature/profile-management
      ├─ feature/capture-preview
      └─ fix/camera-connection
```

### コミットメッセージ規約

**フォーマット**:
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
- `test`: テスト追加・修正
- `chore`: ビルド、補助ツール等

**例**:
```
feat(capture): リアルタイム品質メトリクス表示を追加

撮影中に品質メトリクス（深度有効率、ブラースコア、カバレッジ）を
リアルタイムで表示する機能を実装しました。

- components/quality_metrics.py を追加
- CaptureServiceにメトリクス計算コールバックを追加
- pages/6_Capture.py にメトリクス表示セクションを追加

Closes #45
```

### プルリクエストプロセス

**作成前のチェック**:
- [ ] 全てのテストがパス (`uv run pytest`)
- [ ] Lintエラーがない (`uv run ruff check`)
- [ ] 型チェックがパス (`uv run mypy`)
- [ ] フォーマット済み (`uv run ruff format`)
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
- [ ] 手動テスト実施
- [ ] E2Eテスト追加（UI変更の場合）

## スクリーンショット（UI変更の場合）
[画像]

## 関連Issue
Closes #[Issue番号]
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
# tests/unit/services/test_profile_service.py
import pytest
from app.services.profile_service import ProfileService
from app.models.profile import Profile

class TestProfileService:
    """ProfileServiceのテスト"""

    def test_create_profile_with_valid_data(self, tmp_path):
        """正常なデータでプロファイルを作成できる"""
        # Given
        service = ProfileService(tmp_path / "profiles")
        name = "Test Profile"
        description = "Test description"

        # When
        profile = service.create_profile(name, description)

        # Then
        assert profile.id is not None
        assert profile.name == name
        assert profile.description == description
        assert profile.created_at is not None

    def test_create_profile_with_empty_name_raises_error(self, tmp_path):
        """名前が空の場合ValidationErrorをスロー"""
        # Given
        service = ProfileService(tmp_path / "profiles")

        # When/Then
        with pytest.raises(ValidationError) as exc_info:
            service.create_profile("")

        assert exc_info.value.field == "name"
```

#### 統合テスト

**対象**: 複数コンポーネントの連携

**例**:
```python
# tests/integration/test_profile_workflow.py
import pytest

class TestProfileWorkflow:
    """プロファイルワークフローの統合テスト"""

    def test_profile_crud_workflow(self, tmp_path):
        """プロファイルの作成・取得・更新・削除ができる"""
        profile_service = ProfileService(tmp_path / "profiles")
        object_service = ObjectService(tmp_path / "profiles", tmp_path / "projects")

        # 作成
        profile = profile_service.create_profile("Test Profile")
        assert profile.id is not None

        # オブジェクト追加
        obj = object_service.create_object(
            profile_id=profile.id,
            name="test_object",
            class_id=0
        )
        assert obj.profile_id == profile.id

        # 更新
        updated = profile_service.update_profile(
            profile.id,
            description="Updated description"
        )
        assert updated.description == "Updated description"

        # 削除
        result = profile_service.delete_profile(profile.id)
        assert result is True
        assert profile_service.get_profile(profile.id) is None
```

#### E2Eテスト（chrome-devtools-mcp使用）

**対象**: ユーザーシナリオ全体

**例**:
```python
# tests/e2e/test_profile_crud.py
import pytest

class TestProfileCRUDE2E:
    """プロファイルCRUDのE2Eテスト"""

    async def test_create_profile_via_ui(self, page):
        """UIからプロファイルを作成できる"""
        # Profilesページに遷移
        await page.click('[data-testid="nav-profiles"]')

        # 新規作成ボタンをクリック
        await page.click('[data-testid="btn-create-profile"]')

        # フォーム入力
        await page.fill('[data-testid="input-name"]', "Test Profile")
        await page.fill('[data-testid="input-description"]', "Test")

        # 作成
        await page.click('[data-testid="btn-submit"]')

        # 成功メッセージを確認
        success = await page.wait_for_selector('[data-testid="success-message"]')
        assert "作成しました" in await success.text_content()
```

### テスト命名規則

**パターン**: `test_[対象]_[条件]_[期待結果]`

**例**:
```python
# 良い例
def test_create_profile_with_valid_data_returns_profile():
    pass

def test_create_profile_with_empty_name_raises_validation_error():
    pass

def test_get_profile_with_nonexistent_id_returns_none():
    pass

# 悪い例
def test_profile():
    pass

def test_1():
    pass
```

### モック・フィクスチャの使用

**原則**:
- 外部依存（カメラ、ファイルシステム）はモック化
- ビジネスロジックは実装を使用

**例**:
```python
# conftest.py
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def mock_device_service():
    """DeviceServiceのモック"""
    service = Mock()
    service.list_devices.return_value = [
        DeviceInfo(
            serial_number="123456",
            name="Intel RealSense D435",
            firmware_version="5.12.0",
            usb_type="3.2",
            is_connected=True
        )
    ]
    service.test_capture.return_value = (
        np.zeros((480, 640, 3), dtype=np.uint8),  # RGB
        np.zeros((480, 640), dtype=np.uint16)     # Depth
    )
    return service

@pytest.fixture
def profile_service(tmp_path):
    """ProfileServiceのインスタンス"""
    return ProfileService(tmp_path / "profiles")
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
- [ ] キャッシュが適切に使用されているか

**セキュリティ**:
- [ ] 入力検証が適切か
- [ ] 機密情報がハードコードされていないか
- [ ] パストラバーサル対策がされているか

### レビューコメントの書き方

**建設的なフィードバック**:
```markdown
## 良い例
この実装だと、プロファイル数が増えた時にパフォーマンスが劣化する可能性があります。
`list_profiles()`の結果をキャッシュするか、ページネーションを検討してはどうでしょうか？

## 悪い例
この書き方は良くないです。
```

**優先度の明示**:
- `[必須]`: 修正必須
- `[推奨]`: 修正推奨
- `[提案]`: 検討してほしい
- `[質問]`: 理解のための質問

## 開発環境セットアップ

### 必要なツール

| ツール | バージョン | インストール方法 |
|--------|-----------|-----------------|
| Docker | 24.0+ | 公式サイトからインストール |
| Docker Compose | 2.20+ | Dockerに同梱 |
| uv | 0.4+ | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Python | 3.10+ | uvが管理 |

### セットアップ手順

```bash
# 1. リポジトリのクローン
git clone <repository-url>
cd scan2mesh

# 2. 仮想環境の作成と依存関係のインストール
uv venv
source .venv/bin/activate
uv sync

# 3. 開発用依存関係のインストール
uv sync --group dev

# 4. 設定ファイルの準備
cp config/app_config.example.json config/app_config.json

# 5. アプリケーションの起動（ローカル）
uv run streamlit run app/main.py

# または Docker で起動（CPU版）
docker compose -f docker-compose.cpu.yml up
```

### 開発コマンド

```bash
# リント
uv run ruff check .

# フォーマット
uv run ruff format .

# 型チェック
uv run mypy app/

# テスト実行
uv run pytest

# カバレッジ付きテスト
uv run pytest --cov=app --cov-report=html

# 特定のテストのみ実行
uv run pytest tests/unit/services/test_profile_service.py -v
```

### VSCode推奨設定

```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.analysis.typeCheckingMode": "strict",
    "editor.formatOnSave": true,
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.codeActionsOnSave": {
            "source.organizeImports": "explicit",
            "source.fixAll": "explicit"
        }
    },
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"]
}
```

### 推奨VSCode拡張機能

- `ms-python.python`: Python言語サポート
- `charliermarsh.ruff`: Ruffリンター
- `ms-python.mypy-type-checker`: mypy型チェック
- `ms-toolsai.jupyter`: Jupyter Notebook対応

## 品質チェックの自動化

### pre-commitフック

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
        additional_dependencies: [pydantic, streamlit]
```

```bash
# pre-commitのインストール
uv run pre-commit install

# 手動実行
uv run pre-commit run --all-files
```

### CI/CD（GitHub Actions）

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v1

      - name: Set up Python
        run: uv python install 3.10

      - name: Install dependencies
        run: uv sync --group dev

      - name: Lint
        run: uv run ruff check .

      - name: Type check
        run: uv run mypy app/

      - name: Test
        run: uv run pytest --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

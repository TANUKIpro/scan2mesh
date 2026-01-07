# リポジトリ構造定義書 (Repository Structure Document)

## プロジェクト構造

```
scan2mesh-gui/
├── app/                          # Streamlit GUIアプリケーション
│   ├── main.py                   # アプリケーションエントリーポイント
│   ├── pages/                    # Streamlitページ
│   ├── components/               # 再利用可能UIコンポーネント
│   ├── services/                 # ビジネスロジックサービス
│   ├── data/                     # データアクセスレイヤー
│   ├── models/                   # Pydanticデータモデル
│   ├── utils/                    # ユーティリティ関数
│   └── config.py                 # アプリケーション設定
│
├── tests/                        # テストコード
│   ├── unit/                     # ユニットテスト
│   ├── integration/              # 統合テスト
│   └── e2e/                      # E2Eテスト
│
├── docker/                       # Docker関連ファイル
│   ├── Dockerfile.cpu            # CPU版Dockerfile
│   ├── Dockerfile.gpu            # GPU版Dockerfile
│   └── entrypoint.sh             # コンテナエントリーポイント
│
├── docs-gui/                     # GUIプロジェクトドキュメント
│   ├── product-requirements.md
│   ├── functional-design.md
│   ├── architecture.md
│   ├── repository-structure.md   # 本ドキュメント
│   ├── development-guidelines.md
│   └── glossary.md
│
├── config/                       # 設定ファイル
│   └── app_config.json           # デフォルト設定
│
├── profiles/                     # プロファイルデータ（実行時生成）
├── projects/                     # scan2meshプロジェクト（実行時生成）
├── output/                       # 出力バンドル（実行時生成）
├── logs/                         # ログファイル（実行時生成）
│
├── docker-compose.cpu.yml        # CPU版Docker Compose
├── docker-compose.gpu.yml        # GPU版Docker Compose
├── pyproject.toml                # プロジェクト設定
├── uv.lock                       # 依存関係ロックファイル
└── README.md                     # プロジェクトREADME
```

## ディレクトリ詳細

### app/ (アプリケーションディレクトリ)

#### app/main.py

**役割**: Streamlitアプリケーションのエントリーポイント

**内容**:
- ページ設定（タイトル、レイアウト、アイコン）
- サイドバー描画
- セッション状態の初期化
- ロギング設定

**例**:
```python
# main.py
import streamlit as st
from components.sidebar import render_sidebar
from utils.session import init_session_state

def main():
    st.set_page_config(
        page_title="scan2mesh GUI",
        page_icon="📦",
        layout="wide"
    )

    init_session_state()
    render_sidebar()

    st.title("scan2mesh GUI")
    # メインコンテンツ

if __name__ == "__main__":
    main()
```

#### app/pages/

**役割**: Streamlitのマルチページ構成

**配置ファイル**:
- `1_Dashboard.py`: ダッシュボードページ
- `2_Profiles.py`: プロファイル管理ページ
- `3_Registry.py`: オブジェクトレジストリページ
- `4_Devices.py`: デバイス管理ページ
- `5_Capture_Plan.py`: 撮影計画ページ
- `6_Capture.py`: 撮影ページ
- `7_Preprocess.py`: 前処理ページ
- `8_Reconstruct.py`: 3D復元ページ
- `9_Optimize.py`: 最適化ページ
- `10_Package.py`: パッケージングページ
- `11_Report.py`: 品質レポートページ
- `12_Settings.py`: 設定ページ

**命名規則**:
- プレフィックス番号でページ順序を制御
- アンダースコアでスペースを表現
- PascalCase

**依存関係**:
- 依存可能: `components/`, `services/`, `models/`, `utils/`
- 依存禁止: 他の`pages/`ファイル（直接）

**例**:
```
pages/
├── 1_Dashboard.py
├── 2_Profiles.py
├── 3_Registry.py
├── 4_Devices.py
├── 5_Capture_Plan.py
├── 6_Capture.py
├── 7_Preprocess.py
├── 8_Reconstruct.py
├── 9_Optimize.py
├── 10_Package.py
├── 11_Report.py
└── 12_Settings.py
```

#### app/components/

**役割**: 再利用可能なUIコンポーネント

**配置ファイル**:
- `sidebar.py`: サイドバーコンポーネント
- `metrics_display.py`: メトリクス表示コンポーネント
- `viewer_3d.py`: 3Dビューアコンポーネント
- `camera_preview.py`: カメラプレビューコンポーネント
- `quality_badge.py`: 品質バッジコンポーネント
- `progress_tracker.py`: 進捗トラッカーコンポーネント
- `object_card.py`: オブジェクトカードコンポーネント
- `profile_selector.py`: プロファイル選択コンポーネント

**命名規則**:
- snake_case
- 機能を表す名前

**依存関係**:
- 依存可能: `models/`, `utils/`
- 依存禁止: `pages/`, `services/`（直接呼び出しはページから）

**例**:
```
components/
├── __init__.py
├── sidebar.py
├── metrics_display.py
├── viewer_3d.py
├── camera_preview.py
├── quality_badge.py
├── progress_tracker.py
├── object_card.py
└── profile_selector.py
```

#### app/services/

**役割**: ビジネスロジックの実装（サービスレイヤー）

**配置ファイル**:
- `profile_service.py`: プロファイル管理サービス
- `object_service.py`: オブジェクト管理サービス
- `device_service.py`: デバイス管理サービス
- `pipeline_service.py`: パイプライン実行サービス
- `metrics_service.py`: メトリクス計算サービス

**命名規則**:
- snake_case
- `*_service.py` パターン

**依存関係**:
- 依存可能: `data/`, `models/`, `utils/`, scan2mesh Core
- 依存禁止: `pages/`, `components/`

**例**:
```
services/
├── __init__.py
├── profile_service.py
├── object_service.py
├── device_service.py
├── pipeline_service.py
└── metrics_service.py
```

#### app/data/

**役割**: データアクセスレイヤー（データ永続化）

**配置ファイル**:
- `profile_storage.py`: プロファイルストレージ
- `object_storage.py`: オブジェクトストレージ
- `config_storage.py`: 設定ストレージ
- `base_storage.py`: ストレージ基底クラス

**命名規則**:
- snake_case
- `*_storage.py` パターン

**依存関係**:
- 依存可能: `models/`, `utils/`
- 依存禁止: `pages/`, `components/`, `services/`

**例**:
```
data/
├── __init__.py
├── base_storage.py
├── profile_storage.py
├── object_storage.py
└── config_storage.py
```

#### app/models/

**役割**: Pydanticデータモデル定義

**配置ファイル**:
- `profile.py`: Profileモデル
- `scan_object.py`: ScanObjectモデル
- `device.py`: DeviceInfoモデル
- `config.py`: AppConfigモデル
- `enums.py`: 列挙型定義

**命名規則**:
- snake_case（ファイル名）
- PascalCase（クラス名）

**依存関係**:
- 依存可能: なし（純粋なデータ定義）
- 依存禁止: 他のすべてのディレクトリ

**例**:
```
models/
├── __init__.py
├── profile.py
├── scan_object.py
├── device.py
├── config.py
└── enums.py
```

#### app/utils/

**役割**: ユーティリティ関数

**配置ファイル**:
- `session.py`: セッション状態管理
- `validators.py`: バリデーション関数
- `formatters.py`: フォーマット関数
- `image_utils.py`: 画像処理ユーティリティ
- `file_utils.py`: ファイル操作ユーティリティ

**命名規則**:
- snake_case
- 機能を表す名前

**依存関係**:
- 依存可能: `models/`
- 依存禁止: `pages/`, `components/`, `services/`, `data/`

**例**:
```
utils/
├── __init__.py
├── session.py
├── validators.py
├── formatters.py
├── image_utils.py
└── file_utils.py
```

### tests/ (テストディレクトリ)

#### tests/unit/

**役割**: ユニットテストの配置

**構造**:
```
tests/unit/
├── services/
│   ├── test_profile_service.py
│   ├── test_object_service.py
│   └── test_pipeline_service.py
├── data/
│   ├── test_profile_storage.py
│   └── test_object_storage.py
├── models/
│   ├── test_profile.py
│   └── test_scan_object.py
└── utils/
    ├── test_validators.py
    └── test_formatters.py
```

**命名規則**:
- パターン: `test_[テスト対象ファイル名].py`
- 例: `profile_service.py` → `test_profile_service.py`

#### tests/integration/

**役割**: 統合テストの配置

**構造**:
```
tests/integration/
├── test_profile_workflow.py
├── test_object_workflow.py
└── test_pipeline_workflow.py
```

**命名規則**:
- パターン: `test_[ワークフロー名].py`

#### tests/e2e/

**役割**: E2Eテスト（chrome-devtools-mcp使用）

**構造**:
```
tests/e2e/
├── test_dashboard.py
├── test_profile_crud.py
├── test_capture_flow.py
└── conftest.py
```

**命名規則**:
- パターン: `test_[シナリオ名].py`

### docker/ (Docker関連ディレクトリ)

**役割**: Docker関連ファイルの配置

**配置ファイル**:
- `Dockerfile.cpu`: CPU版イメージ定義
- `Dockerfile.gpu`: GPU版イメージ定義
- `entrypoint.sh`: コンテナ起動スクリプト

**例**:
```
docker/
├── Dockerfile.cpu
├── Dockerfile.gpu
└── entrypoint.sh
```

### docs-gui/ (ドキュメントディレクトリ)

**配置ドキュメント**:
- `product-requirements.md`: プロダクト要求定義書
- `functional-design.md`: 機能設計書
- `architecture.md`: アーキテクチャ設計書
- `repository-structure.md`: リポジトリ構造定義書（本ドキュメント）
- `development-guidelines.md`: 開発ガイドライン
- `glossary.md`: 用語集

### config/ (設定ファイルディレクトリ)

**配置ファイル**:
- `app_config.json`: デフォルトアプリケーション設定

**例**:
```json
{
  "profiles_dir": "profiles",
  "projects_dir": "projects",
  "output_dir": "output",
  "log_level": "INFO",
  "default_preset": {
    "coordinate_system": "Z-up",
    "units": "meter",
    "texture_resolution": 2048
  }
}
```

### 実行時生成ディレクトリ

#### profiles/

**役割**: プロファイルデータの永続化

**構造**:
```
profiles/
└── {profile_id}/
    ├── profile.json
    └── objects/
        └── {object_id}/
            ├── object.json
            └── reference/
```

#### projects/

**役割**: scan2meshプロジェクトの保存

**構造**:
```
projects/
└── {object_id}/
    ├── project.json
    ├── capture_plan.json
    ├── raw_frames/
    ├── masked_frames/
    ├── recon/
    ├── asset/
    └── metrics/
```

#### output/

**役割**: 出力バンドルの一時保存

#### logs/

**役割**: アプリケーションログの保存

## ファイル配置規則

### ソースファイル

| ファイル種別 | 配置先 | 命名規則 | 例 |
|------------|--------|---------|-----|
| ページ | `app/pages/` | `N_Page_Name.py` | `1_Dashboard.py` |
| コンポーネント | `app/components/` | `snake_case.py` | `metrics_display.py` |
| サービス | `app/services/` | `*_service.py` | `profile_service.py` |
| ストレージ | `app/data/` | `*_storage.py` | `profile_storage.py` |
| モデル | `app/models/` | `snake_case.py` | `scan_object.py` |
| ユーティリティ | `app/utils/` | `snake_case.py` | `validators.py` |

### テストファイル

| テスト種別 | 配置先 | 命名規則 | 例 |
|-----------|--------|---------|-----|
| ユニットテスト | `tests/unit/` | `test_[対象].py` | `test_profile_service.py` |
| 統合テスト | `tests/integration/` | `test_[ワークフロー].py` | `test_profile_workflow.py` |
| E2Eテスト | `tests/e2e/` | `test_[シナリオ].py` | `test_capture_flow.py` |

### 設定ファイル

| ファイル種別 | 配置先 | 命名規則 |
|------------|--------|---------|
| アプリ設定 | `config/` | `app_config.json` |
| Docker設定 | `docker/` | `Dockerfile.*` |
| プロジェクト設定 | ルート | `pyproject.toml` |
| Streamlit設定 | `app/.streamlit/` | `config.toml` |

## 命名規則

### ディレクトリ名

- **レイヤーディレクトリ**: 複数形、snake_case
  - 例: `services/`, `components/`, `models/`
- **機能ディレクトリ**: 単数形、snake_case
  - 例: `profile/`, `capture/`
- **実行時データ**: 複数形、snake_case
  - 例: `profiles/`, `projects/`, `logs/`

### ファイル名

- **クラスファイル**: snake_case
  - 例: `profile_service.py`, `scan_object.py`
- **Streamlitページ**: `N_Page_Name.py`（N=表示順番号）
  - 例: `1_Dashboard.py`, `6_Capture.py`
- **テストファイル**: `test_[対象].py`
  - 例: `test_profile_service.py`

### クラス名・関数名

- **クラス名**: PascalCase
  - 例: `ProfileService`, `ScanObject`
- **関数名**: snake_case
  - 例: `render_sidebar()`, `load_profile()`
- **定数**: UPPER_SNAKE_CASE
  - 例: `DEFAULT_TEXTURE_RESOLUTION`, `MAX_FILE_SIZE`

## 依存関係のルール

### レイヤー間の依存

```
pages/
    ↓ (OK)
components/ ←→ services/
    ↓ (OK)      ↓ (OK)
    └───→ data/ ←───┘
           ↓ (OK)
         models/
           ↓ (OK)
         utils/
```

**許可される依存**:
- `pages/` → `components/`, `services/`, `models/`, `utils/`
- `components/` → `models/`, `utils/`
- `services/` → `data/`, `models/`, `utils/`, scan2mesh Core
- `data/` → `models/`, `utils/`
- `models/` → `utils/`（最小限）
- `utils/` → なし（または`models/`のみ）

**禁止される依存**:
- `data/` → `services/` (❌)
- `data/` → `pages/` (❌)
- `services/` → `pages/` (❌)
- `services/` → `components/` (❌)
- `models/` → `services/`, `data/` (❌)
- 循環依存 (❌)

### モジュール間の依存

**循環依存の禁止**:
```python
# ❌ 悪い例: 循環依存
# profile_service.py
from .object_service import ObjectService

# object_service.py
from .profile_service import ProfileService  # 循環依存
```

**解決策**:
```python
# ✅ 良い例: 依存性注入
# object_service.py
class ObjectService:
    def __init__(self, profile_getter: Callable[[str], Profile]):
        self.get_profile = profile_getter
```

## スケーリング戦略

### 機能の追加

新しい機能を追加する際の配置方針:

1. **新規ページ**: `pages/`にファイル追加（番号プレフィックス調整）
2. **新規コンポーネント**: `components/`にファイル追加
3. **新規サービス**: `services/`にファイル追加
4. **新規モデル**: `models/`にファイル追加

**例: ターンテーブル連携機能の追加**
```
app/
├── pages/
│   └── 13_Turntable.py          # 新規ページ
├── components/
│   └── turntable_control.py     # 新規コンポーネント
├── services/
│   └── turntable_service.py     # 新規サービス
└── models/
    └── turntable.py             # 新規モデル
```

### ファイルサイズの管理

**ファイル分割の目安**:
- 1ファイル: 300行以下を推奨
- 300-500行: リファクタリングを検討
- 500行以上: 分割を強く推奨

**分割方法**:
```python
# 悪い例: 1ファイルに全コンポーネント
# components/metrics_display.py (600行)

# 良い例: 責務ごとに分割
# components/metrics/
# ├── __init__.py
# ├── capture_metrics.py
# ├── recon_metrics.py
# └── asset_metrics.py
```

### ページの複雑化への対応

ページが複雑になった場合のリファクタリング:

```
# Before: 単一ファイル
pages/
└── 6_Capture.py (500行)

# After: ページ用サブディレクトリ
pages/
├── 6_Capture.py (メインエントリー、100行)
└── capture/
    ├── __init__.py
    ├── preview_section.py
    ├── quality_section.py
    └── controls_section.py
```

## 特殊ディレクトリ

### .streamlit/

**役割**: Streamlit設定

**構造**:
```
app/.streamlit/
└── config.toml
```

**config.toml例**:
```toml
[server]
port = 8501
address = "0.0.0.0"

[theme]
primaryColor = "#007bff"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f8f9fa"
textColor = "#212529"
```

### .steering/ (ステアリングファイル)

**役割**: 特定の開発作業における計画・進捗管理

**構造**:
```
.steering/
└── [YYYYMMDD]-[task-name]/
    ├── requirements.md
    ├── design.md
    └── tasklist.md
```

### .claude/ (Claude Code設定)

**役割**: Claude Code設定とカスタマイズ

**構造**:
```
.claude/
├── commands/
├── skills/
└── agents/
```

## 除外設定

### .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
.venv/

# 実行時生成
profiles/
projects/
output/
logs/

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db

# テスト
.pytest_cache/
.coverage
htmlcov/

# ステアリングファイル
.steering/
```

### .dockerignore

```dockerignore
.git
.gitignore
.steering/
__pycache__
*.pyc
.pytest_cache
.coverage
htmlcov/
docs-gui/
tests/
.venv/
*.md
!README.md
```

# scan2mesh

> RealSenseカメラで撮るだけで、シミュレーション・機械学習用の3Dアセットを生成するCLIツール

scan2meshは、Intel RealSenseカメラを用いた3Dスキャンから、シミュレーション・機械学習に使える高品質な3Dメッシュを自動生成するPythonパイプラインです。

## 特徴

- **品質ゲート付きパイプライン**: 各ステージで品質を自動判定し、「使える/要注意/使えない」を明確化
- **再現可能なアセット生成**: 同じ入力・設定から同じ出力を得られる決定論的なパイプライン
- **段階的な処理**: 8つのステージに分割された柔軟なワークフロー
- **CLI優先設計**: すべての機能がコマンドラインから実行可能
- **型安全**: Pydantic v2による堅牢なデータモデル

## 開発ステータス

**現在のバージョン**: 0.1.0 (Alpha)

### 実装状況

| Stage | ステージ名 | ステータス | 説明 |
|-------|-----------|----------|------|
| 0 | init | ✅ 完全実装 | プロジェクト初期化 |
| 1 | plan | ✅ 完全実装 | 撮影計画生成 |
| 2 | capture | 🚧 スタブのみ | RGBDフレーム取得 |
| 3 | preprocess | 🚧 スタブのみ | 前処理・背景除去 |
| 4 | reconstruct | 🚧 スタブのみ | 3D復元 |
| 5 | optimize | 🚧 スタブのみ | アセット最適化 |
| 6 | package | 🚧 スタブのみ | パッケージング |
| 7 | report | 🚧 スタブのみ | 品質レポート |

### ロードマップ

| フェーズ | 内容 | ステータス |
|---------|------|----------|
| Phase 1 | init, plan の完全実装 | ✅ 完了 |
| Phase 2 | capture, preprocess の実装 | 📋 予定 |
| Phase 3 | reconstruct, optimize の実装 | 📋 予定 |
| Phase 4 | package, report の実装 | 📋 予定 |
| Phase 5 | Docker環境の整備 | 📋 予定 |

## パイプライン構成

scan2meshは8つのステージ（Stage 0: init から Stage 7: report）からなるパイプライン構造を採用しています。

```mermaid
graph LR
    A[0. init] --> B[1. plan]
    B --> C[2. capture]
    C --> D[3. preprocess]
    D --> E[4. reconstruct]
    E --> F[5. optimize]
    F --> G[6. package]
    G --> H[7. report]

    style A fill:#90EE90
    style B fill:#90EE90
    style C fill:#FFE4B5
    style D fill:#FFE4B5
    style E fill:#FFE4B5
    style F fill:#FFE4B5
    style G fill:#FFE4B5
    style H fill:#FFE4B5
```

### Stage 0: プロジェクト初期化 (init) ✅

プロジェクトディレクトリと設定ファイルを作成します。

**機能**:
- プロジェクト構造の生成（7つのディレクトリ）
- オブジェクト情報の登録（名前、クラスID、タグ）
- スケール情報の設定（既知寸法またはRealSenseスケール）
- 設定ハッシュの生成（再現性の確保）

**出力**:
- `project.json`: プロジェクト設定
- 7つの作業ディレクトリ（raw_frames, keyframes, masked_frames, recon, asset, metrics, logs）

### Stage 1: 撮影計画生成 (plan) ✅

最適な撮影視点を自動生成します。

**プリセット**:

| プリセット | 視点数 | 仰角パターン | 最低フレーム数 | 推奨用途 |
|-----------|--------|------------|--------------|---------|
| QUICK | 16 | 2段階 (0°, 30°) | 12 | 簡単な物体 |
| STANDARD | 36 | 3段階 (-15°, 15°, 45°) | 20 | 標準的な物体（推奨） |
| HARD | 48 | 4段階 (-30°, 0°, 30°, 60°) | 30 | 複雑な物体 |

**出力**:
- `capture_plan.json`: 撮影計画
  - 視点リスト（方位角、仰角、距離）
  - 最低必要フレーム数
  - 撮影順序
  - 撮影時の注意事項

### Stage 2: RGBDフレーム取得 (capture) 🚧

RealSenseカメラからRGB-Dデータを取得します。

**予定機能**:
- RealSenseストリームの取得（RGB、Depth、intrinsics）
- リアルタイム品質監視（深度有効率、ブラースコア、カバレッジ）
- キーフレームの自動選別
- 品質ゲートによるWARN/FAIL判定

### Stage 3: 前処理 (preprocess) 🚧

撮影データから背景を除去し、復元に最適な状態に整えます。

**予定機能**:
- Depthフィルタリング（穴埋め、外れ値除去）
- RGB-Dアラインメント
- 背景除去（深度閾値 or 床平面推定）
- マスク品質の評価

### Stage 4: 3D復元 (reconstruct) 🚧

前処理済みのRGBDデータから3Dメッシュを生成します。

**予定機能**:
- フレーム間の姿勢推定（RGBD odometry）
- TSDFフュージョン
- メッシュ抽出
- テクスチャ生成（UV、アトラス）
- 追跡破綻の検出

### Stage 5: アセット最適化 (optimize) 🚧

生成されたメッシュをシミュレーション・学習に適した形式に最適化します。

**予定機能**:
- スケール確定（既知実寸 or RealSenseスケール）
- 軸/原点の正規化（Z-up、底面中心原点）
- メッシュ修正（法線、非多様体、穴）
- LOD生成（LOD0: ~100k tris, LOD1: ~30k, LOD2: ~10k）
- 衝突メッシュ生成（Convex hull）
- テクスチャ最適化（2k上限、圧縮）

### Stage 6: パッケージング (package) 🚧

最適化されたアセットを配布可能な形式でパッケージングします。

**予定機能**:
- 規定のバンドル構造生成
- マニフェストファイル生成（メタデータ、品質ステータス、来歴）
- プレビュー画像生成
- ZIP圧縮

### Stage 7: 品質レポート (report) 🚧

生成されたアセットの品質と次に取るべきアクションを提示します。

**予定機能**:
- キャプチャ品質の表示
- 復元品質の表示
- アセット品質の表示
- 総合判定（PASS/WARN/FAIL）
- 次アクションの提案

## インストール

### 前提条件

- Python 3.10以上
- uv（推奨パッケージマネージャ）

### uvのインストール

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

### scan2meshのインストール

```bash
# リポジトリをクローン
git clone https://github.com/scan2mesh/scan2mesh.git
cd scan2mesh

# 依存関係をインストール
uv sync

# CLIが使えることを確認
uv run scan2mesh --help
```

### 開発環境のセットアップ

```bash
# 開発用依存関係（テスト、リント等）を含めてインストール
uv sync --all-extras

# テストを実行して確認
uv run pytest
```

## クイックスタート

### 1. プロジェクトの初期化

新しいスキャンプロジェクトを作成します。

```bash
uv run scan2mesh init \
  --name robocup_ball \
  --class-id 0 \
  --tags ball,robocup \
  --dimension 220 \
  --dimension-type diameter
```

**生成されるディレクトリ構造**:

```
./projects/robocup_ball/
├── project.json          # プロジェクト設定
├── raw_frames/           # 生フレームデータ
├── keyframes/            # キーフレーム
├── masked_frames/        # マスク適用済みフレーム
├── recon/                # 復元結果
├── asset/                # 最適化済みアセット
├── metrics/              # メトリクス
└── logs/                 # ログ
```

### 2. 撮影計画の生成

プロジェクトの撮影計画を生成します。

```bash
uv run scan2mesh plan ./projects/robocup_ball --preset standard
```

**生成されるファイル**:

`./projects/robocup_ball/capture_plan.json`:

```json
{
  "preset": "standard",
  "viewpoints": [
    {
      "index": 0,
      "azimuth_deg": 0.0,
      "elevation_deg": -15.0,
      "distance_m": 0.4,
      "order": 0
    }
  ],
  "min_required_frames": 20,
  "recommended_distance_m": 0.4,
  "notes": [...]
}
```

### 次のステップ

現在実装済みの機能は `init` と `plan` のみです。
Stage 2 (capture) 以降は開発中のため、以下のコマンドは `NotImplementedError` を発生させます:

```bash
# これらは現在動作しません
uv run scan2mesh capture ./projects/robocup_ball
uv run scan2mesh preprocess ./projects/robocup_ball
```

## コマンドリファレンス

### scan2mesh init

新しいスキャンプロジェクトを初期化します。

**構文**:
```bash
scan2mesh init --name NAME --class-id ID [OPTIONS]
```

**必須オプション**:

| オプション | 短縮形 | 型 | 説明 |
|-----------|--------|-----|------|
| `--name` | `-n` | TEXT | オブジェクト名（英数字、アンダースコア、ハイフンのみ） |
| `--class-id` | `-c` | INTEGER | クラスID (0-9999) |

**任意オプション**:

| オプション | 短縮形 | 型 | デフォルト | 説明 |
|-----------|--------|-----|----------|------|
| `--project-dir` | `-d` | PATH | `./projects` | プロジェクトベースディレクトリ |
| `--tags` | `-t` | TEXT | なし | タグ（カンマ区切り） |
| `--dimension` | - | FLOAT | なし | 既知の寸法（mm） |
| `--dimension-type` | - | TEXT | なし | 寸法の種類（width/height/depth/diameter） |

**使用例**:

```bash
# 基本的な使用
uv run scan2mesh init --name ball --class-id 0

# タグと既知寸法を指定
uv run scan2mesh init \
  --name robocup_ball \
  --class-id 0 \
  --tags ball,robocup \
  --dimension 220 \
  --dimension-type diameter
```

### scan2mesh plan

プロジェクトの撮影計画を生成します。

**構文**:
```bash
scan2mesh plan PROJECT_DIR [OPTIONS]
```

**引数**:

| 引数 | 型 | 説明 |
|------|-----|------|
| `PROJECT_DIR` | PATH | プロジェクトディレクトリのパス |

**オプション**:

| オプション | 短縮形 | 型 | デフォルト | 説明 |
|-----------|--------|-----|----------|------|
| `--preset` | `-p` | TEXT | `standard` | 撮影プリセット（quick/standard/hard） |

**プリセットの詳細**:

| プリセット | 視点数 | 方位角分割 | 仰角パターン | 最低フレーム数 | 推奨距離 |
|-----------|--------|-----------|------------|--------------|---------|
| `quick` | 16 | 8分割 | 2段階 (0°, 30°) | 12 | 0.4m |
| `standard` | 36 | 12分割 | 3段階 (-15°, 15°, 45°) | 20 | 0.4m |
| `hard` | 48 | 12分割 | 4段階 (-30°, 0°, 30°, 60°) | 30 | 0.35m |

**使用例**:

```bash
# 標準プリセット（推奨）
uv run scan2mesh plan ./projects/robocup_ball

# クイックプリセット（短時間撮影）
uv run scan2mesh plan ./projects/ball --preset quick

# ハードプリセット（複雑な物体）
uv run scan2mesh plan ./projects/complex_object --preset hard
```

### 未実装コマンド

以下のコマンドは現在開発中です（スタブのみ実装）:

| コマンド | 説明 |
|---------|------|
| `scan2mesh capture PROJECT_DIR` | RGBDフレームの取得 |
| `scan2mesh preprocess PROJECT_DIR` | 前処理の実行 |
| `scan2mesh reconstruct PROJECT_DIR` | 3D復元の実行 |
| `scan2mesh optimize PROJECT_DIR` | アセット最適化の実行 |
| `scan2mesh package PROJECT_DIR` | パッケージングの実行 |
| `scan2mesh report PROJECT_DIR` | 品質レポートの生成 |

## プロジェクト構造

### プロジェクトディレクトリ

`scan2mesh init` で作成されるプロジェクトディレクトリの構造:

```
project_name/
├── project.json              # プロジェクト設定
├── capture_plan.json         # 撮影計画（plan実行後）
├── raw_frames/               # 生フレームデータ
├── keyframes/                # キーフレーム
├── masked_frames/            # マスク適用済みフレーム
├── recon/                    # 復元結果
├── asset/                    # 最適化済みアセット
├── metrics/                  # メトリクス
└── logs/                     # ログ
```

### リポジトリ構造

```
scan2mesh/
├── src/scan2mesh/            # メインパッケージ
│   ├── cli/                  # CLIレイヤー
│   │   ├── commands.py       # コマンド実装
│   │   ├── display.py        # 出力表示
│   │   └── validators.py     # 入力検証
│   ├── orchestrator/         # パイプラインオーケストレーター
│   ├── stages/               # 処理ステージ
│   │   ├── init.py           # ✅ ProjectInitializer
│   │   ├── plan.py           # ✅ CapturePlanner
│   │   ├── capture.py        # 🚧 RGBDCapture (stub)
│   │   ├── preprocess.py     # 🚧 Preprocessor (stub)
│   │   ├── reconstruct.py    # 🚧 Reconstructor (stub)
│   │   ├── optimize.py       # 🚧 AssetOptimizer (stub)
│   │   ├── package.py        # 🚧 Packager (stub)
│   │   └── report.py         # 🚧 QualityReporter (stub)
│   ├── services/             # 共通サービス
│   ├── models/               # データモデル (Pydantic)
│   ├── gates/                # 品質ゲート
│   └── utils/                # ユーティリティ
├── tests/                    # テストコード
├── docs/                     # プロジェクトドキュメント
├── pyproject.toml            # プロジェクト設定
└── README.md                 # このファイル
```

## 技術スタック

### 現在使用中

| ライブラリ | バージョン | 用途 |
|----------|-----------|------|
| Typer | 0.12+ | CLIフレームワーク |
| Pydantic | 2.6+ | データモデル・バリデーション |
| Rich | 13.7+ | CLI出力（プログレスバー、テーブル） |
| NumPy | 1.26+ | 数値計算 |
| PyYAML | 6.0+ | 設定ファイル読み込み |

### 将来使用予定（Stage 2以降）

| ライブラリ | 用途 | 必要なステージ |
|----------|------|--------------|
| pyrealsense2 | RealSense制御 | Stage 2 (capture) |
| Open3D | 3D処理（RGBD、TSDF、メッシュ） | Stage 3-5 |
| OpenCV | 画像処理 | Stage 2-3 |
| trimesh | メッシュ操作 | Stage 5 |
| pymeshlab | メッシュ修正 | Stage 5 |
| pygltflib | glTFエクスポート | Stage 6 |

### 開発ツール

| ツール | 用途 |
|-------|------|
| pytest | テストフレームワーク |
| mypy | 型チェック（strict mode） |
| Ruff | リンター・フォーマッター |
| pytest-cov | カバレッジ測定 |

## 開発

### テストの実行

```bash
# すべてのテストを実行
uv run pytest

# カバレッジ付きで実行
uv run pytest --cov=src/scan2mesh --cov-report=term-missing
```

### リント・フォーマット

```bash
# Ruffでリント
uv run ruff check src tests

# 自動修正
uv run ruff check --fix src tests

# フォーマット
uv run ruff format src tests
```

### 型チェック

```bash
# mypyで型チェック（strict mode）
uv run mypy src/scan2mesh
```

### ドキュメント

プロジェクトの設計ドキュメントは `docs/` ディレクトリにあります:

- [プロダクト要求定義書](docs/product-requirements.md)
- [機能設計書](docs/functional-design.md)
- [技術仕様書](docs/architecture.md)
- [リポジトリ構造定義書](docs/repository-structure.md)
- [開発ガイドライン](docs/development-guidelines.md)
- [用語集](docs/glossary.md)

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。
詳細は [LICENSE](LICENSE) ファイルを参照してください。

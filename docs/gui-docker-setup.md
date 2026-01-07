# scan2mesh GUI Docker セットアップガイド

このガイドでは、scan2mesh GUIアプリケーションをDocker環境で実行する方法を説明します。

## 前提条件

以下のソフトウェアがインストールされている必要があります:

| ソフトウェア | 最小バージョン | インストール方法 |
|------------|--------------|----------------|
| Docker | 24.0+ | https://docs.docker.com/get-docker/ |
| Docker Compose | 2.20+ | Dockerに同梱 |

バージョン確認:
```bash
docker --version
docker compose version
```

## クイックスタート

### 1. イメージのビルド

```bash
cd docker
docker compose build scan2mesh-gui
```

### 2. GUIの起動

```bash
docker compose up scan2mesh-gui
```

### 3. ブラウザでアクセス

http://localhost:8501 にアクセスしてGUIを開きます。

### 4. 停止

```bash
docker compose down
```

## 開発モード

ソースコードの変更を自動反映（ホットリロード）したい場合:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up scan2mesh-gui
```

開発モードでは以下が有効になります:
- ソースコードのマウント（変更が即座に反映）
- DEBUGログレベル
- Streamlitのホットリロード

## コマンドリファレンス

### イメージ操作

```bash
# ビルド
docker compose build scan2mesh-gui

# ビルド（キャッシュなし）
docker compose build --no-cache scan2mesh-gui

# イメージ削除
docker rmi scan2mesh:gui
```

### コンテナ操作

```bash
# 起動（フォアグラウンド）
docker compose up scan2mesh-gui

# 起動（バックグラウンド）
docker compose up -d scan2mesh-gui

# ログ確認
docker compose logs scan2mesh-gui

# ログ追跡
docker compose logs -f scan2mesh-gui

# 停止
docker compose down

# コンテナに入る
docker compose exec scan2mesh-gui bash
```

## 環境変数

以下の環境変数でGUIの動作をカスタマイズできます:

| 変数名 | デフォルト値 | 説明 |
|-------|------------|------|
| `SCAN2MESH_LOG_LEVEL` | `INFO` | ログレベル（DEBUG, INFO, WARNING, ERROR） |
| `SCAN2MESH_PROJECT_DIR` | `/workspace/projects` | プロジェクトデータの保存先 |
| `STREAMLIT_SERVER_PORT` | `8501` | Streamlitサーバーのポート |
| `STREAMLIT_SERVER_ADDRESS` | `0.0.0.0` | Streamlitサーバーのバインドアドレス |
| `STREAMLIT_SERVER_HEADLESS` | `true` | ヘッドレスモード（ブラウザ自動起動を無効化） |
| `STREAMLIT_BROWSER_GATHER_USAGE_STATS` | `false` | 使用統計の収集を無効化 |

### 環境変数の変更例

docker-compose.ymlを直接編集するか、環境変数ファイルを使用します:

```bash
# .envファイルを作成
echo "SCAN2MESH_LOG_LEVEL=DEBUG" > docker/.env

# 起動（.envファイルが自動読み込み）
docker compose up scan2mesh-gui
```

## ボリュームマウント

以下のディレクトリがコンテナにマウントされます:

| ホスト側 | コンテナ側 | 権限 | 用途 |
|---------|----------|------|------|
| `./projects` | `/workspace/projects` | 読み書き | プロジェクトデータ |
| `./profiles` | `/workspace/profiles` | 読み書き | プロファイルデータ |
| `./config` | `/workspace/config` | 読み取り専用 | 設定ファイル |
| `./output` | `/workspace/output` | 読み書き | 出力ファイル |

### カスタムボリュームマウント

別のディレクトリをマウントしたい場合:

```bash
docker run -it --rm \
  -p 8501:8501 \
  -v /path/to/your/projects:/workspace/projects \
  -v /path/to/your/profiles:/workspace/profiles \
  scan2mesh:gui
```

## ポートの変更

デフォルトポート8501が使用中の場合、別のポートにマッピングできます:

```bash
# ポート8502でアクセスする場合
docker run -it --rm -p 8502:8501 scan2mesh:gui
```

または、docker-compose.ymlを編集:

```yaml
services:
  scan2mesh-gui:
    ports:
      - "8502:8501"  # ホストポート:コンテナポート
```

## トラブルシューティング

### ポート競合エラー

```
Error response from daemon: ports are not available: exposing port TCP 0.0.0.0:8501
```

**解決策**:
1. ポート8501を使用しているプロセスを確認:
   ```bash
   lsof -i :8501
   ```
2. プロセスを停止するか、別のポートを使用

### パーミッションエラー

```
PermissionError: [Errno 13] Permission denied: '/workspace/projects'
```

**解決策**:
1. ホスト側のディレクトリに書き込み権限があるか確認:
   ```bash
   ls -la projects/
   ```
2. 必要に応じて権限を変更:
   ```bash
   chmod 755 projects/
   ```

### コンテナが起動しない

**確認手順**:
1. ログを確認:
   ```bash
   docker compose logs scan2mesh-gui
   ```
2. コンテナのステータスを確認:
   ```bash
   docker compose ps
   ```
3. ヘルスチェックを確認:
   ```bash
   curl http://localhost:8501/_stcore/health
   ```

### イメージのビルドに失敗

**解決策**:
1. Docker Desktop / Docker Engineが起動しているか確認
2. ディスク容量を確認:
   ```bash
   docker system df
   ```
3. キャッシュをクリアして再ビルド:
   ```bash
   docker system prune
   docker compose build --no-cache scan2mesh-gui
   ```

## セキュリティ

- コンテナは非rootユーザー（`scan2mesh`, UID 1000）で実行されます
- `no-new-privileges` セキュリティオプションが有効です
- デフォルトではローカルホスト（127.0.0.1）からのみアクセス可能です

### 外部ネットワークからのアクセス

外部ネットワークからアクセスを許可する場合は、docker-compose.ymlのポート設定を変更:

```yaml
ports:
  - "0.0.0.0:8501:8501"  # すべてのインターフェースでリッスン
```

**注意**: 本番環境では適切なファイアウォール設定やリバースプロキシを使用してください。

## 関連ドキュメント

- [アーキテクチャ設計書](architecture.md)
- [開発ガイドライン](development-guidelines.md)
- [リポジトリ構造](repository-structure.md)

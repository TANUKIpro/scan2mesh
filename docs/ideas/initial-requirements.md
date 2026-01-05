# アイデアメモ

## 0) ツールの責務

### ツールが提供する価値

* RealSenseで撮るだけで、**学習・シミュ用の3Dアセット**が一定品質でできる
* **再現可能**（同じ入力・設定→同じ出力に近い）
* **品質ゲート**があり「このモデルは使える/危険」が判断できる
* **配布フォーマットが統一**され、次工程（Sim Pack/データ合成）が迷わない

### ツールが“やらない”こと（この段階では）

* 特定シミュレータ向けURDF/SDF/USDのラッパ生成は別工程（Sim Pack）
  ただし、その直前までの **座標系・単位系・衝突メッシュ・LOD・メタ情報**は責務として持つ

---

## 1) 深掘りパイプライン（ステージ/入出力/ゲート）

以下の7ステージに分けると、実装・UX・失敗時の切り戻しが綺麗になります。

### Stage 1: Project Init（案件・対象の定義）

**入力**

* object_name / class_id（例: “robocup_ball”, 0）
* 出力プリセット（canonical座標系、単位、テクスチャ解像度など）
* 任意: 既知の実寸（長辺 mm / 直径など）

**出力**

* project.json（設定と履歴）
* キャプチャ計画（後述）

**ゲート**

* class_idなど必須フィールドが揃っている

---

### Stage 2: Capture Plan（撮影計画の生成）

**目的**：短時間で「足りる」カバレッジを得る。
**仕様案（テンプレ）**

* Quick：水平1周（8–12視点）＋上30°（8視点）＝16–20
* Standard：水平＋上＋下＝24–36
* Hard：遮蔽しやすい形状向け追加（真上/真横の補完）

**出力**

* capture_plan.json（推奨視点数、距離、角度、撮影順）
* UIなら「次にどの角度から撮れ」ガイド

**ゲート**

* 計画に対して最低視点数が満たせる想定（撮影範囲/距離）

---

### Stage 3: Capture（RGBD取得＋品質監視）

**入力**

* RealSenseストリーム（RGB, Depth, intrinsics, depth scale）
* （推奨）撮影モード：

  * 物体固定＋カメラ周回 or ターンテーブル
* （任意）背景条件：単色マット、簡易マーカーなど

**中間出力（重要）**

* raw_frames/（RGB, Depth, timestamp, intrinsics）
* keyframes/（選別後）
* capture_metrics.json（品質指標）

**品質指標（リアルタイムで出したい）**

* Depth valid ratio（深度有効画素比）
* Motion blur proxy（RGB差分やシャープネス）
* Coverage estimate（視点の偏り、未観測方向推定）
* Object occupancy（物体が画面内にいる割合）

**ゲート（自動判定）**

* 深度有効率が低すぎるフレームは除外
* 物体が画面外/ブレ過多は除外
* 計画視点の最低ラインを満たすまで「追加撮影」を促す

> この段階で「撮り直し」を誘導できると、後工程の無駄が激減します。

---

### Stage 4: Preprocess（整流・外れ値除去・マスク）

**目的**：復元の安定化。ここが“速さ”に直結します。

**処理の仕様**

* Depthのフィルタ（穴埋め/外れ値/スムージングは“弱め”が基本）
* RGB-Dアライン
* 背景除去（選択肢を用意）

  * A: 深度閾値＋床平面推定（高速）
  * B: 手動バウンディング/クリック（最小手作業）
  * C: 2Dセグ（将来拡張）

**出力**

* masked_frames/（背景除去済みRGBD）
* mask_quality.json（マスク面積推移、破綻検出）

**ゲート**

* 物体マスクが小さすぎ/途切れすぎの場合はCaptureへ戻す

---

### Stage 5: Reconstruct（姿勢推定→フュージョン→メッシュ化）

ここはアルゴリズム差が出るので、**ツール設計としては“実装差し替え可能”**にするのが吉です（プラグイン構造）。

**サブステップ**

1. Frame-to-frame / frame-to-model で姿勢推定（RGBD odometry系）
2. フュージョン（TSDF等）で統合点群/体素
3. メッシュ抽出
4. テクスチャ生成（UV、アトラス）

**出力（中間含む）**

* recon/tsdf_volume（任意、デバッグ）
* recon/pointcloud.ply
* recon/mesh_raw.glb（or obj）
* recon/recon_report.json（残差、ドリフト、使用フレーム数）

**ゲート（最低限）**

* 追跡破綻（大ジャンプ/残差急増）の検出 → “その区間を破棄” or “撮り直し”
* メッシュの欠損が大きい場合（穴面積やバウンディングの欠落率）→ Captureへ戻す

---

### Stage 6: Asset Optimize（配布・シム向けの整形）

**目的**：学習/シムのどちらにも使える、軽量で破綻しないアセットへ。

**必須処理**

* スケール確定（m単位）

  * 既知実寸がある場合：それでスケール合わせ
  * 無い場合：RealSenseスケールを採用（ただし不確かさをメタデータに記録）
* 軸/原点の正規化（canonical）

  * 例：Z-up、原点=底面中心、+Y前方（など固定）
* メッシュ修正

  * 法線修正、非多様体/穴の軽微修正、孤立片除去
* LOD生成（例）

  * LOD0: 高（~100k tris上限）
  * LOD1: 中（~30k）
  * LOD2: 低（~10k）
* Collision mesh生成

  * まずは **Convex hull**（最速）
  * 可能なら **凸分解**（精度寄りオプション）
* テクスチャ調整

  * 解像度固定（例：2k上限）＋圧縮（png/jpg or KTX2等は要検討）

**出力**

* asset/visual_lod0.glb, visual_lod1.glb, visual_lod2.glb
* asset/collision.obj（またはglb）
* asset/preview.png（サムネ）
* asset/asset_metrics.json（後述）

**ゲート（配布可能判定）**

* 三角形数が上限内
* メッシュが読み込める（glTFバリデーション相当）
* AABB/OBBが妥当（極端に潰れてない）
* テクスチャ欠損なし
* collisionが極端に重くない（凸数/面数上限）

---

### Stage 7: Package（“配布可能な束”へ）

**出力（canonical asset bundle）**

* `object_bundle.zip`（またはフォルダ）
* manifest（メタデータ、再現情報、品質）

**ここが“Sim Pack直前”のゴール**

---

## 2) 配布アセット束の仕様（フォルダ構造とメタデータ）

### フォルダ構造案（例）

```
bundle/
  manifest.json
  README.md
  licenses/
  source/
    capture_plan.json
    project.json
    recon_report.json
    raw_summary.json      # raw全量は別保管でもOK（サイズ対策）
  asset/
    visual_lod0.glb
    visual_lod1.glb
    visual_lod2.glb
    collision.obj
    preview.png
    textures/ ...         # glb内包なら不要
  metrics/
    asset_metrics.json
    capture_metrics.json
```

### manifest.json の最低フィールド案

```json
{
  "schema_version": "1.0",
  "object": {
    "name": "robocup_ball",
    "class_id": 0,
    "tags": ["ball", "robocup"]
  },
  "units": "meter",
  "coordinate_system": {
    "up_axis": "Z",
    "forward_axis": "Y",
    "origin": "bottom_center"
  },
  "scale": {
    "method": "known_dimension|realsense_depth_scale",
    "known_dimension_mm": 220,
    "uncertainty": "low|medium|high"
  },
  "files": {
    "visual": {
      "lod0": "asset/visual_lod0.glb",
      "lod1": "asset/visual_lod1.glb",
      "lod2": "asset/visual_lod2.glb"
    },
    "collision": "asset/collision.obj",
    "preview": "asset/preview.png"
  },
  "quality": {
    "status": "pass|warn|fail",
    "reasons": ["hole_area_high", "scale_uncertain"]
  },
  "provenance": {
    "device": "Intel RealSense ...",
    "tool_version": "scan2asset 0.3.0",
    "date": "2026-01-05",
    "config_hash": "..."
  }
}
```

---

## 3) 品質メトリクス仕様（“使える/危険”を機械判定）

### Capture側メトリクス（例）

* `num_frames_raw / num_keyframes`
* `depth_valid_ratio_mean/min`
* `blur_score_distribution`
* `coverage_score`（視点分布の偏り指標）

### Recon側メトリクス（例）

* `tracking_success_rate`
* `alignment_rmse_mean/max`
* `drift_indicator`（ループ閉じに相当する尺度があれば）

### Asset側メトリクス（配布判定の中心）

* `triangles_lod0/1/2`
* `hole_area_ratio`（穴の割合）
* `non_manifold_edges`（ゼロでなくてもWARN扱いなど）
* `texture_resolution` / 欠損有無
* `aabb_size`（極端値チェック）
* `collision_complexity`（凸数/面数）

**判定ロジック例**

* PASS：学習・シム投入の足切りを満たす
* WARN：学習はOKだがシム衝突が粗い/スケール不確か 等
* FAIL：破綻（ロード不可、極端欠損、スケール崩壊）

---

## 4) ツールI/F（CLIファーストが強い）

ロボカップの現場だと、GUIより「回せるCLI＋必要箇所だけUI」の構成が運用しやすいことが多いです。

### 主要コマンド案

* `scan2asset init --name ... --class-id ...`
* `scan2asset capture --plan quick|standard`
* `scan2asset reconstruct`
* `scan2asset optimize --preset canonical`
* `scan2asset package --out bundle.zip`
* `scan2asset report`（品質結果と次アクション提示）

### 設定ファイル

* `config.yaml` に全パラメータ集約（seed含む）
* すべての出力に config hash を書く（再現性）

---

## 5) “手戻りを最小にする”UX設計ポイント

このスコープのツールは、途中で人が介入できるポイントを絞るほど強いです。

**介入ポイントは3つに限定するのが現実的**

1. Capture中：カバレッジ不足/深度欠損の警告 → 追加撮影
2. Preprocess：背景除去が失敗してるときだけ簡易修正（クリックで範囲指定など）
3. Optimize：原点/軸/スケールが怪しいときだけ手動上書き

それ以外は “自動で進む・失敗したら戻り先が明確” が大事。

---

## 6) 出力フォーマットの推奨（canonical）

Sim Pack直前の中立形式は、基本は **glTF 2.0（.glb）** を推奨にしておくと、次工程がかなり楽になります（多くの環境に渡せる）。
衝突メッシュは単純に `obj` でも良いですが、最終統一はglb内に入れる/別ファイルにする、どちらでもOK。重要なのは **manifestで参照が一意**なこと。

---

## 7) 次の深掘り（ここから“仕様を確定”させるための軸）

この後、仕様を固めるなら「どこを最適化するか」を先に決めると早いです。具体的には：

* **出力プリセット（canonical）**の確定

  * up軸/forward軸/原点/スケール合わせ方
* **品質ゲートの閾値**（tri数上限、穴割合、depth_valid等）
* **対象物の“苦手フラグ”運用**

  * 反射・透明・黒物体などは WARN/FAIL にし、別手段へ逃がす

---

## 次のステップ

1. **このドキュメントのレビュー**
   - 抜けてる視点はないか？
   - 優先順位は妥当か？

2. **PRD（プロダクト要求定義書）の作成**
   - `/setup-project` コマンドで正式なドキュメントを作る
   - このアイデアメモを元に、もっと詳しく具体的にする

3. **プロトタイプを作る**
   - MVP機能だけで最小限のプロトタイプ
   - 実際に使ってフィードバックをもらう

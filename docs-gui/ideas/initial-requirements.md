# アイデアメモ

- 現状のscan2meshを利用し、一連のパイプラインをGUI操作で行うことができるようにしたい。
- UI/UXは/Users/ryo/Documents/workspace/hsr-perception-robocup(プロジェクトページ：https://github.com/TANUKIpro/hsr-perception-robocup)と同様で、統一感のあるものにしたい。
- デバイスの接続確認や撮影テストから始まり、作成したい3Dモデルの登録・修正を行うことができる。
- 最終的には1つの3Dオブジェクトとして出力することが可能
- hsr-perception-robocupと同様にプロファイルを作成することができ、各プロファイルごとに3Dスキャンしたい複数の物体を登録・修正・呼び出し等を行うことができる。
- UI/UXの評価やテスト・エラーの確認については、chrome-devtools-mcpを利用して確認すること。
- 非常に大規模な追加要素であるため、現状のdocs/architecture.md, docs/repository-structure.mdなどとは別にdocs/gui/というディレクトリを作成し、ここで.claude/commands/setup-project.mdの内容を実行するようなイメージで運用したい。
- gpuが無いPCでも動作でき、dockerで環境を汚さないように実装したい。
- /add-featureコマンドにて、最初に内容がcuiかguiかを推測し、曖昧な場合は必ず確認を取るように.claude以下の必要ファイルへ記述を追加すること。

# 最初に行うこと
- /setup-projectを実行し、docs-guiの充足を行う
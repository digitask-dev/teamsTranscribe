# teamsTranscribe

こちらもご覧ください。[README.md](README.md)(英語版)

`teamsTranscribe` はマイク入力およびシステム音声をリアルタイムにテキスト化し、常に前面表示されるオーバーレイウィンドウに字幕として表示する Python デスクトップユーティリティです。PyAudio による音声取得、faster-whisper による高品質音声認識、PyQt ベースの UI を組み合わせ、Microsoft Teams や Zoom、ブラウザ会議などの上に字幕を重ねられます。

> **Proof of concept:** 本プロジェクトは評価・検証を目的とした試作段階であり、本番運用を想定した十分なハードニングは行われていません。

## 主な機能
- 低遅延ストリーミングによるリアルタイム文字起こし
- マイクのみ・システム音声のみ・両方のミックスを選択可能
- ドラッグで移動でき、ステータスパネルを切り替えられる常時最前面オーバーレイウィンドウ
- 設定ファイルまたは環境変数で上書きできる自動言語検出
- コマンドライン引数でキャプチャモードやデバイス一覧を制御

## 前提条件
- Windows 10/11（WASAPI ループバックが標準対応）※ macOS / Linux でも PortAudio 対応のループバックデバイスがあれば利用可能
- Python 3.9 以上
- Git（任意、リポジトリをクローンする場合）
- Windows の場合: Visual C++ 14 以上（PyAudio ホイールに必要）
- Linux/macOS の場合: PortAudio 開発ヘッダー（PyAudio をソースからビルドする際）
- システム音声を取得したい場合は仮想ループバックデバイス（例: VB-Audio Virtual Cable）

## セットアップ手順
1. リポジトリをクローン、または ZIP を展開してプロジェクトルートに移動:
   `powershell
   git clone https://github.com/yourusername/teamsTranscribe.git
   cd teamsTranscribe
   `
2. （推奨）仮想環境を作成して有効化:
   `powershell
   python -m venv .venv
   .\\.venv\\Scripts\\Activate.ps1
   `
3. 依存パッケージをインストール:
   `powershell
   pip install --upgrade pip
   pip install -r requirements.txt
   `
   - GPU で高速化したい場合は、faster-whisper の公式手順に従って CUDA 対応ホイールを導入してください。
4. `config/settings.json` の設定ファイルを開き、必要に応じて値を変更してください:
   ```json
   {
     "whisper_model_path": "base",
     "whisper_compute_type": "int8",
     "whisper_language": "auto",
     "whisper_window_seconds": 5,
     "whisper_overlap_seconds": 1,
     "whisper_beam_size": 1
   }
   ```
   - `whisper_model_path`: 利用する faster-whisper モデル名またはローカルパス（例: `base`, `medium`, `large-v3`）
   - `whisper_compute_type`: CPU/GPU に合わせた計算精度（`int8`, `float16` など）
   - `whisper_language`: `auto` で自動検出、固定する場合は言語コード（例: `ja`, `en`）
   - `whisper_window_seconds` / `whisper_overlap_seconds`: ストリーミング窓と重なりの秒数
   - `whisper_beam_size`: ビーム幅。値を大きくすると精度は上がりますが速度は低下します。
   - 大文字表記の環境変数（例: `WHISPER_MODEL_PATH`）を設定すると、このファイルより優先されます。
   - 複数のプロファイルを切り替える場合は、環境変数 `TEAMS_TRANSCRIBE_CONFIG` で別の設定ファイルを指定できます。
既存の `.env` も自動で読み込まれるため、従来の上書き方法もそのまま使えます。

## CLI からの設定管理
JSON を直接編集せずに設定を確認・更新するには `config` サブコマンドを利用します:

```powershell
python -m src.main config --list
python -m src.main config --set whisper_model_path=medium --set whisper_language=en
```

キー名は大文字小文字を区別せず、`WHISPER_MODEL_PATH` や `whisper_model_path` の表記をそのまま指定できます。`--config-path` を付けると `config` コマンドと本体の起動の両方で別の設定ファイルを読み込めます:

```powershell
python -m src.main config --config-path C:\path\to\custom.json --list
python -m src.main --config-path C:\path\to\custom.json
```

## 実行方法
- 起動前に利用可能な音声デバイスを確認:
  `powershell
  python -m src.main --list-devices
  `
  ループバックデバイスや仮想ケーブルが表示されるかを確認してください。
- 標準モード（マイクとシステム音声を自動ミックス）:
  `powershell
  python -m src.main
  `
- マイクのみ:
  `powershell
  python -m src.main --mic-only
  `
- システム音声のみ（ループバック必須。見つからない場合はマイクにフォールバック）:
  `powershell
  python -m src.main --system-only
  `

起動中はオーバーレイウィンドウが他アプリの前面に表示されます。ドラッグで位置を変更でき、切り替え矢印でモデルや言語などのステータスを表示し、X ボタンで終了します。端末には使用中のデバイス情報や VAD（音声区間検出）に関するログが出力されます。

## ビルド / インストール
- 開発向けの編集可能インストール:
  `powershell
  pip install -e .
  `
- 配布用にホイール / sdist を生成（初回のみ `pip install build` が必要）:
  `powershell
  python -m build
  `
  生成物は dist/ 配下に出力され、別環境では `pip install dist/teamsTranscribe-<version>-py3-none-any.whl` のようにインストールできます。

## トラブルシューティング
- **PyAudio がインストールできない**: Windows では Visual C++ Build Tools を導入。Linux/macOS では PortAudio ヘッダーを追加後に再試行。
- **システム音声が取得できない**: オーディオドライバーが WASAPI ループバックを提供しているか確認。提供が無い場合は仮想オーディオケーブルを導入。
- **文字起こしが遅い**: モデルを小さくする（`tiny`, `base`）かビーム幅を縮小。もしくは GPU 用 faster-whisper を利用。
- **オーバーレイが表示されない**: PyQt はデスクトップセッションが必要。ヘッドレス環境でないこと、`QT_QPA_PLATFORM` が適切 (`windows`, `xcb` 等) であることを確認。

## ライセンス
本プロジェクトは `GNU Affero General Public License v3.0 (AGPL-3.0)` の下で公開されています。ネットワーク経由で提供する場合も含め、ソースコードを同じ条件で公開する必要があります。






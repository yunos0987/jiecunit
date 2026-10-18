# JiecUnit Rules for AI Agents

JiecUnit は、IEC 61131-3 ST 言語向けの単体テストフレームワークです。コーディング規約・バージョン管理の詳細は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。ここには重複して書きません。

## ファイルの形式

- 文字コードは UTF-8 BOM なし、改行コードは LF とする。`.bat` ファイルを追加する場合だけ CRLF とする（現在、`.bat` はない）。
- バッチ処理で文字列を置換するときは、置換元のファイルの文字コードに注意する。
- IEC 61131-3 のキーワードはすべて小文字とする（例: `if` / `var` / `and`）。
- コーディング規約（命名規則・インデント・テストの書き方など）は [CONTRIBUTING.md](CONTRIBUTING.md#コーディング規約) に従う。

## テスト

- 変更後は、リポジトリルートで `python scripts/run_tests.py` を実行し、`All checks passed.` と表示されることを確認する。全ターゲットのコンパイル確認、jier（`jiecc --run`）によるテスト実行、メッセージ引数省略形と `_MSG` 形の展開結果の一致検証を一度に行う。
- jiecc は、`--jiecc PATH`、環境変数 `JIECC`、`PATH` 上の `jiecc` の順に探す。
- `jiecc --run` の終了コードは、テストの失敗を反映しない。テストの合否は標準出力の集計行から判定する（`scripts/run_tests.py` が行う）。
- `jiecc` の終了コードが 0 でも、標準エラー出力に `error:` の行があれば失敗とみなす。手動でコンパイルや実行をした場合も、この行を確認する。
- マクロ展開の一致検証だけを実行する場合は `python scripts/check_macro_expansion.py` を使う。

## バージョン

- `VERSION` と、`src/jiecunit_config.iec` の 3 個のマクロ（`_JIECUNIT_FULL_VER`・`_JIECUNIT_VER`・`_JIECUNIT_VERSION`）は、リリース時に `release vX.Y.Z` という独立したコミットで更新する。機能追加・修正のコミットでは更新しない。手順は [CONTRIBUTING.md](CONTRIBUTING.md#バージョン管理) を参照する。

## 既知の落とし穴

- `//` で始まるコメント行の最初の語が `{#` の場合（例: `//   {#define NAME(...)`）、jiepp はそれをディレクティブとして解釈する。Jiecc 8.0.0（jiepp 1.0.0）ではエラー（PP30）になる。コメントの中にディレクティブの例を書くときは、`{` を付けない（`#define NAME(...)`）。
- jier（`jiecc --run`）は、関数を呼び出す位置より前にその関数が定義されている必要がある。後ろで定義した関数を呼ぶと `UNDEFINED_SYMBOL` になる。定義の順序を入れ替えて対処する。前方宣言は、PLC メーカーの環境が対応していないので使わない。
- `(*{doc ...}*)` プラグマの中にアポストロフィ（`'`）を書くと、jiepp が警告（PP29）を出す。アポストロフィを使わない言い回しにするか、`$27` と書く。

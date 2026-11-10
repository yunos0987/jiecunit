# JiecUnit Rules for AI Agents

JiecUnit は、IEC 61131-3 ST 言語向けの単体テストフレームワークです。コーディング規約・バージョン管理の詳細は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。ここには重複して書きません。

## ファイルの形式

- 文字コードは UTF-8 BOM なし、改行コードは LF とする。`.bat` ファイルを追加する場合だけ CRLF とする（現在、`.bat` はない）。
- バッチ処理で文字列を置換するときは、置換元のファイルの文字コードに注意する。
- IEC 61131-3 のキーワードはすべて小文字とする（例: `if` / `var` / `and`）。
- コーディング規約（命名規則・インデント・テストの書き方など）は [CONTRIBUTING.md](CONTRIBUTING.md#コーディング規約) に従う。

## テスト

- 変更後は、リポジトリルートで `python scripts/run_tests.py` を実行し、`All checks passed.` と表示されることを確認する。全ターゲットのコンパイル確認、jier（`jiecc --run`）によるテスト実行、メッセージ引数省略形と `_MSG` 形の展開結果の一致検証（式のテキストの順序を含む）、`test/golden` のゴールデン出力の比較と JUnit 変換の自己テストを一度に行う。
- 失敗の出力やランナーの挙動を変えたときは、`python scripts/check_golden.py --update <ケース>` で期待値を作り直し、`git diff test/golden` で差分が意図どおりか確かめてからコミットする。ケースの 1 行目の `// golden-args:` に書いた引数を jiecc に渡す（`-Wno-error` は jiecc に渡さず、既定の `-Werror` を外す。`--allow-narrowing` と併用する）。新しい挙動には、`test/golden/` にケースを足す（失敗するテストの出力は、`test/test.iec` ではなくゴールデンか `EXPECT_NONFATAL_FAILURE` で確かめる）。
- jiecc は、`--jiecc PATH`、環境変数 `JIECC`、`PATH` 上の `jiecc` の順に探す。
- `jiecc --run` の終了コードはテストの結果を反映する（`JiecUnitMain` が集計の後に `halt` を呼ぶ。全テスト合格なら 0、失敗か登録時の致命的エラーなら 1）。テストの合否は標準出力の集計行から判定し、加えて `jiecc --run` の終了コードが 0 以外なら失敗とする（`scripts/run_tests.py` が行う）。必要な Jiecc は 9.4.0 以降（`src/jiecunit_config.iec` の `{#error}`）。
- `jiecc` の終了コードが 0 でも、標準エラー出力に `error:` の行があれば失敗とみなす。手動でコンパイルや実行をした場合も、この行を確認する。
- マクロ展開の一致検証だけを実行する場合は `python scripts/check_macro_expansion.py` を使う。

## バージョン

- `VERSION` と、`src/jiecunit_config.iec` の 3 個のマクロ（`_JIECUNIT_FULL_VER`・`_JIECUNIT_VER`・`_JIECUNIT_VERSION`）は、リリース時に `release vX.Y.Z` という独立したコミットで更新する。機能追加・修正のコミットでは更新しない。手順は [CONTRIBUTING.md](CONTRIBUTING.md#バージョン管理) を参照する。

## 既知の落とし穴

- `//` で始まるコメント行の最初の語が `{#` の場合（例: `//   {#define NAME(...)`）、jiepp はそれをディレクティブとして解釈する。Jiecc 8.0.0（jiepp 1.0.0）ではエラー（PP30）になる。コメントの中にディレクティブの例を書くときは、`{` を付けない（`#define NAME(...)`）。
- jier（`jiecc --run`）は 1 秒に 50 サイクル程度しか実行できない。サイクル数の多いテストやゴールデンは、`SET_TEST_MAX_CYCLES` や `--max-cycles` で短くする。
- jier（`jiecc --run`）は、関数を呼び出す位置より前にその関数が定義されている必要がある。後ろで定義した関数を呼ぶと `UNDEFINED_SYMBOL` になる。定義の順序を入れ替えて対処する。前方宣言は、PLC メーカーの環境が対応していないので使わない。
- Jiecc 9.2.0 以降では、POU の本体直下に ST の文を `{st}` / `{end}` なしで書く。POU の見出し（名前・戻り型など）の直後の行が `(`、`[`、`+`、`-`、文字列リテラルで始まる文だと、見出しの続きとして読まれる。その場合は、見出しの末尾に `;` を付ける。
- POU の本体直下では、宣言は書いた位置から有効になる。文の後ろで `var` を宣言した変数を、その文より前で使うと `UNDEFINED_SYMBOL` になる。pragma、`var` ブロック、入れ子の定義は、文のまとまりの区切りになる。
- `(*{doc ...}*)` プラグマの中にアポストロフィ（`'`）を書くと、jiepp が警告（PP29）を出す。アポストロフィを使わない言い回しにするか、`$27` と書く。
- 関数形式マクロの本体に書いた doc プラグマ（`(*${doc ...$}*)`）の中では、マクロの仮引数が置換されない。型名などを doc の文面に入れたくても入らないので、仮引数に依存しない文面にする（例: `src/jiectest_validate_common.iec`）。
- 関数形式マクロの仮引数名は、本体の名前付き引数の左辺（`name:=` の `name`）も置き換える。仮引数名は、本体で使う引数名と重ならない名前（末尾に `_` を付けるなど）にする。
- 実引数は、別のマクロに渡すと先に展開される。そのため、入れ子のマクロの中で `@x` を使うと、ソースどおりの式ではなく展開後のテキストになる。ソースどおりの式が要るときは、利用者が呼ぶマクロ自身で `@` を使う（`jiecunit.iec` の `_JIECUNIT_TEXT(@arg)`）。
- `{#error}` の本文の中のマクロ名は展開される。`{#error}` の文面には、マクロ名を書かない。
- ST の `and` / `or` は短絡評価しない。`(i < n) and (a[i] = b[i])` のような条件は、範囲外の要素を読む。ループの中の `if` と `exit` で書く。
- 配列の宣言で、上限にマクロの式を書く（`array[0..N - 1]`）と、XML に式のまま（`upper="8-1"`）出る。要素数で書く（`array[N]`）と数値（`upper="7"`）になる。jier はどちらも実行できるので、テストでは気付かない。
- OMRON の `string[N]` は終端を含むので、N - 1 バイトしか入らない。1 文字用の変数でも余裕を持たせる（`sys/sys.iec` の `jiec_quote`）。jier は長さを検査しない。
- jier の `abs()` は、NaN に 0.0 を返す。`0.0 / 0.0` は DIVISION_BY_ZERO で止まる（NaN は `inf - inf` で作る）。NaN の判定には `x <> x` を使う。
- jiepp（1.2.0 / 1.4.0）の `{#if}` で `X and (...)` や `defined(X) and (...)` と書くと、`X` が未定義のとき型エラー（PP50）になる。`{#ifdef X}` か、`defined(X) && (...)`（jiepp 1.4.0 = Jiecc 9.4.0 以降で使える。`and` ではなく `&&`）を使う。

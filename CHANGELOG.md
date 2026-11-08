# 変更履歴 / Changelog

5.0.0 以降の変更を記録します。それ以前の変更は、Git の履歴と GitHub の Pull Request（https://github.com/yunos0987/jiecunit）を参照してください。

## 未リリース / Unreleased

### 互換性に影響する変更 / Breaking changes

- 必要な Jiecc を 9.2.0 以降から 9.4.0 以降に変更しました。Jiecc 9.4.0 未満では、`src/jiecunit_config.iec` の `{#error}` で前処理が止まります（`JiecUnit requires Jiecc 9.4.0 or later.`）。`jiecc --run`（jier）の `halt` と、Jiecc 9.4.0 から `jiecc` が受け付ける `-Wundef` を前提にするためです。

### 不具合の修正 / Bug fixes

- CODESYS ターゲットで、時間型の比較検証関数が `JiecTest_validate<CMP>_ltime` という名前で生成され、呼び出し側の `JiecTest_validate<CMP>_TIME`（`EXPECT_EQ_TIME` などの展開結果）と一致していませんでした。`sys/sys_conv.iec` が CODESYS 向けに `TIME` を `ltime` と定義しているため、関数名を組み立てるときに `TIME` が先に置換されていたものです。関数名を `*_TIME` に直しました。CODESYS 以外のターゲットの出力は変わりません。
- MITSUBISHI ターゲットで、時間型の大小比較の検証関数（`JiecTest_validate{LT,LE,GE,GT}_TIME`）が、`sys/sys_conv.iec` に無い `time_to_string_sec` を呼ぶ形で生成されていました（GX Works3 でビルドエラーになります）。MITSUBISHI ではこれらを生成しないようにしました。
- 対応していないターゲットで時間型のアサーションを使ったとき（KEYENCE / MITSUBISHI の `EXPECT_EQ_TIME` / `EXPECT_NE_TIME` 系、MITSUBISHI の `EXPECT_LT_TIME` / `EXPECT_LE_TIME` / `EXPECT_GE_TIME` / `EXPECT_GT_TIME` 系と `ASSERT_*` 版）、従来は未定義関数の呼び出しを含む XML が黙って生成されていました。前処理の時点で `not supported on this target` のエラー（jiepp の `__error`）になるようにしました。

### 新機能 / New features

- `jiecc --run`（jier）では、`JiecUnitMain` が集計を表示した時点で Jiecc の `halt` を呼んでスキャンループを止めます。プロセスは `--max-cycles` を待たずに終わり、終了コードがテストの結果を反映します（全テスト合格なら 0、失敗があるか登録時の致命的エラーなら 1）。`scripts/run_tests.py` は従来どおり標準出力の集計行で判定し、加えて終了コードも見ます（下記）。実 PLC のターゲットでは従来どおり（`done` フラグでスキャンごとに `return`）。
- `scripts/run_tests.py` の compile フェーズを並列に実行します。同時に動かす `jiecc` の数は `--jobs N` で 1〜4 の範囲で指定でき、既定は 4 です（5 以上は指定できません）。run フェーズと macro-check フェーズは従来どおり 1 本ずつ実行します。出力の表の形式と既存のオプションは変わりません。
- `scripts/run_tests.py` は、compile と run の `jiecc` に `-Werror` と `-Wundef` を付けます。警告が出るとそのスイートは失敗になります。
- `scripts/run_tests.py` の run フェーズは、標準出力の集計行に加えて `jiecc --run` の終了コードも見て、0 以外なら失敗にします。

### その他 / Other

- 互換性に影響しない内部の変更です。公開マクロの名前と引数、関数名、失敗時の出力、生成される IEC 61131-10 XML（空白の違いを除く）は変わりません。
  - 比較の検証関数 `JiecTest_validate<CMP>_<DATATYPE>` を、テンプレートファイルを型ごとに `{#include}` する方式から、関数の定義全体に展開する関数形式マクロで生成する方式に変えました。`src/jiectest_validate_cmp_template.iec`・`src/jiectest_validate_eq_template.iec`・`src/jiectest_validate_ne_template.iec` を削除し、`src/jiectest_validate_common.iec` を追加しました。
  - 省略可能なメッセージ引数を振り分ける内部マクロを、必須引数の個数ごとの 4 系統から 1 系統（`_JIECUNIT_OPTMSG_N`）にまとめました。必須引数より後ろの余分な引数が 17 個以上あるとき、`jiecc --run` の `UNDEFINED_SYMBOL` に出る内部シンボル名が `_JIECUNIT_OPTMSG2_18` のような名前から `_JIECUNIT_OPTMSG_18` のような名前に変わります。
  - `src/jiecunit_core.iec` と `sys/sys.iec` の `{#if _JIER}` を `{#ifdef _JIER}` に変えました。`-Wundef` を付けても、jier 以外のターゲットで `_JIER` が未定義である旨の警告（`PP54`）が出ません。

## 6.0.0 (2026-11-01)

5.0.0 からの変更です。

### 互換性に影響する変更 / Breaking changes

- 必要な Jiecc を 8.0.0 以降から 9.2.0 以降に変更しました。Jiecc 9.2.0 では、POU の本体直下に ST の文を直接書けるようになったため、`{st}` / `{end}`（マクロ定義内のものを含む）の囲みを、`src/`・`sys/`・`test/`・`samples/` のすべてのソースとマクロから取り除きました。JiecUnit を使うコードも、`{st}` / `{end}` は不要です。
- Jiecc 9.2.0 未満では、`src/jiecunit_config.iec` の `{#error}` で前処理が止まります（`JiecUnit requires Jiecc 9.2.0 or later.`）。

## 5.0.0 (2026-10-18)

4.2.0 からの変更です。

### 互換性に影響する変更 / Breaking changes

- 必要な Jiecc を 5.14 以降から 8.0.0 以降に変更しました。Jiecc 8.0.0 に同梱されている jiepp 1.0.0 は、前処理でエラーが出ると後続の処理を行いません。5.0.0 は、この動作に合わせて修正してあります（「不具合の修正」を参照）。`scripts/run_tests.py` と `jiecc --run`（jier インタプリタ）による実行も、Jiecc 8.0.0 以降を使います。
- 公開アサーションマクロ（`EXPECT_EQ_INT(expected, actual, ...)` など 288 個）の必須引数に名前が付きました。引数の個数を間違えたときの検出のされ方が、足りない場合（プリプロセッサの `PP34`）、多すぎる場合（`JIECUNIT_ASSERTION_TAKES_<lo>_OR_<hi>_ARGUMENTS`）、0 個の場合（`INVALID_SYNTAX`）、必須引数より後ろの余分な引数が 17 個以上の場合（`jiecc --run` の `UNDEFINED_SYMBOL` のみ）で変わりました。詳細は README.md を参照してください。`FAIL` と `ADD_FAILURE` は必須引数がないため、`(...)` のままです。
- `EXPECT_GE`・`EXPECT_GT`・`EXPECT_LE`・`EXPECT_LT` 系の比較が失敗したときのメッセージが、`Expected: lhs <op> rhs` / `Actual: <lval> vs <rval>` の形式に変わりました。従来は、等価比較と同じ書き方で同じ値を 2 回表示していました。
- `JiecUnitMain` が、テスト開始時に `[========] Running N tests.` を表示し、実行結果にスキップ数（`[ SKIPPED]`）を加えるようになりました。出力を解析しているツールに影響することがあります。

### 新機能 / New features

- すべてのアサーションマクロで、末尾にメッセージ引数を渡せるようになりました（`_MSG` 形を使わずに書けます）。`_MSG` 形は、後方互換性のために非推奨の別名として残してあります。
- `FAIL(message)`・`ADD_FAILURE(message)` を追加しました。メッセージの有無で 0 引数形と 1 引数形を切り替えます。
- `SKIP_TEST(reason)` を追加しました。テストが自分自身をスキップできます。スキップしたテストは、実行結果に `[ SKIPPED]` と表示されます。
- `EXPECT_NEAR_REL`・`ASSERT_NEAR_REL`（`_MSG` 形を含む）を追加しました。相対誤差で比較します。
- 引数の個数を間違えると、`JIECUNIT_ASSERTION_TAKES_<lo>_OR_<hi>_ARGUMENTS` という名前のマクロでコンパイルエラーになります。間違いの箇所が呼び出し側で分かります。
- `scripts/run_tests.py` を追加しました。`test/test.iec` と `samples/sample.iec` を、OMRON・KEYENCE・CODESYS・MITSUBISHI・STD の各ターゲットでコンパイルし、jier インタプリタ（`jiecc --run`）で実行して合否を判定します。`jiecc` の終了コードはテストの失敗を反映しないため、標準出力の集計行を解析します。標準エラー出力の `error:` の行も失敗として扱います。
- `scripts/check_macro_expansion.py` を追加しました。メッセージ引数を省略した形と `_MSG` 形の展開結果が一致することと、`__LINE__` が呼び出し元の行に展開されること、引数の個数が誤った呼び出しがコンパイルエラーになることを検証します。`scripts/run_tests.py` が実行します（`--skip-macro-check` で省略できます）。

### 不具合の修正 / Bug fixes

- Jiecc 8.0.0（jiepp 1.0.0）で、`scripts/run_tests.py` のすべての段階が失敗する問題を、次の 3 点で修正しました。
  - `jiecunit.iec` のコメント行 `//   {#define NAME(...)` を、jiepp がディレクティブとして読んでいました。`#define NAME(...)` の形に書き換えました。
  - `src/jiecunit_jiectest.iec` で、`JiecTest_currentCycle` を、それを呼び出す `JiecTest_failure` より前に定義するようにしました。jier は、後ろで定義した関数の呼び出しを `UNDEFINED_SYMBOL` と報告します。関数の本体は変えていません。
  - `src/jiectest_validate_near_rel.iec` の doc コメントからアポストロフィを除きました（jiepp の `PP29` の警告を避けるためです）。
- `GE`・`GT`・`LE`・`LT` 系の失敗メッセージで、同じ値を等価比較の書き方で 2 回表示していた問題を修正しました（上の「互換性に影響する変更」を参照）。
- `samples/sample_pous.iec` の `mean()` に、`sample_size <= 0` のとき 0.0 を返すガードを追加しました。0 除算の挙動がメーカーによって異なるためです。

### その他 / Other

- `scripts/generate_macros.py` と `src/jiectest_validate_{ge,gt,le,lt}.iec` の改行コードを、CRLF から LF に統一しました。
- `.gitignore` に `__pycache__/` と `*.pyc` を追加しました。
- `sys/sys_conv.iec` に、`_JIER` が `time_to_usec_dint`・`date_to_string` などを、`_CODESYS` が `DATE_TO_STRING` などを標準で提供するため、`Unsupported` のスタブを追加しないことを注記しました。
- `test/` に、`EXPECT_NEAR_REL`・メッセージ引数・`SKIP_TEST` のテストを追加しました。
- README.md を、新しい API と Jiecc 8.0.0 の動作に合わせて更新しました。

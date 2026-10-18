# 変更履歴 / Changelog

5.0.0 以降の変更を記録します。それ以前の変更は、Git の履歴と GitHub の Pull Request（https://github.com/yunos0987/jiecunit）を参照してください。

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

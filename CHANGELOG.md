# 変更履歴 / Changelog

5.0.0 以降の変更を記録します。それ以前の変更は、Git の履歴と GitHub の Pull Request（https://github.com/yunos0987/jiecunit）を参照してください。

## Unreleased

7.0.0 からの変更です。

### 互換性に影響する変更 / Breaking changes

- `JiecTest_t` のフィールドを変えました。`tmp_is_test_available` を削除し、`tmp_is_active`・`tmp_exec_count`・`tmp_is_single_cycle`・`tmp_max_cycles`・`tmp_test_file`・`tmp_test_line` を追加しました。ほかに、テストごとの致命的・非致命的な失敗の数、失敗の捕捉、表示名、TearDown の待ちのフィールドも追加しました。テストが動いているかどうかは `tmp_is_active` で表し、`JiecTest_deactivate` はサイクル数（`tmp_cycle`）を変えません（従来は `DINT` の最小値にしていました）。初期化直後の `tmp_cycle` は 0 です。`JiecTest_nextCycle` は、テストが動いていないときと上限に達したときはサイクル数を変えません。
- 時計の無いターゲット（jier・CODESYS・MITSUBISHI）では、所要時間を `(0us)` ではなく `(n/a)` と表示します。
- 失敗の出力を Google Test の形式に変えました。出力を解析しているツールに影響します。
  - 位置の行を詳細より先に出し、`<ファイル>:<行>: Failure` の形にしました（従来は詳細の後に `<テスト名>:<行>@<サイクル>`）。ファイルは `__FILE__`（jiecc に渡した、またはインクルードに書いたパス）です。複数サイクルのテスト（`TEST_M`）では末尾に ` (cycle N)` を付けます。
  - 値だけでなく、テストに書いた式のテキストも出します。等値は `Expected equality of these values:` に続けて式ごとに `  <式>` と `    Which is: <値>`（式と値の表示が同じリテラルのときは省略）、不等と大小は `Expected: (<式1>) <op> (<式2>), actual: <値1> vs <値2>`、`EXPECT_TRUE`/`EXPECT_FALSE` は `Value of: <式>` / `  Actual: <値>` / `Expected: <値>`、`EXPECT_NEAR`/`EXPECT_NEAR_REL` は `The difference between ... which exceeds ..., where` と各式の値、`FAIL`/`ADD_FAILURE` は `Failed` です。メッセージは最後の行に出します。
  - STRING の値は `'...'` で囲み、`'` と `$` を ST のリテラルと同じく `$'`・`$$` と書きます（末尾の空白などの違いが見えます）。
  - 検証関数（`JiecTest_validate*`）に、式のテキストを受け取る省略可能な入力（`expected_text` など）を追加しました。位置引数（informal call）で呼んでいるコードは、引数を追加する必要があります。`EXPECT_TRUE`/`EXPECT_FALSE` は新しい `JiecTest_validateBOOL` を使います。
  - 式のテキストは公開マクロの中で文字列化するので、マクロを引数に書くと、展開後の値ではなく書いたとおりの名前が出ます。`JIECUNIT_NO_EXPRESSION_TEXT` を定義すると、式のテキストを渡しません（PLC のメモリとスキャン時間を減らすとき）。
- `*_REAL` / `*_FLOAT` のアサーション（`EXPECT_EQ_REAL`・`EXPECT_NE_FLOAT`・`EXPECT_LT_REAL` など、`ASSERT_*` と `_MSG` 形を含む 48 個）は、値を LREAL に広げずに REAL のまま比べます。従来は LREAL に広げていたので、`r: real := 0.1` を `EXPECT_EQ_REAL(0.1, r)` と比べると失敗していました（`0.1` と `0.10000000149011612`）。LREAL の値を渡しているコードは、`*_LREAL` / `*_DOUBLE` か `EXPECT_DOUBLE_EQ` に変えてください。jier はこの縮小を型エラーにしますが、ベンダーによっては黙って REAL に丸めて比べます。`*_LREAL` / `*_DOUBLE` は従来どおり LREAL で比べます。
- `[ RUN    ]` の行は、JiecUnitMain ではなくテストプログラムが最初に実行されたときに出します（タスクに割り付けられていないテストでは、従来どおり JiecUnitMain が `[  ERROR ]` の前に出します。表示名はテストプログラムが実行されて初めて分かるので、この場合はプログラム名で表示します）。`JiecTest_enterTest` は、テストの最初の実行で true を返します。
- `TEST_S` / `TEST_M` の外（ヘルパーの関数・FB・プログラム）でアサーションを使うときは、その POU の宣言に `JIECUNIT_DECLARE_HELPER();` を書く必要があります。アサーションが参照する変数 `jiecunit_in_helper` を宣言するためです（従来は `TestName` と `g_jiectest` の宣言が要り、事実上ヘルパーでは使えませんでした）。
- `_JIEC_TESTNAMES_LIST_` は、グローバル変数 `g_jiecunit_result` と `g_jiecunit_rerun` も宣言します。構成（configuration）を手で書いているときは、この 2 つを宣言に加えてください（JiecUnitMain が `var_external` で参照します）。
- `DEFINE_CONFIGURATION(_JIEC_TESTNAMES_LIST_(...))` は、すべての `TEST_S` / `TEST_M` の定義の**後ろ**に置く必要があります。前処理の時点で、定義の数と一覧の名前の数を比べるためです（新機能を参照）。従来の `samples/sample.iec` のように一覧を定義より前に置いていると、前処理がエラー（`PP91`）で止まります。一覧を定義の後ろへ移すか、`JIECUNIT_NO_TEST_COUNT_CHECK` を定義して照合を止めてください。

### 不具合の修正 / Bug fixes

- 失敗した後に `SKIP_TEST` したテストが `[ SKIPPED]` と表示され、失敗の一覧にも載りませんでした（失敗がそれだけなら `[ FAILED ] 0 tests, listed below.` と出て終了コード 1）。失敗を優先して `[ FAILED ]` と表示するようにしました。
- `EOT()` を呼ばない `TEST_M` や、本体の途中で `return` した `TEST_S` は、終わらずに後続のテストと集計が実行されませんでした。`TEST_S` は最初のサイクルの終わりで終了します（GTest の `return` と同じ）。`TEST_M` は `JIECUNIT_MAX_CYCLES_PER_TEST` サイクル実行してもまだ終わっていなければ失敗として記録され、次のテストへ進みます。既定値は 100000 で、1 秒に 50 サイクル程度しか実行できない jier では 1000 です。0 以下なら無制限です。サイクル数があふれたときも失敗にします。
- テストが 1 つも無いとき、`[========] Running 0 tests.` の後に何も起きず、jier では `--max-cycles` まで止まりませんでした。空の集計を出して終了します（終了コード 0。Google Test と同じ）。
- 複数サイクルのテストの所要時間が、サイクルごとに「テスト開始からの経過時間」を足していたため、二乗で大きくなっていました。
- オムロン・キーエンスの所要時間が、100ns 単位のカウンタを `/100/1000`（10ms 単位）で換算していました。`/10`（us 単位）に直し、カウンタの差を元の型で取ってから換算するようにしました（カウンタが一巡しても正しい差になります）。
- テストが終わった後（ヘルパーの中の ASSERT の後など）の失敗の位置が `@-2147483648` と表示されていました。
- `EXPECT_NEAR`・`EXPECT_NEAR_REL` に NaN を渡したとき、jier では成功していました（jier の `abs` は NaN に 0.0 を返します）。NaN は明示的に判定して失敗にし、`A NaN is never near any value.` と出します。同じ値（同符号の無限大どうしを含む）は、差を計算せずに近いとみなします。`EXPECT_NEAR` は、Google Test と同じく、差が許容値以内なら近いとみなします（`EXPECT_NEAR(inf, 1.0, inf)` は成功します）。`EXPECT_NEAR_REL` は、差と許容値がどちらも有限のときだけ近いとみなします（`EXPECT_NEAR_REL(inf, 1.0, 0.1)` は、許容値も無限大になりますが失敗します）。

### 新機能 / New features

- `JIECUNIT_MANUAL_START` を定義すると、`g_jiecunit_rerun` を true にするまでテストを始めません（既定では、運転にするとすぐに始めます）。
- `EXPECT_DOUBLE_EQ`・`ASSERT_DOUBLE_EQ`（LREAL）と `EXPECT_FLOAT_EQ`・`ASSERT_FLOAT_EQ`（REAL）を追加しました。Google Test と同じく、2 つの値の間にある表現可能な値の数（ULP の距離）が 4 以下なら等しいとみなします（2 の冪をまたぐ場合・ゼロをまたぐ場合・非正規化数を含む）。NaN はどの値とも等しくありません。Google Test と違い、無限大は同じ無限大とだけ等しいとします（Google Test は最大の有限値と無限大を 1 ULP 離れているとみなします）。ビット列への変換（ベンダーによって挙動が違う）は使わず、2 の冪による正規化で距離を計算します。末尾にメッセージを渡せます（`_MSG` 形はありません）。
- ヘルパーでアサーションを使えるようにしました（`JIECUNIT_DECLARE_HELPER()`）。Google Test と同じく、ヘルパーの中の致命的な失敗（`ASSERT_*`・`FAIL`）は、ヘルパーから戻るだけでテストは続きます。次を追加しました。
  - `HAS_FATAL_FAILURE()`・`HAS_NONFATAL_FAILURE()`・`HAS_FAILURE()`: 実行中のテストに失敗があったか。
  - `ASSERT_NO_FATAL_FAILURE(statement)`・`EXPECT_NO_FATAL_FAILURE(statement)`: 文（ヘルパーの呼び出し）が新しい致命的な失敗を起こしたら失敗にします。`ASSERT_` はテストを止めます。入れ子は `JIECUNIT_MAX_NO_FATAL_FAILURE_DEPTH`（既定 8）段までです。
  - `EXPECT_FATAL_FAILURE(statement, substr)`・`EXPECT_NONFATAL_FAILURE(statement, substr)`: 文がその種類の失敗をちょうど 1 つ起こし、その行（位置の行を除く）のどれかに `substr` を含むことを確かめます（Google Test の gtest-spi.h）。確かめた失敗は表示も集計もしません。アサーションやヘルパー自体のテストに使います。`EXPECT_FATAL_FAILURE` の文はヘルパーの呼び出しにしてください。文の中に直接 `ASSERT_*` を書くとテストから戻ってしまうので、次のサイクルの始めにその旨の失敗を出してテストを終えます（`TEST_M` も終えます）。入れ子にはできません。`substr` が空なら、どの失敗にも含まれるとみなします。`EXPECT_FATAL_FAILURE` の中の `EXPECT_NO_FATAL_FAILURE` は捕捉した致命的失敗を数え、`EXPECT_NO_FATAL_FAILURE` の中の `EXPECT_FATAL_FAILURE` が捕捉した失敗は新しい致命的失敗に数えません（Google Test と同じ）。
- テストスイート: `TEST_S(suite, name)`・`TEST_M(suite, name)` と書けます（引数 1 個の従来の形もそのまま使えます）。プログラム名は `suite_name` で（`_JIEC_TESTNAMES_LIST_` にはこの名前を書きます）、結果の行には `suite.name` と表示します。
- フィクスチャ（Google Test の `TEST_F`）: `TEST_F_S(F, name)`（単一サイクル）と `TEST_F_M(F, name)`（複数サイクル）を追加しました。終わりは `END_TEST_S` / `END_TEST_M` です。フィクスチャ `F` は、構造体型 `F` と、関数 `F_SetUp` / `F_TearDown`（どちらも `var_in_out fixture: F` を受け取り、`JIECUNIT_DECLARE_HELPER()` で宣言する）で定義します。テストは変数 `fixture` を使えます。`fixture` はテストを実行するたびに `F` の初期値に戻り、`F_SetUp` を呼んでから本体を実行します。SetUp が致命的に失敗するか、スキップ・`EOT()` したときは、本体を実行しません。テストが終わった後（`EOT()`・`ASSERT`・`SKIP_TEST`・サイクルの上限のいずれでも）、JiecUnitMain が 1 サイクル待つ間に `F_TearDown` を実行し、TearDown の失敗もそのテストに数えます。TearDown が実行されなかったときは `[  ERROR ]` にします。
- 配列の比較 `EXPECT_EQ_ARRAY_<T>(expected, actual, n)`・`ASSERT_EQ_ARRAY_<T>` を追加しました（`<T>` は `EXPECT_EQ_<T>` と同じ 28 種類の型）。両方の配列の添字 0 から n - 1 の要素を比べ、最初に違う要素を `expected[i]` / `actual[i]` として、その型の EQ と同じ形式で報告します（`The arrays differ first at index i.`）。配列は添字 0 から始まる必要があり、`n` は 0 以上で配列の長さ以下にしてください（0 以下なら何も比べません）。`n` と配列の式は繰り返し評価されるので、副作用のない式にしてください。ループ変数 `jiecunit_loop_index` を、テストの見出しと `JIECUNIT_DECLARE_HELPER()` が宣言します。
- 部分文字列 `EXPECT_STR_CONTAINS(haystack, needle)`・`ASSERT_STR_CONTAINS` を追加しました。空の `needle` はどの文字列にも含まれるとみなします。
- 実行結果をグローバル変数 `g_jiecunit_result`（`JiecUnitResult_t`）に公開します。`state`（0: 未実行、1: 実行中、2: 完了）・`num_of_tests`・`num_of_passed`・`num_of_failed`・`num_of_skipped`（テストが終わるたびに更新）・`elapsed_us`・`all_passed`・`run_count` です。PLC のツールで、コンソールを読まずに合否が分かります。
- 再実行: 完了した後（`g_jiecunit_result.state` が 2 のとき）に `g_jiecunit_rerun` を true にすると、JiecUnitMain がそれを false に戻して、すべてのテストをもう一度実行します（PLC をダウンロードし直す必要がありません）。実行中に立てた要求は、完了の時点で捨てます。テストプログラムの変数は初期化されないので、テストごとに初期化したい状態はフィクスチャ（`TEST_F_*`）に置いてください。フィクスチャは実行のたびに初期値に戻ります。
- `DECLARE_EXTERNAL_JIECUNIT_RESULT()` で、`g_jiecunit_result` と `g_jiecunit_rerun` の `var_external` を宣言できます。
- `JIECUNIT_NO_HALT` を定義すると、jier でも集計の後に `halt` せず、PLC と同じく動き続けます（再実行の確認などに使います）。この場合、jier の終了は `--max-cycles` か、利用者のプログラムの `halt` によります。
- KEYENCE・MITSUBISHI で使えない型のアサーション（64bit の整数とビット列、DATE・TOD・DT。配列の形を含む）は、前処理の時点で `not supported on this target` のエラーにします（従来は TIME の EQ/NE だけで、ほかは展開されないマクロ名が残り、ベンダーのツールで初めてエラーになっていました）。
- `SET_TEST_MAX_CYCLES(n)` を追加しました。実行中のテストのサイクル数の上限を変えます（0 なら無制限）。次のテストでは `JIECUNIT_MAX_CYCLES_PER_TEST` に戻ります。`JIECUNIT_MAX_CYCLES_PER_TEST` は `-D` で上書きできます。
- テストプログラムが JiecUnitMain の 1 サイクルの間に 1 回も実行されなかったとき、または 2 回以上実行されたとき（別の周期のタスクに割り付けたときなど）、`[  ERROR ]` を出して失敗にします。JiecUnitMain は、従来どおりタスクの先頭に置くほか、末尾に置いても動きます。

- 設定値を `-D NAME=VALUE` で上書きできるようにしました（従来は再定義の警告 PP35 が出て、`-Werror` では失敗していました）。対象は `MAX_TESTS`・`TESTNAME_MAX_SIZE`・`FILENAME_MAX_SIZE`・`JIECUNIT_MAX_CYCLES_PER_TEST`・`EXPRESSION_MAX_SIZE`（新設。既定 128）と、`sys/sys_config.iec` の `STRING_MAX_SIZE`・`CONSOLE_MAX_ROWS`・`CONSOLE_MAX_COLS` です。`MAX_TESTS` が 512（`src/jiecunit_macros.iec` の上限）を超えるとき、`TESTNAME_MAX_SIZE`・`FILENAME_MAX_SIZE`・`EXPRESSION_MAX_SIZE` が `STRING_MAX_SIZE` を超えるときは、前処理をエラーで止めます。`CONSOLE_MAX_COLS` より長い行は、従来どおりコンソールの行バッファでは切れます。
- コンソール（`g_console`）の行バッファが一巡して古い行が上書きされたとき、集計の最後に `[ WARNING] The console buffer is full (CONSOLE_MAX_ROWS=N); older lines may have been overwritten.` と出します（すべての行を標準出力に出す jier では、`JIECUNIT_JIER_CONSOLE_WARNING` を定義したときだけ出します）。`Console_t` に `full`（一巡した）と `wrapped`（上書きした）を追加しました。

- テストを `_JIEC_TESTNAMES_LIST_` に書き忘れると、そのテストは黙って実行されませんでした。`TEST_S` / `TEST_M` の定義の数を jiepp の名前付きカウンタで数え、一覧の名前の数と違えば前処理をエラーで止めます。比べるのは数だけです。一覧に同じ名前を 2 回書いたときは、jier ではコンパイル時の `DUPLICATE_SYMBOL`、PLC では登録時の `Fatal error: ... already registered.` で検出されます。名前の綴りの誤りは、jier では未定義のプログラム、PLC では実行時の `[  ERROR ] ... was not found in active tasks.` で検出されます。一覧は 1 回だけ展開してください（カウンタは戻らないので、2 回目は必ず不一致になります）。`JIECUNIT_NO_TEST_COUNT_CHECK` を定義すると照合しません。完全な自動登録は、jiepp がマクロからディレクティブを作れないこと、構成（configuration）とベンダーのタスク割付にプログラム名の列挙が要ることから、行っていません。

- `scripts/jiecunit_to_junit.py` を追加しました。JiecUnit の出力（`jiecc --run` の標準出力、または PLC の `g_console` を順に書き出したテキスト）を JUnit XML に変換します。`suite.name` のテストは `classname="suite"`、スイートの無いテストは入力ファイル名（`--classname` で変更可）を classname にします。失敗は 1 件ずつ `<failure>`、`[  ERROR ]` は `<error>`、スキップは `<skipped>` にし、所要時間が `(n/a)` のときは `time` を付けません。再実行の出力は最後の実行だけを変換します。集計が無い・結果の無いテストがある・集計の件数が合わない・登録時の致命的エラー・コンソールの溢れの警告があるときは、テストスイート `JiecUnit` のテストケース `(run)` の `<error>` として XML に書き、終了コードを 1 にします。XML に使えない制御文字は `?` に置き換えます。`scripts/run_tests.py` に `--junit-dir DIR`（各スイートの XML を `DIR/<スイート>.xml` に書く。変換で問題が見つかればそのスイートを失敗にする）を追加し、golden フェーズで変換スクリプトの自己テスト（`--self-test`）を実行します。

### その他 / Other

- PLC のツールに取り込めない恐れのある箇所を直しました。`JiecTest_t` の配列の上限が XML に式（`upper="8-1"`）のまま出ていたのを、数値で出るようにしました。変数名 `t1`・`t2`・`t3`・`next` を改名しました（キーエンス・三菱のデバイス名や命令名と重なりうるため）。`jiec_quote` の 1 文字用の変数を `string[8]` にし、切り詰めの余白を 1 増やしました（OMRON の STRING のサイズは終端を含むため）。
- 実行していないとき、各テストプログラムは `JiecTest_isActive` を呼ぶだけで戻ります（従来は毎スキャン、テスト名の文字列も比べていました）。
- ゴールデンの比較で、`(n/a)` を所要時間として正規化するのをやめました（時計の無い jier が `(0us)` と出す退行を検出できます）。
- README に「テストの書き方」（最小の例、テストの種類とフィクスチャ、アサーションの一覧、ヘルパー、失敗の出力、サイクル数の上限、結果の変数と再実行、設定の上書き、JUnit XML、Google Test との違い、7.x からの移行）と、ターゲットごとのアサーションの対応表を加えました。サンプルの実行手順のテストプログラムの一覧を更新しました（画面の写真は 7.x のままです）。
- AGENTS.md と CONTRIBUTING.md に、ゴールデン出力の更新手順と、実装中に見つけた jiepp・jier・ST の落とし穴を加えました。
- `sys/sys.iec` に `jiec_find`（標準の `find`）と `jiec_quote`（文字列を ST のリテラルの形にする。`STRING_MAX_SIZE` に収まらなければ切って、閉じの `'` の後ろに `...` を付ける）を追加しました。
- 失敗に関する出力は `JiecTest_print` を通して出します。位置・詳細・メッセージを出す `JiecTest_beginFailure`・`JiecTest_printValue`・`JiecTest_printComparison`・`JiecTest_endFailure` を追加しました。
- JiecUnit 自身のテスト（`test/test_failure_api.iec`）で、失敗の出力の文面を `EXPECT_NONFATAL_FAILURE` で確かめます。
- `scripts/check_macro_expansion.py` は、各公開マクロが値の引数の式のテキストを引数の順に渡していることも検査します。
- `src/jiecunit_core.iec` から、使われていなかった内部マクロ（`_MSG` の付かない `_VALIDATE_*`）を削除しました。
- `samples/sample.iec` に、スイートのテスト（`Mean.of_negative_values`）とフィクスチャのテスト（`RunningMeanFixture.follows_the_samples`）を追加しました。
- `samples/sample.iec` の一覧を、テストの定義の後ろへ移しました。
- 検証関数の `message` 引数の長さを `string[128]` から `string[STRING_MAX_SIZE]` にそろえました（失敗の出力を行う `JiecTest_failure` と同じ長さです）。
- `scripts/check_golden.py` を追加しました。`test/golden/*.iec` を `jiecc --run` で実行し、標準出力と終了コードを `test/golden/*.out` と比べます。所要時間の表示とパスの区切りは比べる前に正規化します。`--update` で期待値を作り直します。`scripts/run_tests.py` は、この検査を `golden` フェーズとして実行します（`--skip-golden` で省略できます。`--compile-only`・`--run-only` のときも実行しません）。CI でも、jier の実行と同じく任意のステップとして実行します。
- `scripts/run_tests.py` の `--max-cycles` の既定値を 200 から 100000 に変えました。jier の実行は集計の後の `halt` で止まるので、この値は集計に達しない実行を打ち切るときだけ効きます。

## 7.0.0 (2026-11-08)

6.0.0 からの変更です。

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

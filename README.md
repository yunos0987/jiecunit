# JiecUnit

![JiecUnit](./docs/jiecunit.png)

## 目次
- [概要](#概要)
- [アサーションのメッセージ引数](#アサーションのメッセージ引数)
- [必要環境](#必要環境)
- [単体テストのサンプルの実行方法](#単体テストのサンプルの実行方法)
  - [オムロン社製Sysmac Studioの場合](#オムロン社製sysmac-studioの場合の単体テストサンプルの実行方法)
  - [キーエンス社製KV Studioの場合](#キーエンス社製kv-studioの場合の単体テストサンプルの実行方法)
  - [CODESYS社製CODESYSの場合](#codesys社製codesysの場合の単体テストサンプルの実行方法)
- [JiecUnit開発者向け](#jiecunit開発者向け)
  - [リポジトリ構成](#リポジトリ構成)
  - [JiecUnitのテスト方法](#jiecunitのテスト方法)
  - [追加したアサーション API](#追加したアサーション-api)
  - [各メーカーの言語サポート状況](#各メーカーの言語サポート状況)
- [ライセンス](#ライセンス)
- [その他の情報](#その他の情報)

## 概要

JiecUnitは、テキスト形式で記述された[IEC 61131-3言語](https://plcopen.org/sites/default/files/downloads/iec_61131-3_preview.pdf)のPOUを単体テストするためのフレームワークです。

特徴は、テスト対象POUのソースコード、単体テストコード、JiecUnit自体のソースコードがすべてIEC 61131-3 ST言語を拡張したテキスト形式で完結している点です。これにより、Git等で直接構成管理が可能です。[Visual Studio Code](https://code.visualstudio.com/)などの対応IDEによっては生成AIを活用したIEC 61131-3プログラミングも可能です。

このテキスト形式コードをPLCメーカーのツールで取り込み可能な形式に変換するため、[IEC 61131-3 ⇄ IEC 61131-10変換ソフトウェア Jiecc](https://www.graviness.com/iec_61131-3/jiecc.html)を使用します。

JiecUnitは現在、[IEC 61131-10 XML](https://plcopen.org/sites/default/files/downloads/iec_61131-10_preview.pdf)をサポートする以下の環境に対応しています。
* オムロン社製[Sysmac Studio](https://www.fa.omron.co.jp/products/family/3077/download/software.html)
* キーエンス社製[KV Studio](https://www.keyence.co.jp/support/user/controls/installer/)
* CODESYS社製[CODESYS](https://content.helpme-codesys.com/en/CODESYS%20Installer/_inst_start_page.html)
* Jieccのjierインタプリタによる直接実行（`jiecc --run`。PLC・IDE不要。開発者検証／CI用途）

## アサーションのメッセージ引数

すべての`EXPECT_*`・`ASSERT_*`アサーションマクロ、および`FAIL`・`ADD_FAILURE`は、失敗時に表示するメッセージを末尾の省略可能な引数として受け取ります。メッセージを渡すために`_MSG`サフィックス付きのマクロ名を使う必要はありません。

```
EXPECT_EQ_INT(expected, actual);
EXPECT_EQ_INT(expected, actual, '期待値と一致しません');
EXPECT_TRUE(condition, '条件を満たしていません');
EXPECT_NEAR(1.0, 1.001, 0.01, '許容誤差を超えています');
FAIL('想定外の分岐に到達しました');
ADD_FAILURE('この時点で失敗として記録します');
```

- `_MSG`サフィックス付きのマクロ（`EXPECT_EQ_INT_MSG`など）は後方互換のために残していますが、**非推奨**です。新規コードでは末尾の省略可能な引数としてメッセージを渡してください。
- メッセージ文字列や値引数に含まれるカンマ・括弧はそのまま書けます（例: `EXPECT_EQ_STRING(a, b, 'カンマ, と (括弧)');`）。
- 引数の個数を間違えた場合の検出のされ方は4通りあります。`jiecc --run`（および`python scripts/run_tests.py`）はいずれの間違いも検出しますが、`jiecc -c`は次の2番目・4番目のケースでは終了コード0のまま（誤った）XMLを出力してしまうため、終了コードだけを見る運用では見逃します。`jiecc -c`を使う場合は標準エラー出力の`error:`行も必ず確認してください。
  - 多すぎる場合（必須引数より後ろの余分な引数が16個以内）: `JIECUNIT_ASSERTION_TAKES_<lo>_OR_<hi>_ARGUMENTS`（`<lo>`・`<hi>`は正しい総引数数）という名前の構文エラーになります。`jiecc -c`によるコンパイル時、`jiecc --run`による直接実行時のいずれでも、呼び出し元の行番号とともに検出されます。
  - 少なすぎる場合（例: `EXPECT_EQ_INT(1)`）: 必須引数が名前付きで宣言されているため、プリプロセッサが`PP34: Argument count mismatch; 'expected 2-16777215, got 1'`のようなエラーを呼び出し元の行番号とともに報告します。`16777215`はプリプロセッサ上の「上限なし」を表す内部値で、実際の上限は上記の構文エラー側で検出されます。同一ファイル内に複数あっても最初の1件で打ち切られます。ただし`jiecc -c`はこのPP34エラーをstderrに表示しつつ**終了コード0でPOUを1つも含まないXML**を出力してしまいます。終了コードだけを確認すると気付けず、そのままIDEに取り込むとテストが全部消えた空プロジェクトになるので注意してください。`python scripts/run_tests.py`はstderrの`error:`行を検出してこのケースを失敗として扱います。
  - 引数を1つも書かなかった場合（例: `EXPECT_FALSE()`）: 空の引数1個として展開されるため、`jiecc -c`が呼び出し元の行で`','; INVALID_SYNTAX`を報告します。
  - 必須引数より後ろの余分な引数が17個以上ある場合: `jiecc -c`はエラーを出さず**正常なXML**を生成してしまいます。この間違いは`jiecc --run`実行時の`UNDEFINED_SYMBOL`エラー（`_JIECUNIT_OPTMSG2_17`のような内部シンボル名を含む）でのみ検出されます。
- 値引数の直後に置く最後の省略可能な引数（`EXPECT_TRUE`・`EXPECT_FALSE`なら2番目、`EXPECT_EQ_*`などの2値比較系は3番目、`EXPECT_NEAR`・`EXPECT_NEAR_REL`のような3値比較系は4番目、`FAIL`・`ADD_FAILURE`なら1番目の引数）は、常にSTRINGのメッセージとして解釈されます。数値やBOOLを渡してしまっても`jiecc -c`では検出されず、実行時に型不一致で停止するため注意してください（例: 許容誤差のつもりで`EXPECT_NEAR`ではなく`EXPECT_EQ_INT(a, b, tol)`のように書いてしまうミスに注意）。
- `SKIP_TEST(reason)`の理由は、スキップした事実を記録に残すため省略できません。
- `python scripts/check_macro_expansion.py`で、この省略可能引数の展開結果と`_MSG`版の展開結果が一致することを検証できます。

## 必要環境

JiecUnitのサンプル単体テストを実行するには、以下の環境が必要です。

* [Jiecc 5.14以降](https://www.graviness.com/iec_61131-3/jiecc.html#Header.Jiecc%E3%81%AE%E3%83%80%E3%82%A6%E3%83%B3%E3%83%AD%E3%83%BC%E3%83%89%E3%81%A8%E5%AE%9F%E8%A1%8C%E6%96%B9%E6%B3%95)
  * Jieccは、IEC 61131-3テキストをIEC 61131-10 XMLに変換する無料のコマンドラインソフトウェアです。[Jieccのダウンロードと実行方法](https://www.graviness.com/iec_61131-3/jiecc.html#Header.Jiecc%E3%81%AE%E3%83%80%E3%82%A6%E3%83%B3%E3%83%AD%E3%83%BC%E3%83%89%E3%81%A8%E5%AE%9F%E8%A1%8C%E6%96%B9%E6%B3%95)を参照してください。
  * `jiecc --run`（jierインタプリタによる直接実行）や`scripts/run_tests.py`を使用する場合は、Jiecc 7.1.0以降が必要です。
* [Sysmac Studio](https://www.fa.omron.co.jp/products/family/3077/download/software.html)（試用期間制限あり）、[KV Studio](https://www.keyence.co.jp/support/user/controls/installer/)（試用回数制限あり）、または[CODESYS](https://content.helpme-codesys.com/en/CODESYS%20Installer/_inst_start_page.html)
  * いずれも同梱シミュレータでテスト可能。必要に応じてPLC本体もご用意ください。
  * `jiecc --run`による直接実行のみで検証する場合は、ベンダIDEは不要です。

## 単体テストのサンプルの実行方法

まず、JiecUnitプロジェクトをダウンロードします。mainブランチの[Download ZIP](https://github.com/yunos0987/jiecunit/archive/refs/heads/main.zip)で取得するか、`git clone https://github.com/yunos0987/jiecunit.git`でクローンしてください。

JiecUnitプロジェクトには、単体テスト実行可能なサンプルが[samplesディレクトリ](./samples/)にあります。[samples/sample_pous.iec](./samples/sample_pous.iec)には、テスト対象POUとして以下2つが含まれます。
* `mean`ファンクション：配列入力の平均値を計算
* `RunningMean`ファンクションブロック：状態を記憶し逐次平均値を出力

[samples/sample.iec](./samples/sample.iec)には、上記POUをテストする2つのテストプログラム`test_mean`と`test_RunningMean`が含まれています。

テストサンプルの実行方法は環境ごとに異なります。

### オムロン社製Sysmac Studioの場合の単体テストサンプルの実行方法

1. コマンドプロンプトを起動し、次のコマンドを実行します。

コマンド内の`<JiecUnit Project Root>`はJiecUnitプロジェクトをダウンロードしたディレクトリに変更してください。また、事前にjiecc.exeを`<JiecUnit Project Root>`直下におくか、jieccがあるディレクトリへパスを通しておいてください。

```
$ cd <JiecUnit Project Root>
$ jiecc .\samples\sample.iec -I. -I.\sys -t omron -o .\samples\sample.xml
```

`.\samples\sample.xml`が出力されます。

2. 出力された`.\samples\sample.xml`をSysmac StudioのIEC 61131-10インポート機能 [ ツール | IEC 61131-10 XML | インポート ] でインポートします。

単体テストを実行するためのグローバル変数、データ型、およびPOUがインポートされます。インポート完了後に次のダイアログが表示されるので、OKを押下します。

![インポート完了ダイアログ](./docs/dialog_complete_to_import.png)

3. Sysmac Studioのタスク設定でプライマリ定周期タスクに以下のようにプログラムを割り付けます（マルチビューエクスプローラ|構成・設定|タスク設定|プログラムの割付設定|）。必要に応じて、デフォルトで作成されるProgram0プログラムを削除してください。特に、`JiecUnitMain`が先頭になるように設定してください。
  * `JiecUnitMain`
  * `test_mean`
  * `test_RunningMean`

![プログラムの割付設定](./docs/display_task_config.png)

4. ビルド（F8キー）し、シミュレータ（F5キー）や実機で実行します。
5. テストの実行結果がグローバル変数`g_console`に出力されます。

![テスト実行ログ](./docs/display_test_result.png)

2つのテスト`test_mean`と`test_RunningMean`が実行され、テストをパス（成功）したことを意味します。

以下は、テストが失敗したときの例です。テスト`test_RunningMean`のテストコード57行目の3サイクル目（@2）において、期待値は5であったが、実値は3となり、失敗したことを意味します。

※*57行目*という数字は、XMLにコンバートする前のテキストの行番号です。これをSysmac Studio上のtest_RunningMeanの行数で表示するテクニックは、[Jieccソフトウェア](https://www.graviness.com/iec_61131-3/jiecc.html)の機能を活用します。ここでは、深く述べません。

![テスト実行NGログ](./docs/display_test_result_ng.png)

### キーエンス社製KV Studioの場合の単体テストサンプルの実行方法

1. コマンドプロンプトを起動し、次のコマンドを実行します。

コマンド内の`<JiecUnit Project Root>`はJiecUnitプロジェクトをダウンロードしたディレクトリに変更してください。また、事前にjiecc.exeを`<JiecUnit Project Root>`直下におくか、jieccがあるディレクトリへパスを通しておいてください。

```
$ cd <JiecUnit Project Root>
$ jiecc .\samples\sample.iec -I. -I.\sys -t keyence -o .\samples\sample.xml
```

`.\samples\sample.xml`が出力されます。

2. 出力された`.\samples\sample.xml`をKV StudioのIEC 61131-10インポート機能 \[ ファイル | インポート | IEC 61131-10 XMLのインポート \] でインポートします。

単体テストを実行するためのグローバル変数、データ型、およびPOUがインポートされます。インポート完了後に次のダイアログが表示されるので、OKを押下します。

![インポート完了ダイアログ](./docs/ke.dialog_complete_to_import.png)

3. KV Studioのワークスペースにおいて、毎スキャンモジュールが次のようになっていることを確認します。必要に応じて、デフォルトで作成される`Main`モジュールを削除してください。特に`JiecUnitMain`が先頭になっていることを確認してください。
  * `JiecUnitMain`
  * `test_mean`
  * `test_RunningMean`

![毎スキャンモジュール](./docs/ke.display_modules.png)

4. 変換（Ctrl＋F9キー）し、シミュレータ（Ctrl＋F2キー）や実機で実行（シミュレータの場合、[ デバッグ | RUN ]）します。
5. テストの実行結果がグローバル変数`g_console`に出力されます。

![テスト実行ログ](./docs/ke.display_test_result.png)

2つのテスト`test_mean`と`test_RunningMean`が実行され、テストをパス（成功）したことを意味します。

以下は、テストが失敗したときの例です。テスト`test_RunningMean`のテストコード56行目の3サイクル目（@2）において、期待値は5であったが、実値は3となり、失敗したことを意味します。

※*56行目*という数字は、XMLにコンバートする前のテキストの行番号です。これをKV Studio上のtest_RunningMeanの行数で表示するテクニックは、[Jieccソフトウェア](https://www.graviness.com/iec_61131-3/jiecc.html)の機能を活用します。ここでは、深く述べません。

![テスト実行NGログ](./docs/ke.display_test_result_ng.png)

### CODESYS社製CODESYSの場合の単体テストサンプルの実行方法

事前にCODESYSの[IEC 61131-10のインポート機能を有効化](https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_cmd_import_iec_61131_10.html)しておいてください。

1. コマンドプロンプトを起動し、次のコマンドを実行します。

コマンド内の`<JiecUnit Project Root>`はJiecUnitプロジェクトをダウンロードしたディレクトリに変更してください。また、事前にjiecc.exeを`<JiecUnit Project Root>`直下におくか、jieccがあるディレクトリへパスを通しておいてください。

```
$ cd <JiecUnit Project Root>
$ jiecc .\samples\sample.iec -I. -I.\sys -t codesys -o .\samples\sample.xml
```

`.\samples\sample.xml`が出力されます。

2. CODESYSにてNew ProjectにてEmpty projectを作成し、出力された`.\samples\sample.xml`をCODESYSのIEC 61131-10インポート機能 \[File | Import IEC 61131-10\] でインポートします。

インポートダイアログが表示されます。

![インポートダイアログ](./docs/co.dialog_ready_to_import.png)

3. OKボタンを押下します。

単体テストを実行するためのコンフィグレーション、リソース、グローバル変数、データ型、POUがインポートされます。

4. CODESYSのDevices画面において、インポートされたMainConfigurationを右クリックし、Update Device...から適切なデバイスを設定します。

5. POUs画面において、以下画像の通りにオブジェクトを選択し（Project Settings以外を選択し）、Devices画面のMainResourceにドラッグ＆ドロップします。

![POUs画面](./docs/co.display_ready_to_set_objects.png)

MainResouce下にオブジェクトが移動されます。

![Devices画面](./docs/co.display_complete_to_set_objects.png)

6. Devices画面において、MainResourceを右クリックし、Add Object | Task Configuration... し、追加されたTask Configurationを次のように設定します。特に`JiecUnitMain`が先頭になっていることを確認してください。
  * `JiecUnitMain`
  * `test_mean`
  * `test_RunningMean`

![タスク構成](./docs/co.display_task_configuration.png)

7. Devices画面のLibrary Managerを選択し、AddLibraryを選択し、次の画面のようにStandard Libraryの`CONCAT`を選択した状態にし、OKボタンを押下します。

![標準ライブラリの追加](./docs/co.display_add_stdlib.png)

Standardライブラリが追加されます。

8. Generate Code（F11キー）すると、「C0174: VAR_TEMP declaration not allowed in this place」エラーが複数出力されますので、Replaceダイアログで次のように設定し、Replace Allボタンを押下します。

![Replaceダイアログ](./docs/co.dialog_replace_VAR_TEMP_to_VAR.png)

ソースコード内のすべての`VAR_TEMP`が`VAR`に置換されます。

9. Generate Code（F11キー）し、成功することを確認します。シミュレーションや実機で実行（シミュレーションの場合、[ Debug | F5 ]）します。

10. テストの実行結果がグローバル変数`g_console`に出力されます。

![テスト実行ログ](./docs/co.display_test_result.png)

2つのテスト`test_mean`と`test_RunningMean`が実行され、テストをパス（成功）したことを意味します。

以下は、テストが失敗したときの例です。テスト`test_RunningMean`のテストコード58行目の3サイクル目（@2）において、期待値は5.0であったが、実値は3.0となり、失敗したことを意味します。

※*58行目*という数字は、XMLにコンバートする前のテキストの行番号です。これをCODESYS上のtest_RunningMeanの行数で表示するテクニックは、[Jieccソフトウェア](https://www.graviness.com/iec_61131-3/jiecc.html)の機能を活用します。ここでは、深く述べません。

![テスト実行NGログ](./docs/co.display_test_result_ng.png)

## JiecUnit開発者向け

### リポジトリ構成

* [jiecunit.iec](./jiecunit.iec)：JiecUnitユーザが使用すべき公開API。テスト記述用のマクロや関数群を定義。
* [docsディレクトリ](./docs/)：補助資料（各種画像、説明図、メーカー別手順、技術資料など）を格納。
* [samplesディレクトリ](./samples/)：JiecUnitの使い方サンプル。テスト対象POU（sample_pous.iec）とテストコード（sample.iec）を含む。
* [srcディレクトリ](./src/)：JiecUnit本体のソースコード。コア機能、テスト実行エンジン、設定ファイルなど。
* [sysディレクトリ](./sys/)：JiecUnitの動作に必要な補助的コード。型変換ファンクション、コンソール出力、メーカー依存の補助関数など。
* [testディレクトリ](./test/)：JiecUnit自体の単体テストコード。各種マクロ・内部関数の動作検証用テストファイル（test_jiectest.iec等）を含む。
* [scriptsディレクトリ](./scripts/)：開発補助スクリプト。マクロ生成（generate_macros.py）、テスト一括実行（run_tests.py）、およびメッセージ引数省略形と`_MSG`形の展開結果一致検証（check_macro_expansion.py）を含む。
* [checkディレクトリ](./check/)：テスト結果（XMLファイル等）の出力先。テスト実行時に生成される成果物を格納。
* [README.md](./README.md)：本ドキュメント。使い方・構成・サポート状況などを記載。
* [CODING_RULES.md](./CODING_RULES.md)：コーディング規約。命名規則・フォーマット・テストの書き方などを記載。
* [LICENSE](./LICENSE)：ライセンス情報。
* [VERSION](./VERSION)：バージョン管理用ファイル。
* [VERSION_MANAGEMENT.md](./VERSION_MANAGEMENT.md)：バージョン管理の運用ルールや履歴。

### JiecUnitのテスト方法

まず、以下のコマンドで一括検証することを推奨します（全ターゲットのコンパイル確認、jierインタプリタによるテスト実行、およびメッセージ引数省略形と`_MSG`形の展開結果一致検証を一度に行います）。

```
$ cd <JiecUnit Project Root>
$ python scripts/run_tests.py
```

マクロ展開の同値検証だけを単独で実行したい場合は、以下のコマンドを使用します。

```
$ python scripts/check_macro_expansion.py
```

個別にjierインタプリタで実行する場合は、以下のコマンドを使用します。

```
$ jiecc --run test/test.iec -I. -I./sys --max-cycles 200
```

* jiecc --runモードのプロセス終了コードはテスト結果を反映しません。テストの成否は標準出力の`[ PASSED ]`/`[ FAILED ]`行で判定してください（`scripts/run_tests.py`はこれを自動判定します）。
* `--max-cycles`オプションは必須です。指定しない場合、複数スキャンサイクルにまたがるテストが完走しません。

ベンダIDEへの取り込みを確認する場合は、ターゲットの環境ごとに以下のコマンドを実行し、上述と同じ手順を実行します。

```
$ cd <JiecUnit Project Root>
$ mkdir check
$ cd check
$ jiecc -I.. -I..\sys ..\test\test.iec -o .\test.xml -t omron
or
$ jiecc -I.. -I..\sys ..\test\test.iec -o .\test.xml -t keyence
or
$ jiecc -I.. -I..\sys ..\test\test.iec -o .\test.xml -t codesys
```

### 追加したアサーション API

* `EXPECT_NEAR_REL(val1, val2, rel_error)` / `ASSERT_NEAR_REL(val1, val2, rel_error)`（末尾にmessageを追加可能）：相対誤差による近似比較。許容差は`rel_error * max(abs(val1), abs(val2))`。
```
EXPECT_NEAR_REL(100.0, 101.0, 0.02); // |100.0 - 101.0| <= 0.02 * 101.0 なので成功
```
* `FAIL()` / `FAIL(message)`：即座に失敗として記録し、テストを中断する。
```
FAIL('到達してはならない分岐に到達した');
```
* `ADD_FAILURE()` / `ADD_FAILURE(message)`：失敗として記録するが、テストは継続する。
```
ADD_FAILURE('この時点で不整合を検出したが、後続の検証も継続する');
```
* `SKIP_TEST(reason)`：現在のテストをスキップとして報告し、テストを終了する（成功でも失敗でもない）。
```
SKIP_TEST('この環境では出力フォーマットが処理系依存のため検証しない');
```

### 各メーカーのIEC 61131-3言語サポート状況

| 項目             | OM (Sysmac) | KE (KV) | CO (CODESYS) |
|------------------|:-----------:|:-------:|:------------:|
| データ型 SINT    | ✓           |         | ✓            |
| データ型 INT     | ✓           | ✓       | ✓            |
| データ型 DINT    | ✓           | ✓       | ✓            |
| データ型 LINT    | ✓           |         | ✓            |
| データ型 USINT   | ✓           |         | ✓            |
| データ型 UINT    | ✓           | ✓       | ✓            |
| データ型 UDINT   | ✓           | ✓       | ✓            |
| データ型 ULINT   | ✓           |         | ✓            |
| データ型 REAL    | ✓           | ✓       | ✓            |
| データ型 LREAL   | ✓           | ✓       | ✓            |
| データ型 BYTE    | ✓           |         | ✓            |
| データ型 WORD    | ✓           |         | ✓            |
| データ型 DWORD   | ✓           |         | ✓            |
| データ型 LWORD   | ✓           |         | ✓            |
| データ型 TIME    | ✓           |         | ✓            |
| データ型 BOOL    | ✓           | ✓       | ✓            |
| データ型 DATE    | ✓           |         | ✓            |
| データ型 TIME_OF_DAY    | ✓           |         | ✓            |
| データ型 DATE_AND_TIME    | ✓           |         | ✓            |
| データ型 STRING  | ✓           | ✓       | ✓            |
| データ型 WSTRING |             |         | ✓            |
| 構造体          | ✓           | ✓       | ✓            |
| FB              | ✓           | ✓       | ✓            |
| 配列            | ✓           | ✓       | ✓            |

## ライセンス

このプロジェクトはMIT Licenseのもとで公開されています。詳細は[LICENSE](./LICENSE)ファイルをご参照ください。

## その他の情報

[Graviness Blog](http://blog.graviness.com/?eid=949303)もご参照ください。

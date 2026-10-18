# Contributing to JiecUnit

JiecUnit への貢献に関心を持っていただき、ありがとうございます。

## 目次

1. [貢献の流れ](#貢献の流れ)
2. [テストの実行](#テストの実行)
3. [コーディング規約](#コーディング規約)
4. [バージョン管理](#バージョン管理)

## 貢献の流れ

1. `develop` ブランチから作業用のブランチを作る。
2. 変更する。コミットは、目的が分かる最小の単位にする。
3. `python scripts/run_tests.py` を実行し、`All checks passed.` と表示されることを確認する（[テストの実行](#テストの実行)）。
4. Pull Request を作る。通常は `develop` を宛先にする。`main` への Pull Request は、`develop` からのリリースの取り込みに使う。
5. リリースは、`release vX.Y.Z` というコミットで [バージョン](#バージョンの更新)を更新し、そのコミットにタグ `vX.Y.Z` を付けて行う。機能追加・修正のコミットでは、バージョンを更新しない。

## テストの実行

[Jiecc](https://www.graviness.com/iec_61131-3/jiecc.html) が必要です。バージョンの要件は [README.md](README.md) を参照してください。

```
$ cd <JiecUnit Project Root>
$ python scripts/run_tests.py
```

jiecc は、`--jiecc PATH`、環境変数 `JIECC`、`PATH` の順に探します。

```
$ python scripts/run_tests.py --jiecc /path/to/jiecc.exe
```

詳細は [README.md](README.md) の「JiecUnitのテスト方法」を参照してください。

## コーディング規約

### 目的

このコーディング規約は、JiecUnit プロジェクトにおける IEC 61131-3 ST 言語コードの品質と一貫性を保つために定められています。

- コードの可読性と保守性の向上
- チーム開発における統一されたコーディングスタイルの確立
- 各社プログラミングツールとの互換性の確保
- 生成 AI との協調開発における効率性の向上
- テスト駆動開発（TDD）による品質保証

### コーディングスタイル

- ファンクションの戻り値に構造体型を使用しない。構造体データを結果として得る必要がある場合、`var_in_out` を使用する。
  - オムロン環境が未サポートのため。
- 時間リテラルは、`time#` を使用する。
  - 時間型の精度のメーカー間互換のため、CODESYS の場合、`time` を `ltime` に置換している。
- 論理式における `or` や `and` のオペランドが式の場合、括弧で括る。

  ```
  if ((i = 0) and (j = 0)) or first_time then
  	...
  end_if;
  ```

- 一行で書くことができる注釈は、`// ～` を使用する。複数行の注釈は、`(* ～ *)` を使用する。`/* ～ */` を使用しない。

### 命名規則

- 以下の名前で定義することを禁止する。
  - `left`, `right`
    - IEC 61131-3 の定義と重複するため。
  - `h`, `H` で始まり、`_` を含まない変数名
    - キーエンス環境の制約。
  - 正規表現 `^[rRtTcC]\d+$` にマッチする変数名
    - キーエンス環境の制約。
  - `p_`, `P_` で始まる要素名
    - オムロン環境の制約。
  - アルファベット 1 文字の要素名
    - キーエンス環境や三菱環境の制約。
- POU 名は、64 バイト以内とすること。
  - キーエンス環境の制約。
- IEC 61131-3 は、ASCII の大文字・小文字を区別しないことに注意すること。
  - 例えば、行列を意味する変数 `A` と、ベクトルを意味する変数 `a` を同一のものとして解釈します。

### フォーマット

- インデントにはタブ文字を使用する。スペース文字によるインデントは使用しない。
- エディタのタブ幅設定は 4 文字とする。

### テスト

次の例のように記述すること。要点については後述する。

```
TEST_S(test_mean)
	var
		x_regular: array[0..3] of lreal;
		x_zeros: array[0..2] of lreal;
		x_negative: array[0..2] of lreal;
		mean_val: lreal;
	end
	{st}
	// Fact: The mean of a sequence of values equals their arithmetic average.
		// Arrange
	x_regular[0] := 6.0;
	x_regular[1] := 3.0;
	x_regular[2] := 5.0;
	x_regular[3] := 2.0;
		// Act
	mean_val := mean(x_regular);
		// Assert
	EXPECT_NEAR(4.0, mean_val, 1.0e-6);

	// Fact: The mean of all-zero values is 0.
		// Arrange
	x_zeros[0] := 0.0;
	x_zeros[1] := 0.0;
	x_zeros[2] := 0.0;
		// Act/Assert
	EXPECT_NEAR(0.0, mean(x_zeros), 1.0e-6);

	// Fact: The mean is correctly computed even when values include negatives.
		// Arrange
	x_negative[0] := -7.0;
	x_negative[1] := -1.0;
	x_negative[2] := 2.0;
		// Act
	mean_val := mean(x_negative);
		// Assert
	EXPECT_NEAR(-2.0, mean_val, 1.0e-6);
	{end}
END_TEST_S
```

- 1 事実を 1 インスタンスでテストコードを記述する。
- 1 関数の n 事実を一つの `TEST_S` 内に記述する。
  - オムロン環境にて、タスクの数が増えると登録に時間が掛かるため。
- 事実を 1 行のコメントで記述する。
- AAA 形式で、Arrange 節、Act 節、Assert 節を明示する。

### ドキュメント

- （生成 AI）POU の先頭に `doc` プラグマを記述すること。

```
(*{doc Obtain the main descriptive statistics.
Compute the mean, variance, skewness, and kurtosis.
@inout data Array containing sample data.
    Must be a normal array (0-based lower bound and at least 1 element).
@input n Use the first n elements of data.
    If -1 is specified, use all elements of data.
    Default value: -1
@output mean Mean (arithmetic mean).
@output variance Variance.
@output skewness Skewness.
@output kurtosis Kurtosis.
@return The number of elements actually used in the calculation.
@error If data is not a normal array.}*)
function Stats_statistics_value: dint
    _PROLOGUE_OF_FUNCTION_()
    var_in_out
        (*{doc Array containing sample data.}*)
        data: array[*] of lreal;
    end
    var_input
        (*{doc Use the first n elements of data.}*)
        n: dint := -1;
    end
    var_output
    (*{doc Mean (arithmetic mean).}*)
    mean: lreal;
    (*{doc Variance.}*)
    variance: lreal;
    (*{doc Skewness.}*)
    skewness: lreal;
    (*{doc Kurtosis.}*)
    kurtosis: lreal;
    end
    :
end
```

### 依存関係

- `{#include}` プリプロセッサ指令を使用してモジュール間の依存関係を明確にする。

### ソースコードの管理

- Git を使用してソースコードを管理する。
- `main` ブランチは常にビルド可能で、テストが通る状態を維持する。
- タグを使用してリリースバージョンを管理する（例: `v1.0.0`）。
- `.gitignore` ファイルを適切に設定し、生成ファイル（`*.xml`、`__pycache__` など）をリポジトリに含めない。

## バージョン管理

JiecUnit は、セマンティックバージョニング（MAJOR.MINOR.PATCH）でリリースを管理します。バージョンはプロジェクトルートの `VERSION` ファイルに記録し、プリプロセッサのマクロでプログラムから参照できます。

### VERSION ファイル

`VERSION` ファイルには、現在のバージョンを次の形式で記述します。

```
MAJOR.MINOR.PATCH
```

例:

```
2.8.1
```

### プログラムからのバージョン参照

バージョンは `src/jiecunit_config.iec` で定義されており、次のマクロで参照できます。

- `_JIECUNIT`: 常に true（JiecUnit がインクルードされていることを示す）
- `_JIECUNIT_VERSION`: バージョン文字列（例: `"2.8.1"`）
- `_JIECUNIT_VER`: 短いバージョン番号（例: バージョン 2.8.x なら `208`）
- `_JIECUNIT_FULL_VER`: 完全なバージョン番号（例: バージョン 2.8.1 なら `20801`）

#### バージョン番号の計算式

- `_JIECUNIT_VER` = MAJOR * 100 + MINOR
  - 例: 2.8.1 → 2 * 100 + 8 = 208
- `_JIECUNIT_FULL_VER` = MAJOR * 10000 + MINOR * 100 + PATCH
  - 例: 2.8.1 → 2 * 10000 + 8 * 100 + 1 = 20801

#### 使用例

```
{#include <jiecunit.iec>}

TEST_S(test_version_info)
	{st}
	puts(jiec_concat('Version: ', _JIECUNIT_VERSION));
	puts(jiec_concat('Short Ver: ', dint_to_string(_JIECUNIT_VER)));
	puts(jiec_concat('Full Ver: ', dint_to_string(_JIECUNIT_FULL_VER)));
	{end}
END_TEST_S
```

### バージョンの更新

バージョンの更新は、リリース時に `release vX.Y.Z` という独立したコミットで行います。機能追加・修正のコミットでは更新しません。

1. `VERSION` ファイルを新しいバージョンに更新する。
2. `src/jiecunit_config.iec` のバージョンマクロを更新する。

   ```
   {#define _JIECUNIT true}
   {#define _JIECUNIT_FULL_VER XXXXX}  // MAJOR*10000 + MINOR*100 + PATCH
   {#define _JIECUNIT_VER XXX}          // MAJOR*100 + MINOR
   {#define _JIECUNIT_VERSION "X.Y.Z"}
   ```

3. 変更をコミットする（コミットメッセージは `release vX.Y.Z`）。
4. コミットにバージョン番号のタグを付ける: `git tag vX.Y.Z`

### セマンティックバージョニングの指針

- **MAJOR**: 互換性のない API の変更
- **MINOR**: 後方互換性のある機能の追加
- **PATCH**: 後方互換性のあるバグの修正

セマンティックバージョニングの詳細は https://semver.org/lang/ja/ を参照してください。

<a id="coding-rules"></a>
# コーディング規約

## 目次
1. [目的](#目的)
2. [コーディングスタイル](#コーディングスタイル)
3. [命名規則](#命名規則)
4. [フォーマット](#フォーマット)
5. [エラーハンドリング](#エラーハンドリング)
6. [テスト](#テスト)
7. [ドキュメント](#ドキュメント)
8. [依存関係](#依存関係)
9. [バージョン管理](#バージョン管理)

## 目的

このコーディング規約は、JiecUnitプロジェクトにおけるIEC 61131-3 ST言語コードの品質と一貫性を保つために定められています。

- コードの可読性と保守性の向上
- チーム開発における統一されたコーディングスタイルの確立
- 各社プログラミングツールとの互換性の確保
- 生成AIとの協調開発における効率性の向上
- テスト駆動開発（TDD）による品質保証

## コーディングスタイル

- ファンクションの戻り値に構造体型を使用しない。構造体データを結果として得る必要がある場合、var_in_outを使用する。
	- オムロン環境が未サポートのため。
- 時間リテラルは、`time#` を使用する。
    - 時間型の精度のメーカー間互換のため、CODESYSの場合、`time`を`ltime`に置換している。
- 論理式における or や and のオペランドが式の場合、括弧で括る。
```
if ((i = 0) and (j = 0)) or first_time then
	...
end_if;
```
- 一行で書くことができる注釈は、// ～ を使用する。複数行の注釈は、(\* ～ \*) を使用する。/\* ～ \*/ を使用しない。

## 命名規則

- 以下の名前で定義することを禁止する。
  - left, right
    - IEC 61131-3 の定義と重複するため。
  - `h`, `H`で始まり、`_`を含まない変数名
    - キーエンス環境の制約
  - ^\[rRtTcC\]\\d+$ にマッチする変数名
    - キーエンス環境の制約
  - `p\_`, `P\_`で始まる要素名
	- オムロン環境の制約。
　- アルファベット1文字の要素名。
    - キーエンス環境や三菱環境の制約。
- POU名は、64バイト以内とすること。
  - キーエンス環境の制約。
- IEC 61131-3は、ASCIIの大文字・小文字を区別しないことに注意すること。
	- 例えば、行列を意味する変数Aと、ベクトルを意味する変数aを同一のものとして解釈します。

## フォーマット

- インデントにはタブ文字を使用する。スペース文字によるインデントは使用しない。
- エディタのタブ幅設定は4文字とする。

## エラーハンドリング

- TBD

## テスト

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

- 1事実を1インスタンスでテストコードを記述する。
- 1関数のn事実を一つのTEST_S内に記述する。
  - オムロン環境にて、タスクの数が増えると登録に時間が掛かるため。
- 事実を1行のコメントで記述する。
- AAA形式で、Arrange節, Act節, Assert節を明示する。

## ドキュメント

- （生成AI）POUの先頭にdocプラグマを記述すること。
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

## 依存関係

- `{#include}`プリプロセッサ指令を使用してモジュール間の依存関係を明確にする。

## バージョン管理

- Gitを使用してソースコードを管理する。
- `main`ブランチは常にビルド可能で、テストが通る状態を維持する。
- タグを使用してリリースバージョンを管理する（例：v1.0.0）。
- `.gitignore`ファイルを適切に設定し、生成ファイル（*.xml、__pycache__など）をリポジトリに含めない。

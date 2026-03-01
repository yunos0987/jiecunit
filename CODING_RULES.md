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

- ファンクションの戻り値に構造体型を使用しないこと。構造体データを結果として得る必要がある場合、var_in_outを使用する。
	- オムロン環境が未サポートのため。
- 時間リテラルは、`time#` を使用する。
    - 時間型の精度のメーカー間互換のため、CODESYSの場合、`time`を`ltime`に置換している。
- 論理式における or や and のオペランドが式の場合、括弧で括る。
```
if ((i = 0) and (j = 0)) or first_time then
	...
end_if;
```
- 一行で書くことができる注釈は、// ～ を使用する。複数行の注釈は、(* ～ *) を使用する。/* ～ */ を使用しない。

## 命名規則

- "p_", "P_"で始まる名前で定義することを禁止する。
	- オムロン環境が禁止しているため。
- アルファベット一文字の名前で定義することを禁止する。
	- 三菱環境において問題が発生するため。

## フォーマット

- インデントにはタブ文字を使用する。スペース文字によるインデントは使用しない。
- エディタのタブ幅設定は4文字とする。

## エラーハンドリング

- TBD

## テスト

- TBD

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

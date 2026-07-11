# デイトレード練習・自動売買検証シミュレーター

ブラウザ上で動作する、デイトレード練習とルールベース売買戦略検証のためのローカルアプリです。OpenAI Codex を使って作成しています。

<video src="docs/assets/demo_movie.mov" controls width="960"></video>

[デモ動画を開く](https://github.com/user-attachments/assets/8d6db9ef-b70e-456d-a1af-a27ec49e3a4a)


## 使い方

```bash
conda env create -f environment.yml
conda activate sim
streamlit run app.py
```

ブラウザで `http://127.0.0.1:8501` を開きます。

## トラブルシュート

コード更新後に、最新版のはずなのに古い関数定義を参照するエラーが出る場合は、Streamlit の古いプロセスが残っている可能性があります。

```bash
pkill -f streamlit
conda activate sim
streamlit run app.py
```

## 詳細

機能、仕様、データ形式、再作成手順は [docs/APP_SPEC.md](docs/APP_SPEC.md) にまとめています。
デイトレード手法モードの詳細は [docs/daytrade_strategy_modes_spec_ja.md](docs/daytrade_strategy_modes_spec_ja.md) に分けて管理しています。
Android版は [docs/ANDROID_APP_SPEC.md](docs/ANDROID_APP_SPEC.md) を正本として、`feature/android-app` ブランチで開発します。

## Android版を初めて動かす手順

ここでは、MacでAndroid開発をしたことがない人を対象に、必要なソフトのインストールからアプリの起動までを説明します。

Android版は、次の2つを同時に動かします。

1. Mac上で動くモバイルAPI。株価データとシミュレーションを担当します。
2. Android Emulator上で動くAndroidアプリ。画面表示と操作を担当します。

### 1. 必要なソフトをインストールする

#### Miniconda

Python環境の管理にMinicondaを使います。すでにターミナルの先頭に `(base)` または `(sim)` と表示されている場合は、インストール済みなので次へ進んでください。

未導入の場合は、[Minicondaの公式ページ](https://docs.conda.io/projects/miniconda/en/latest/)からApple Silicon用のmacOSインストーラーを入手してインストールします。

#### Android Studio

[Android Studioの公式ページ](https://developer.android.com/studio)からmacOS版をダウンロードして、`Applications`フォルダーへインストールします。

初回起動時は、次の設定を選びます。

- Setup Type: `Standard`
- Android SDK: インストールする
- Android SDK Platform: API 35をインストールする
- Android Virtual Device: インストールする
- License Agreement: 内容を確認して同意する

Android Studioに付属するJDK 17を利用するため、通常はJavaを別途インストールする必要はありません。

### 2. このプロジェクトを準備する

ターミナルを開き、プロジェクトのフォルダーへ移動します。

```bash
cd /Users/tsujita/stock_simulator
```

初回だけ、Python環境を作成します。

```bash
conda env create -f environment.yml
```

すでに`sim`環境を作成済みの場合、上のコマンドは不要です。代わりに依存関係を更新できます。

```bash
conda activate sim
pip install -r requirements.txt
```

### 3. Android Studioでプロジェクトを開く

1. Android Studioを起動します。
2. `Open`をクリックします。
3. `/Users/tsujita/stock_simulator/android`を選択します。リポジトリ全体ではなく、`android`フォルダーを選びます。
4. `Trust Project`が表示された場合は、内容を確認して信頼します。
5. 画面下部の処理が終わるまで待ちます。初回はGradleやライブラリのダウンロードに時間がかかります。

Android Studioで一度プロジェクトを開くと、通常は`android/local.properties`が自動作成されます。このファイルにはAndroid SDKの場所が記録されます。

自動作成されなかった場合は、`android/local.properties`を作り、次の1行を記載します。

```properties
sdk.dir=/Users/tsujita/Library/Android/sdk
```

SDKを別の場所へインストールした場合は、その実際のパスを指定してください。`local.properties`はMacごとに異なる情報を含むため、Gitには追加しません。

### 4. Android Emulatorを作る

Android Studioで次の操作を行います。

1. メニューから `Tools` → `Device Manager`を開きます。
2. `Create Virtual Device`をクリックします。
3. `Phone`からPixelシリーズの端末を1つ選び、`Next`をクリックします。
4. API 35のシステムイメージを選びます。未導入の場合は、横にあるダウンロードボタンからインストールします。
5. `Finish`をクリックします。
6. Device Managerの再生ボタンを押し、Androidのホーム画面が表示されるまで待ちます。

Apple Silicon搭載Macでは、可能なら`arm64-v8a`のシステムイメージを選びます。

### 5. ターミナル1でモバイルAPIを起動する

1つ目のターミナルで次を実行します。

```bash
cd /Users/tsujita/stock_simulator
conda activate sim
uvicorn mobile_api.main:app --reload
```

次のように表示されれば成功です。

```text
Uvicorn running on http://127.0.0.1:8000
Application startup complete.
```

このターミナルはアプリ使用中に閉じないでください。APIを終了するときは `Control + C`を押します。

ブラウザで [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health) を開き、次の内容が表示されればAPIは正常です。

```json
{"status":"ok","api_version":"1"}
```

### 6. Android Studioからアプリを起動する

1. ターミナル1でAPIが動いていることを確認します。
2. Android Studio上部の端末選択欄から、先ほど作成したEmulatorを選びます。
3. 実行対象が`app`になっていることを確認します。
4. 上部の緑色の再生ボタンをクリックします。
5. ビルド完了後、Emulatorに`デイトレ練習`アプリが自動でインストールされて起動します。

Android Emulator内からMacのAPIへ接続するときは、`127.0.0.1`ではなく専用アドレス`10.0.2.2`を使います。このアプリは初期状態で`http://10.0.2.2:8000/api/v1/`へ接続するよう設定済みです。

アプリが開いたら、次の流れで動作を確認できます。

1. `新しい練習を始める`を押します。
2. 最初は`サンプル`データのままにします。
3. 銘柄コード`285A`、対象日`2026-06-24`を使います。
4. `データを読み込む`を押します。
5. 必要なら重要価格ラインを入力し、`練習を開始`を押します。
6. `1分進む`、`買い`、`空売り`、`全決済`などを操作します。

### 7. ターミナルからAPKを作る場合

Android Studioからアプリを起動できれば、この手順は必須ではありません。APKファイルだけを作りたい場合に使います。

まずAndroid Studioを一度起動して、SDKとJDKのインストールを完了してください。その後、ターミナルで次を実行します。

```bash
cd /Users/tsujita/stock_simulator/android
export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
./gradlew assembleDebug
```

成功すると、次の場所に開発用APKが作られます。

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

### Android版のよくあるエラー

#### `SDK location not found`

Android SDKの場所をGradleが見つけられていません。Android Studioで`android`フォルダーを一度開き、SDKのセットアップ完了を待ってください。

改善しない場合は、次を確認します。

```bash
ls ~/Library/Android/sdk
cat /Users/tsujita/stock_simulator/android/local.properties
```

`local.properties`がなければ、次の内容で作成します。

```properties
sdk.dir=/Users/tsujita/Library/Android/sdk
```

#### `JAVA_HOME is set to an invalid directory`または`No Java compiler found`

Android Studio付属のJDKを指定します。

```bash
export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
"$JAVA_HOME/bin/javac" -version
```

#### アプリに「サーバーに接続できません」と表示される

- ターミナル1でUvicornが動いているか確認します。
- ブラウザで`http://127.0.0.1:8000/api/v1/health`が開くか確認します。
- Emulatorを使っているか確認します。実機では`10.0.2.2`を利用できません。
- VPNやファイアウォールを一時的に確認します。

#### 実機で動かしたい

現在の初期設定はAndroid Emulator向けです。実機では`10.0.2.2`がMacを指さないため、MacのLAN内IPアドレスをAPI接続先へ設定し、UvicornをLANから接続可能な形で起動する必要があります。まずはEmulatorでの動作確認を推奨します。

Android版の詳しい仕様と今後の実装項目は [docs/ANDROID_APP_SPEC.md](docs/ANDROID_APP_SPEC.md) を参照してください。

## 売買戦略

- 押し目重視手法、標準デイトレ手法、積極ブレイク手法
- 15分足、30分足、60分足のボリンジャーバンド ±3σ での逆張り
- VWAP反発、直近高値ブレイク、前日高値ブレイク、出来高急増ブレイク
- VWAP と移動平均線を超えた場合の順張り
- 日足の重要価格ラインを上抜けた場合の買い
- 日足のレジスタンスライン接近時の余裕を持った売り
- 日足ボリンジャーバンド +3σ / -3σ 到達時の逆張り・利確
- 一定以上の損失が出た場合のロスカット

## 実データを用いた自動売買成績

全記録は [docs/REAL_DATA_BACKTESTS.md](docs/REAL_DATA_BACKTESTS.md) に保存します。

<!-- REAL_DATA_RESULTS_START -->
| 銘柄 | 日付 | 当日の特徴 | 前日比 | 戦略 | 損益 | 勝率 | 取引数 | チャート | メモ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 285A キオクシアホールディングス | 2026-07-10 | 下落 / 日中値幅 9.95% | -1,610.0円 (-2.07%) | 標準デイトレ手法 | -68,000円 | 40.0% | 5 | [チャート](docs/assets/backtests/285A_2026-07-10_combined_normal_chart.png) | 7/10のキオクシアホールディングスを更新後の標準デイトレ手法で検証 |
| 6976 太陽誘電 | 2026-07-10 | 下落 / 日中値幅 7.49% | -70.0円 (-0.48%) | 標準デイトレ手法 | -1,000円 | 25.0% | 4 | [チャート](docs/assets/backtests/6976_2026-07-10_combined_normal_chart.png) | 7/10の太陽誘電を更新後の標準デイトレ手法で検証 |
| 6981 村田製作所 | 2026-07-10 | 上昇 / 日中値幅 4.52% | +275.0円 (+2.90%) | 標準デイトレ手法 | -4,700円 | 36.4% | 11 | [チャート](docs/assets/backtests/6981_2026-07-10_combined_normal_chart.png) | 7/10の村田製作所を更新後の標準デイトレ手法で検証 |
| 8035 東京エレクトロン | 2026-07-10 | 上昇 / 日中値幅 4.07% | +1,500.0円 (+2.11%) | 標準デイトレ手法 | +158,000円 | 40.0% | 15 | [チャート](docs/assets/backtests/8035_2026-07-10_combined_normal_chart.png) | 7/10の東京エレクトロンを更新後の標準デイトレ手法で検証 |
<!-- REAL_DATA_RESULTS_END -->

## 注意

本アプリは過去データを使った練習・検証用です。実売買APIには接続せず、実際の投資判断を推奨するものではありません。

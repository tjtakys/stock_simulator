package com.tjtakys.stocksimulator.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import java.text.NumberFormat
import java.util.Locale

private object Routes {
    const val HOME = "home"
    const val SETUP = "setup"
    const val KEY_LINES = "key-lines"
    const val REPLAY = "replay"
    const val RESULT = "result"
    const val HISTORY = "history"
    const val SETTINGS = "settings"
}

@Composable
fun StockSimulatorApp(viewModel: ReplayViewModel = hiltViewModel()) {
    val navController = rememberNavController()
    NavHost(navController, startDestination = Routes.HOME) {
        composable(Routes.HOME) { HomeScreen(navController) }
        composable(Routes.SETUP) { SetupScreen(navController, viewModel) }
        composable(Routes.KEY_LINES) { KeyLinesScreen { navController.navigate(Routes.REPLAY) } }
        composable(Routes.REPLAY) { ReplayScreen(navController, viewModel) }
        composable(Routes.RESULT) { ResultScreen(navController, viewModel) }
        composable(Routes.HISTORY) { HistoryScreen(navController, viewModel) }
        composable(Routes.SETTINGS) { SettingsScreen(navController) }
    }
}

@Composable
private fun HomeScreen(nav: NavHostController) = AppScaffold("デイトレ練習") {
    Column(Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text("過去データで、未来を見ずに売買判断を練習します。", style = MaterialTheme.typography.titleMedium)
        Card(Modifier.fillMaxWidth()) {
            Text(
                "本アプリはシミュレーション専用です。実際の証券口座への注文や投資助言は行いません。",
                Modifier.padding(16.dp),
            )
        }
        Button(onClick = { nav.navigate(Routes.SETUP) }, modifier = Modifier.fillMaxWidth().height(52.dp)) {
            Text("新しい練習を始める")
        }
        OutlinedButton(onClick = { nav.navigate(Routes.HISTORY) }, modifier = Modifier.fillMaxWidth().height(52.dp)) {
            Text("練習履歴")
        }
        TextButton(onClick = { nav.navigate(Routes.SETTINGS) }, modifier = Modifier.fillMaxWidth()) { Text("設定") }
    }
}

@Composable
private fun SetupScreen(nav: NavHostController, viewModel: ReplayViewModel) {
    val form by viewModel.form.collectAsState()
    val state by viewModel.uiState.collectAsState()
    AppScaffold("練習設定", onBack = { nav.popBackStack() }) {
        LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            item {
                OutlinedTextField(
                    value = form.symbol,
                    onValueChange = { value -> viewModel.updateForm { it.copy(symbol = value) } },
                    label = { Text("銘柄コード") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            item {
                OutlinedTextField(
                    value = form.tradingDate,
                    onValueChange = { value -> viewModel.updateForm { it.copy(tradingDate = value) } },
                    label = { Text("対象日（YYYY-MM-DD）") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            item {
                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.weight(1f)) { Text("データ種別"); Text(if (form.dataSource == "sample") "サンプル" else "Yahoo実データ") }
                    Switch(
                        checked = form.dataSource == "yahoo",
                        onCheckedChange = { checked -> viewModel.updateForm { it.copy(dataSource = if (checked) "yahoo" else "sample") } },
                    )
                }
            }
            item {
                OutlinedTextField(
                    value = form.initialCash,
                    onValueChange = { value -> viewModel.updateForm { it.copy(initialCash = value.filter(Char::isDigit)) } },
                    label = { Text("初期入金額（円）") },
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            item {
                OutlinedTextField(
                    value = form.orderQuantity,
                    onValueChange = { value -> viewModel.updateForm { it.copy(orderQuantity = value.filter(Char::isDigit)) } },
                    label = { Text("注文株数") },
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            item {
                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
                    Text("重要価格ラインを使う", Modifier.weight(1f))
                    Switch(form.useKeyLines, { checked -> viewModel.updateForm { it.copy(useKeyLines = checked) } })
                }
            }
            if (state is ReplayUiState.Error) item { Text((state as ReplayUiState.Error).message, color = MaterialTheme.colorScheme.error) }
            item {
                Button(
                    onClick = {
                        viewModel.start {
                            nav.navigate(if (form.useKeyLines) Routes.KEY_LINES else Routes.REPLAY)
                        }
                    },
                    enabled = state !is ReplayUiState.Loading,
                    modifier = Modifier.fillMaxWidth().height(52.dp),
                ) {
                    if (state is ReplayUiState.Loading) CircularProgressIndicator(Modifier.height(24.dp)) else Text("データを読み込む")
                }
            }
        }
    }
}

@Composable
private fun KeyLinesScreen(onComplete: () -> Unit) = AppScaffold("重要価格ライン") {
    val lines = remember { mutableStateListOf<Pair<String, String>>() }
    var price by remember { mutableStateOf("") }
    var label by remember { mutableStateOf("サポートライン") }
    LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item { Text("日足チャートのタップ選択は次の改善で追加します。MVPでは価格を直接入力して水平線を設定できます。") }
        item {
            OutlinedTextField(price, { price = it.filter { char -> char.isDigit() || char == '.' } }, label = { Text("価格（円）") }, modifier = Modifier.fillMaxWidth())
        }
        item { OutlinedTextField(label, { label = it }, label = { Text("ラベル") }, modifier = Modifier.fillMaxWidth()) }
        item {
            OutlinedButton(
                onClick = { if (price.toDoubleOrNull() != null) { lines += label to price; price = "" } },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("ラインを追加") }
        }
        items(lines) { line ->
            Card(Modifier.fillMaxWidth()) {
                Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text("${line.first}: ${line.second}円", Modifier.weight(1f))
                    TextButton(onClick = { lines.remove(line) }) { Text("削除") }
                }
            }
        }
        item { Button(onClick = onComplete, modifier = Modifier.fillMaxWidth().height(52.dp)) { Text("練習を開始") } }
    }
}

@Composable
private fun ReplayScreen(nav: NavHostController, viewModel: ReplayViewModel) {
    val uiState by viewModel.uiState.collectAsState()
    val snackbar = remember { SnackbarHostState() }
    val content = uiState as? ReplayUiState.Content
    LaunchedEffect(content?.state?.lastMessage) { content?.state?.lastMessage?.let { snackbar.showSnackbar(it) } }
    AppScaffold("リプレイ", onBack = { viewModel.stopPlayback(); nav.popBackStack() }, snackbarHost = { SnackbarHost(snackbar) }) {
        when (val state = uiState) {
            ReplayUiState.Idle, ReplayUiState.Loading -> Column(Modifier.fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) { CircularProgressIndicator() }
            is ReplayUiState.Error -> ErrorPanel(state.message) { nav.navigate(Routes.SETUP) }
            is ReplayUiState.Content -> ReplayContent(
                state = state,
                command = { command -> viewModel.command(command) { nav.navigate(Routes.RESULT) } },
                togglePlay = { viewModel.togglePlayback(onFinished = { nav.navigate(Routes.RESULT) }) },
                finish = { viewModel.command("FINISH") { nav.navigate(Routes.RESULT) } },
            )
        }
    }
}

@Composable
private fun ReplayContent(
    state: ReplayUiState.Content,
    command: (String) -> Unit,
    togglePlay: () -> Unit,
    finish: () -> Unit,
) {
    val data = state.state
    LazyColumn(Modifier.fillMaxSize().padding(horizontal = 12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("${data.symbol}  ${data.tradingDate}", fontWeight = FontWeight.Bold)
                Text(data.timestamp.substringAfter("T").take(5))
            }
        }
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Metric("確定損益", yen(data.realizedPnl), data.realizedPnl)
                Metric("含み損益", yen(data.unrealizedPnl), data.unrealizedPnl)
                Metric("買付余力", yen(data.availableCash))
            }
        }
        item { CandlestickChart(data.minuteBars, Modifier.fillMaxWidth()) }
        item {
            Card(Modifier.fillMaxWidth()) {
                Text(
                    if (data.position.side == "FLAT") "建玉なし" else "${if (data.position.side == "LONG") "買い" else "空売り"} ${data.position.quantity}株 / 平均 ${yen(data.position.entryPrice ?: 0.0)}",
                    Modifier.padding(14.dp),
                )
            }
        }
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button({ command("BUY") }, Modifier.weight(1f).height(52.dp), enabled = !state.isPlaying) { Text("買い") }
                Button({ command("SELL_SHORT") }, Modifier.weight(1f).height(52.dp), enabled = !state.isPlaying) { Text("空売り") }
                OutlinedButton({ command("CLOSE") }, Modifier.weight(1f).height(52.dp), enabled = !state.isPlaying && data.position.side != "FLAT") { Text("全決済") }
            }
        }
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton({ command("STEP_BACK") }, Modifier.weight(1f).height(48.dp), enabled = !state.isPlaying) { Text("1分戻る") }
                OutlinedButton({ command("STEP_FORWARD") }, Modifier.weight(1f).height(48.dp), enabled = !state.isPlaying && !data.done) { Text("1分進む") }
                Button(togglePlay, Modifier.weight(1f).height(48.dp), enabled = !data.done) { Text(if (state.isPlaying) "一時停止" else "再生") }
            }
        }
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton({ command("RESET") }, Modifier.weight(1f)) { Text("リセット") }
                TextButton(finish, Modifier.weight(1f)) { Text("練習終了") }
            }
        }
        item { Spacer(Modifier.height(20.dp)) }
    }
}

@Composable
private fun ResultScreen(nav: NavHostController, viewModel: ReplayViewModel) {
    val uiState by viewModel.uiState.collectAsState()
    val data = (uiState as? ReplayUiState.Content)?.state
    AppScaffold("練習結果") {
        if (data == null) ErrorPanel("結果がありません。") { nav.navigate(Routes.HOME) } else {
            val wins = data.trades.count { it.pnl > 0 }
            val winRate = if (data.trades.isEmpty()) 0.0 else wins * 100.0 / data.trades.size
            LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                item { Text(yen(data.realizedPnl), style = MaterialTheme.typography.displaySmall, color = pnlColor(data.realizedPnl)) }
                item { Text("${data.symbol}  ${data.tradingDate}") }
                item { Text("勝率 ${"%.1f".format(winRate)}% / 取引 ${data.trades.size}回") }
                item { CandlestickChart(data.minuteBars, Modifier.fillMaxWidth()) }
                items(data.trades) { trade ->
                    Card(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(12.dp)) {
                            Text("${if (trade.side == "LONG") "買い" else "空売り"} ${trade.quantity}株")
                            Text("${yen(trade.entryPrice)} → ${yen(trade.exitPrice)}  ${yen(trade.pnl)}", color = pnlColor(trade.pnl))
                        }
                    }
                }
                item { Button({ nav.navigate(Routes.SETUP) }, Modifier.fillMaxWidth()) { Text("同じ条件でもう一度") } }
                item { OutlinedButton({ nav.navigate(Routes.HOME) { popUpTo(Routes.HOME) { inclusive = true } } }, Modifier.fillMaxWidth()) { Text("ホームへ戻る") } }
            }
        }
    }
}

@Composable
private fun HistoryScreen(nav: NavHostController, viewModel: ReplayViewModel) {
    val history by viewModel.history.collectAsState()
    AppScaffold("練習履歴", onBack = { nav.popBackStack() }) {
        if (history.isEmpty()) Column(Modifier.fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) { Text("保存された練習履歴はありません。") }
        else LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            items(history, key = { it.sessionId }) { item ->
                Card(Modifier.fillMaxWidth()) {
                    Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text("${item.symbol}  ${item.tradingDate}", fontWeight = FontWeight.Bold)
                            Text("${yen(item.realizedPnl)} / 勝率 ${"%.1f".format(item.winRate)}% / ${item.tradeCount}回", color = pnlColor(item.realizedPnl))
                        }
                        TextButton({ viewModel.deleteHistory(item.sessionId) }) { Text("削除") }
                    }
                }
            }
        }
    }
}

@Composable
private fun SettingsScreen(nav: NavHostController) = AppScaffold("設定", onBack = { nav.popBackStack() }) {
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("テーマは端末設定に合わせます。")
        HorizontalDivider()
        Text("API接続先（開発用）")
        Text("Android Emulator: http://10.0.2.2:8000", style = MaterialTheme.typography.bodySmall)
        HorizontalDivider()
        Text("デイトレ練習 Android 0.1.0")
        Text("過去データを用いた学習・検証専用です。")
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AppScaffold(
    title: String,
    onBack: (() -> Unit)? = null,
    snackbarHost: @Composable () -> Unit = {},
    content: @Composable () -> Unit,
) {
    Scaffold(
        topBar = { TopAppBar(title = { Text(title) }, navigationIcon = { if (onBack != null) TextButton(onBack) { Text("戻る") } }) },
        snackbarHost = snackbarHost,
    ) { padding -> Column(Modifier.padding(padding)) { content() } }
}

@Composable
private fun Metric(label: String, value: String, pnl: Double? = null) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(label, style = MaterialTheme.typography.labelSmall)
        Text(value, color = pnl?.let(::pnlColor) ?: MaterialTheme.colorScheme.onSurface, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun ErrorPanel(message: String, action: () -> Unit) {
    Column(Modifier.fillMaxSize().padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
        Text(message, color = MaterialTheme.colorScheme.error)
        Spacer(Modifier.height(16.dp))
        Button(action) { Text("戻る") }
    }
}

private val yenFormatter = NumberFormat.getNumberInstance(Locale.JAPAN).apply { maximumFractionDigits = 0 }
private fun yen(value: Double): String = "${if (value > 0) "+" else ""}${yenFormatter.format(value)}円"
private fun pnlColor(value: Double): Color = when {
    value > 0 -> Color(0xFFD32F2F)
    value < 0 -> Color(0xFF1B8A3A)
    else -> Color.Gray
}

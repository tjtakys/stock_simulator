package com.tjtakys.stocksimulator.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tjtakys.stocksimulator.data.local.PracticeHistoryEntity
import com.tjtakys.stocksimulator.data.remote.CreateSessionRequest
import com.tjtakys.stocksimulator.data.remote.ReplayStateDto
import com.tjtakys.stocksimulator.data.repository.ReplayRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SetupForm(
    val symbol: String = "285A",
    val tradingDate: String = "2026-06-24",
    val dataSource: String = "sample",
    val initialCash: String = "10000000",
    val orderQuantity: String = "100",
    val useKeyLines: Boolean = true,
)

sealed interface ReplayUiState {
    data object Idle : ReplayUiState
    data object Loading : ReplayUiState
    data class Content(val state: ReplayStateDto, val isPlaying: Boolean = false) : ReplayUiState
    data class Error(val message: String) : ReplayUiState
}

@HiltViewModel
class ReplayViewModel @Inject constructor(private val repository: ReplayRepository) : ViewModel() {
    private val _form = MutableStateFlow(SetupForm())
    val form: StateFlow<SetupForm> = _form.asStateFlow()
    private val _uiState = MutableStateFlow<ReplayUiState>(ReplayUiState.Idle)
    val uiState: StateFlow<ReplayUiState> = _uiState.asStateFlow()
    val history: StateFlow<List<PracticeHistoryEntity>> = repository.history()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    private var playJob: Job? = null

    fun updateForm(transform: (SetupForm) -> SetupForm) { _form.value = transform(_form.value) }

    fun start(onStarted: () -> Unit) {
        val form = _form.value
        val cash = form.initialCash.toDoubleOrNull()
        val quantity = form.orderQuantity.toIntOrNull()
        if (form.symbol.isBlank() || cash == null || cash <= 0 || quantity == null || quantity <= 0) {
            _uiState.value = ReplayUiState.Error("銘柄、入金額、注文株数を正しく入力してください。")
            return
        }
        viewModelScope.launch {
            _uiState.value = ReplayUiState.Loading
            runCatching {
                repository.create(
                    CreateSessionRequest(
                        symbol = form.symbol.trim().uppercase(),
                        tradingDate = form.tradingDate,
                        dataSource = form.dataSource,
                        initialCash = cash,
                        orderQuantity = quantity,
                    ),
                )
            }.onSuccess {
                _uiState.value = ReplayUiState.Content(it)
                onStarted()
            }.onFailure { _uiState.value = ReplayUiState.Error(errorMessage(it)) }
        }
    }

    fun command(command: String, onFinished: (() -> Unit)? = null) {
        val content = _uiState.value as? ReplayUiState.Content ?: return
        if (content.state.done && command != "RESET") return
        viewModelScope.launch {
            runCatching { repository.command(content.state.sessionId, command) }
                .onSuccess { state ->
                    _uiState.value = ReplayUiState.Content(state, isPlaying = content.isPlaying)
                    if (state.done) {
                        stopPlayback()
                        repository.saveResult(state)
                        onFinished?.invoke()
                    }
                }
                .onFailure {
                    stopPlayback()
                    _uiState.value = ReplayUiState.Error(errorMessage(it))
                }
        }
    }

    fun togglePlayback(intervalMillis: Long = 750L, onFinished: () -> Unit) {
        val content = _uiState.value as? ReplayUiState.Content ?: return
        if (playJob != null) {
            stopPlayback()
            return
        }
        _uiState.value = content.copy(isPlaying = true)
        playJob = viewModelScope.launch {
            while (true) {
                val current = (_uiState.value as? ReplayUiState.Content)?.state ?: break
                if (current.done) break
                runCatching { repository.command(current.sessionId, "STEP_FORWARD") }
                    .onSuccess {
                        _uiState.value = ReplayUiState.Content(it, isPlaying = true)
                        if (it.done) {
                            repository.saveResult(it)
                            onFinished()
                            return@launch
                        }
                    }
                    .onFailure {
                        _uiState.value = ReplayUiState.Error(errorMessage(it))
                        return@launch
                    }
                delay(intervalMillis)
            }
        }.also { job -> job.invokeOnCompletion { playJob = null } }
    }

    fun stopPlayback() {
        playJob?.cancel()
        playJob = null
        val content = _uiState.value as? ReplayUiState.Content ?: return
        _uiState.value = content.copy(isPlaying = false)
    }

    fun saveResult() {
        val state = (_uiState.value as? ReplayUiState.Content)?.state ?: return
        viewModelScope.launch { repository.saveResult(state) }
    }

    fun deleteHistory(id: String) { viewModelScope.launch { repository.deleteHistory(id) } }

    private fun errorMessage(throwable: Throwable): String = when {
        throwable.message?.contains("Unable to resolve host") == true -> "サーバーに接続できません。APIの起動と通信状態を確認してください。"
        throwable.message?.contains("timeout", ignoreCase = true) == true -> "通信がタイムアウトしました。もう一度お試しください。"
        else -> throwable.message ?: "予期しないエラーが発生しました。"
    }

    override fun onCleared() {
        playJob?.cancel()
        super.onCleared()
    }
}

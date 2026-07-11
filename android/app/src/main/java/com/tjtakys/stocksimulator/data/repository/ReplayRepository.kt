package com.tjtakys.stocksimulator.data.repository

import com.tjtakys.stocksimulator.data.local.PracticeHistoryDao
import com.tjtakys.stocksimulator.data.local.PracticeHistoryEntity
import com.tjtakys.stocksimulator.data.remote.CreateSessionRequest
import com.tjtakys.stocksimulator.data.remote.MobileApi
import com.tjtakys.stocksimulator.data.remote.ReplayCommandRequest
import com.tjtakys.stocksimulator.data.remote.ReplayStateDto
import kotlinx.coroutines.flow.Flow
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ReplayRepository @Inject constructor(
    private val api: MobileApi,
    private val historyDao: PracticeHistoryDao,
) {
    suspend fun create(request: CreateSessionRequest): ReplayStateDto = api.createSession(request)

    suspend fun command(sessionId: String, command: String): ReplayStateDto = api.command(
        sessionId,
        ReplayCommandRequest(commandId = UUID.randomUUID().toString(), command = command),
    )

    suspend fun saveResult(state: ReplayStateDto) {
        val wins = state.trades.count { it.pnl > 0 }
        historyDao.upsert(
            PracticeHistoryEntity(
                sessionId = state.sessionId,
                symbol = state.symbol,
                tradingDate = state.tradingDate,
                completedAt = System.currentTimeMillis(),
                realizedPnl = state.realizedPnl,
                winRate = if (state.trades.isEmpty()) 0.0 else wins * 100.0 / state.trades.size,
                tradeCount = state.trades.size,
            ),
        )
    }

    fun history(): Flow<List<PracticeHistoryEntity>> = historyDao.observeAll()
    suspend fun deleteHistory(id: String) = historyDao.delete(id)
}

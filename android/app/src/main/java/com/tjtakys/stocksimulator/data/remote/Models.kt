package com.tjtakys.stocksimulator.data.remote

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class CreateSessionRequest(
    val symbol: String,
    @SerialName("trading_date") val tradingDate: String,
    @SerialName("data_source") val dataSource: String,
    @SerialName("initial_cash") val initialCash: Double,
    @SerialName("order_quantity") val orderQuantity: Int,
)

@Serializable
data class ReplayCommandRequest(
    @SerialName("command_id") val commandId: String,
    val command: String,
)

@Serializable
data class BarDto(
    val timestamp: String,
    val open: Double,
    val high: Double,
    val low: Double,
    val close: Double,
    val volume: Long,
    val vwap: Double? = null,
    @SerialName("ma_5") val ma5: Double? = null,
    @SerialName("ma_25") val ma25: Double? = null,
    @SerialName("ma_75") val ma75: Double? = null,
    @SerialName("bb_upper_3") val bbUpper3: Double? = null,
    @SerialName("bb_lower_3") val bbLower3: Double? = null,
)

@Serializable
data class PositionDto(
    val side: String,
    val quantity: Int,
    @SerialName("entry_price") val entryPrice: Double? = null,
    @SerialName("entry_time") val entryTime: String? = null,
)

@Serializable
data class FillDto(
    val timestamp: String,
    val symbol: String,
    val action: String,
    val side: String,
    val quantity: Int,
    val price: Double,
    val pnl: Double? = null,
)

@Serializable
data class TradeDto(
    val symbol: String,
    @SerialName("entry_time") val entryTime: String,
    @SerialName("exit_time") val exitTime: String,
    val side: String,
    val quantity: Int,
    @SerialName("entry_price") val entryPrice: Double,
    @SerialName("exit_price") val exitPrice: Double,
    val pnl: Double,
)

@Serializable
data class ReplayStateDto(
    @SerialName("session_id") val sessionId: String,
    val revision: Long,
    val symbol: String,
    @SerialName("trading_date") val tradingDate: String,
    val timestamp: String,
    @SerialName("current_price") val currentPrice: Double,
    @SerialName("minute_bars") val minuteBars: List<BarDto>,
    val position: PositionDto,
    val fills: List<FillDto>,
    val trades: List<TradeDto>,
    @SerialName("realized_pnl") val realizedPnl: Double,
    @SerialName("unrealized_pnl") val unrealizedPnl: Double,
    val equity: Double,
    @SerialName("initial_cash") val initialCash: Double,
    @SerialName("available_cash") val availableCash: Double,
    @SerialName("committed_notional") val committedNotional: Double,
    val done: Boolean,
    @SerialName("last_message") val lastMessage: String? = null,
)

package com.tjtakys.stocksimulator.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.tjtakys.stocksimulator.data.remote.BarDto
import kotlin.math.max

@Composable
fun CandlestickChart(bars: List<BarDto>, modifier: Modifier = Modifier) {
    if (bars.isEmpty()) {
        Box(modifier.height(280.dp), contentAlignment = Alignment.Center) { Text("チャートデータがありません") }
        return
    }
    val visible = bars.takeLast(60)
    val latest = visible.last()
    val description = "現在値 ${latest.close.toInt()}円、始値 ${latest.open.toInt()}円、高値 ${latest.high.toInt()}円、安値 ${latest.low.toInt()}円、出来高 ${latest.volume}"
    val grid = MaterialTheme.colorScheme.outlineVariant
    val indicator = MaterialTheme.colorScheme.primary
    Canvas(
        modifier = modifier
            .height(300.dp)
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.surface)
            .semantics { contentDescription = description },
    ) {
        val chartHeight = size.height * 0.78f
        val volumeTop = size.height * 0.82f
        val minPrice = visible.minOf { it.low }
        val maxPrice = visible.maxOf { it.high }
        val priceRange = max(maxPrice - minPrice, 1.0)
        val maxVolume = max(visible.maxOf { it.volume }.toDouble(), 1.0)
        val slot = size.width / visible.size
        val candleWidth = (slot * 0.62f).coerceAtLeast(2f)
        fun y(price: Double) = (chartHeight - ((price - minPrice) / priceRange * chartHeight)).toFloat()

        repeat(5) { index ->
            val gy = chartHeight * index / 4f
            drawLine(grid, Offset(0f, gy), Offset(size.width, gy), strokeWidth = 1f)
        }
        visible.forEachIndexed { index, bar ->
            val x = slot * index + slot / 2f
            val color = when {
                bar.close > bar.open -> Color(0xFFD32F2F)
                bar.close < bar.open -> Color(0xFF1B8A3A)
                else -> Color.Gray
            }
            drawLine(color, Offset(x, y(bar.high)), Offset(x, y(bar.low)), strokeWidth = 2f)
            val top = minOf(y(bar.open), y(bar.close))
            val bodyHeight = max(kotlin.math.abs(y(bar.close) - y(bar.open)), 2f)
            drawRect(color, Offset(x - candleWidth / 2f, top), Size(candleWidth, bodyHeight))
            val volumeHeight = ((bar.volume / maxVolume) * (size.height - volumeTop)).toFloat()
            drawRect(color.copy(alpha = 0.55f), Offset(x - candleWidth / 2f, size.height - volumeHeight), Size(candleWidth, volumeHeight))
        }
        val vwapPath = Path()
        var started = false
        visible.forEachIndexed { index, bar ->
            bar.vwap?.let { value ->
                val point = Offset(slot * index + slot / 2f, y(value))
                if (!started) { vwapPath.moveTo(point.x, point.y); started = true } else vwapPath.lineTo(point.x, point.y)
            }
        }
        if (started) drawPath(vwapPath, indicator, style = Stroke(width = 3f))
    }
}

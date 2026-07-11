package com.tjtakys.stocksimulator.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = Color(0xFF1558B0),
    secondary = Color(0xFF386A20),
    error = Color(0xFFBA1A1A),
)
private val DarkColors = darkColorScheme(primary = Color(0xFFA9C7FF), secondary = Color(0xFFA5D18A))

@Composable
fun StockSimulatorTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (isSystemInDarkTheme()) DarkColors else LightColors, content = content)
}

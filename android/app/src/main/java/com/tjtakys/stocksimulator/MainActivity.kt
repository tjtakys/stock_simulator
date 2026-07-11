package com.tjtakys.stocksimulator

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.tjtakys.stocksimulator.ui.StockSimulatorApp
import com.tjtakys.stocksimulator.ui.theme.StockSimulatorTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent { StockSimulatorTheme { StockSimulatorApp() } }
    }
}

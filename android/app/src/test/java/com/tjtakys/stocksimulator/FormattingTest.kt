package com.tjtakys.stocksimulator

import com.tjtakys.stocksimulator.data.remote.ReplayCommandRequest
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Test

class FormattingTest {
    @Test
    fun commandUsesApiFieldNames() {
        val json = Json.encodeToString(ReplayCommandRequest("one", "BUY"))
        assertEquals("{\"command_id\":\"one\",\"command\":\"BUY\"}", json)
    }
}

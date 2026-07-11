package com.tjtakys.stocksimulator.data.remote

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface MobileApi {
    @POST("replay-sessions")
    suspend fun createSession(@Body request: CreateSessionRequest): ReplayStateDto

    @GET("replay-sessions/{id}")
    suspend fun getSession(@Path("id") sessionId: String): ReplayStateDto

    @POST("replay-sessions/{id}/commands")
    suspend fun command(
        @Path("id") sessionId: String,
        @Body request: ReplayCommandRequest,
    ): ReplayStateDto
}

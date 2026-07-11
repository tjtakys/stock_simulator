package com.tjtakys.stocksimulator.data.local

import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.RoomDatabase
import kotlinx.coroutines.flow.Flow

@Entity(tableName = "practice_history")
data class PracticeHistoryEntity(
    @androidx.room.PrimaryKey val sessionId: String,
    val symbol: String,
    val tradingDate: String,
    val completedAt: Long,
    val realizedPnl: Double,
    val winRate: Double,
    val tradeCount: Int,
)

@Dao
interface PracticeHistoryDao {
    @Query("SELECT * FROM practice_history ORDER BY completedAt DESC")
    fun observeAll(): Flow<List<PracticeHistoryEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(item: PracticeHistoryEntity)

    @Query("DELETE FROM practice_history WHERE sessionId = :sessionId")
    suspend fun delete(sessionId: String)
}

@Database(entities = [PracticeHistoryEntity::class], version = 1, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun practiceHistoryDao(): PracticeHistoryDao
}

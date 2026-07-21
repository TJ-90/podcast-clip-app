package com.tj90.podcastclip.data.local

import android.content.ContentValues
import android.content.Context
import android.database.Cursor
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import com.tj90.podcastclip.model.Clip
import com.tj90.podcastclip.model.Episode
import com.tj90.podcastclip.model.ParsedFeed
import com.tj90.podcastclip.model.PlaybackBookmark
import com.tj90.podcastclip.model.Podcast
import com.tj90.podcastclip.model.TranscriptState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

class PodcastStore(context: Context) :
    SQLiteOpenHelper(context.applicationContext, "podcast-clips.db", null, DATABASE_VERSION) {

    private val mutablePodcasts = MutableStateFlow<List<Podcast>>(emptyList())
    private val mutableEpisodes = MutableStateFlow<List<Episode>>(emptyList())
    private val mutableClips = MutableStateFlow<List<Clip>>(emptyList())
    private val mutableQueue = MutableStateFlow<List<Episode>>(emptyList())

    val podcasts: StateFlow<List<Podcast>> = mutablePodcasts
    val episodes: StateFlow<List<Episode>> = mutableEpisodes
    val clips: StateFlow<List<Clip>> = mutableClips
    val queue: StateFlow<List<Episode>> = mutableQueue

    init {
        writableDatabase
        markInterruptedTranscriptions()
        refreshSnapshot()
    }

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(
            """
            CREATE TABLE podcasts (
                feed_url TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                description TEXT NOT NULL,
                artwork_url TEXT NOT NULL,
                subscribed_at INTEGER NOT NULL
            )
            """.trimIndent()
        )
        db.execSQL(
            """
            CREATE TABLE episodes (
                id TEXT PRIMARY KEY,
                podcast_feed_url TEXT NOT NULL,
                podcast_title TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                audio_url TEXT NOT NULL,
                artwork_url TEXT NOT NULL,
                published_at INTEGER NOT NULL,
                duration_ms INTEGER NOT NULL,
                downloaded_path TEXT NOT NULL DEFAULT ''
            )
            """.trimIndent()
        )
        db.execSQL(
            """
            CREATE TABLE clips (
                id TEXT PRIMARY KEY,
                episode_id TEXT NOT NULL,
                episode_title TEXT NOT NULL,
                podcast_title TEXT NOT NULL,
                artwork_url TEXT NOT NULL,
                file_path TEXT NOT NULL,
                start_ms INTEGER NOT NULL,
                end_ms INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                transcript TEXT NOT NULL,
                transcript_state TEXT NOT NULL,
                transcript_error TEXT NOT NULL
            )
            """.trimIndent()
        )
        db.execSQL(
            """
            CREATE TABLE playback_queue (
                episode_id TEXT PRIMARY KEY,
                queued_at INTEGER NOT NULL
            )
            """.trimIndent()
        )
        db.execSQL(
            """
            CREATE TABLE playback_bookmark (
                slot INTEGER PRIMARY KEY CHECK(slot = 1),
                episode_id TEXT NOT NULL,
                position_ms INTEGER NOT NULL,
                speed REAL NOT NULL
            )
            """.trimIndent()
        )
        db.execSQL("CREATE INDEX episodes_feed_index ON episodes(podcast_feed_url)")
        db.execSQL("CREATE INDEX episodes_published_index ON episodes(published_at DESC)")
        db.execSQL("CREATE INDEX clips_created_index ON clips(created_at DESC)")
        db.execSQL("CREATE INDEX queue_order_index ON playback_queue(queued_at)")
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        if (oldVersion < 2) {
            db.execSQL("ALTER TABLE episodes ADD COLUMN downloaded_path TEXT NOT NULL DEFAULT ''")
            db.execSQL(
                "CREATE TABLE playback_queue (episode_id TEXT PRIMARY KEY, queued_at INTEGER NOT NULL)"
            )
            db.execSQL(
                """
                CREATE TABLE playback_bookmark (
                    slot INTEGER PRIMARY KEY CHECK(slot = 1),
                    episode_id TEXT NOT NULL,
                    position_ms INTEGER NOT NULL,
                    speed REAL NOT NULL
                )
                """.trimIndent()
            )
            db.execSQL("CREATE INDEX queue_order_index ON playback_queue(queued_at)")
        }
    }

    @Synchronized
    fun upsertFeed(feed: ParsedFeed) {
        val db = writableDatabase
        db.beginTransaction()
        try {
            db.insertWithOnConflict(
                "podcasts",
                null,
                ContentValues().apply {
                    put("feed_url", feed.podcast.feedUrl)
                    put("title", feed.podcast.title)
                    put("author", feed.podcast.author)
                    put("description", feed.podcast.description)
                    put("artwork_url", feed.podcast.artworkUrl)
                    put("subscribed_at", feed.podcast.subscribedAt)
                },
                SQLiteDatabase.CONFLICT_REPLACE
            )
            feed.episodes.forEach { episode ->
                val localPath = findEpisode(episode.id, db)?.downloadedPath.orEmpty()
                db.insertWithOnConflict(
                    "episodes",
                    null,
                    episodeValues(episode.copy(downloadedPath = localPath)),
                    SQLiteDatabase.CONFLICT_REPLACE
                )
            }
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
        refreshSnapshot()
    }

    @Synchronized
    fun saveDownloadedPath(episodeId: String, path: String) {
        writableDatabase.update(
            "episodes",
            ContentValues().apply { put("downloaded_path", path) },
            "id = ?",
            arrayOf(episodeId)
        )
        refreshSnapshot()
    }

    @Synchronized
    fun enqueue(episodeId: String) {
        writableDatabase.insertWithOnConflict(
            "playback_queue",
            null,
            ContentValues().apply {
                put("episode_id", episodeId)
                put("queued_at", System.currentTimeMillis())
            },
            SQLiteDatabase.CONFLICT_REPLACE
        )
        refreshSnapshot()
    }

    @Synchronized
    fun removeFromQueue(episodeId: String) {
        writableDatabase.delete("playback_queue", "episode_id = ?", arrayOf(episodeId))
        refreshSnapshot()
    }

    @Synchronized
    fun clearQueue() {
        writableDatabase.delete("playback_queue", null, null)
        refreshSnapshot()
    }

    @Synchronized
    fun savePlaybackBookmark(bookmark: PlaybackBookmark) {
        writableDatabase.insertWithOnConflict(
            "playback_bookmark",
            null,
            ContentValues().apply {
                put("slot", 1)
                put("episode_id", bookmark.episodeId)
                put("position_ms", bookmark.positionMs.coerceAtLeast(0))
                put("speed", bookmark.speed.coerceIn(0.5f, 3f))
            },
            SQLiteDatabase.CONFLICT_REPLACE
        )
    }

    fun loadPlaybackBookmark(): PlaybackBookmark? =
        readableDatabase.query(
            "playback_bookmark",
            null,
            "slot = 1",
            null,
            null,
            null,
            null,
            "1"
        ).use { cursor ->
            if (!cursor.moveToFirst()) null
            else PlaybackBookmark(
                episodeId = cursor.string("episode_id"),
                positionMs = cursor.long("position_ms"),
                speed = cursor.getFloat(cursor.getColumnIndexOrThrow("speed"))
            )
        }

    fun findEpisode(episodeId: String): Episode? = findEpisode(episodeId, readableDatabase)

    @Synchronized
    fun saveClip(clip: Clip) {
        writableDatabase.insertWithOnConflict(
            "clips",
            null,
            clipValues(clip),
            SQLiteDatabase.CONFLICT_REPLACE
        )
        refreshSnapshot()
    }

    @Synchronized
    fun deleteClip(clipId: String) {
        writableDatabase.delete("clips", "id = ?", arrayOf(clipId))
        refreshSnapshot()
    }

    @Synchronized
    fun updateTranscript(
        clipId: String,
        transcript: String,
        state: TranscriptState,
        error: String = ""
    ) {
        writableDatabase.update(
            "clips",
            ContentValues().apply {
                put("transcript", transcript)
                put("transcript_state", state.name)
                put("transcript_error", error)
            },
            "id = ?",
            arrayOf(clipId)
        )
        refreshSnapshot()
    }

    fun subscribedFeedUrls(): List<String> =
        readableDatabase.query(
            "podcasts",
            arrayOf("feed_url"),
            null,
            null,
            null,
            null,
            "subscribed_at DESC"
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) add(cursor.getString(0))
            }
        }

    @Synchronized
    fun refreshSnapshot() {
        mutablePodcasts.value = readableDatabase.query(
            "podcasts", null, null, null, null, null, "subscribed_at DESC"
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) add(cursor.toPodcast())
            }
        }
        mutableEpisodes.value = readableDatabase.query(
            "episodes", null, null, null, null, null, "published_at DESC", "250"
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) add(cursor.toEpisode())
            }
        }
        mutableClips.value = readableDatabase.query(
            "clips", null, null, null, null, null, "created_at DESC"
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) add(cursor.toClip())
            }
        }
        mutableQueue.value = readableDatabase.rawQuery(
            """
            SELECT e.*
            FROM playback_queue q
            JOIN episodes e ON e.id = q.episode_id
            ORDER BY q.queued_at ASC
            """.trimIndent(),
            null
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) add(cursor.toEpisode())
            }
        }
    }

    private fun markInterruptedTranscriptions() {
        writableDatabase.update(
            "clips",
            ContentValues().apply {
                put("transcript_state", TranscriptState.OUTCOME_UNKNOWN.name)
                put(
                    "transcript_error",
                    "The app closed before Groq confirmed the result. Check usage before retrying to avoid a duplicate charge."
                )
            },
            "transcript_state = ?",
            arrayOf(TranscriptState.SENDING.name)
        )
    }

    private fun findEpisode(episodeId: String, db: SQLiteDatabase): Episode? =
        db.query(
            "episodes", null, "id = ?", arrayOf(episodeId), null, null, null, "1"
        ).use { cursor ->
            if (cursor.moveToFirst()) cursor.toEpisode() else null
        }

    private fun episodeValues(episode: Episode) = ContentValues().apply {
        put("id", episode.id)
        put("podcast_feed_url", episode.podcastFeedUrl)
        put("podcast_title", episode.podcastTitle)
        put("title", episode.title)
        put("description", episode.description)
        put("audio_url", episode.audioUrl)
        put("artwork_url", episode.artworkUrl)
        put("published_at", episode.publishedAt)
        put("duration_ms", episode.durationMs)
        put("downloaded_path", episode.downloadedPath)
    }

    private fun clipValues(clip: Clip) = ContentValues().apply {
        put("id", clip.id)
        put("episode_id", clip.episodeId)
        put("episode_title", clip.episodeTitle)
        put("podcast_title", clip.podcastTitle)
        put("artwork_url", clip.artworkUrl)
        put("file_path", clip.filePath)
        put("start_ms", clip.startMs)
        put("end_ms", clip.endMs)
        put("created_at", clip.createdAt)
        put("transcript", clip.transcript)
        put("transcript_state", clip.transcriptState.name)
        put("transcript_error", clip.transcriptError)
    }

    private fun Cursor.toPodcast() = Podcast(
        feedUrl = string("feed_url"),
        title = string("title"),
        author = string("author"),
        description = string("description"),
        artworkUrl = string("artwork_url"),
        subscribedAt = long("subscribed_at")
    )

    private fun Cursor.toEpisode() = Episode(
        id = string("id"),
        podcastFeedUrl = string("podcast_feed_url"),
        podcastTitle = string("podcast_title"),
        title = string("title"),
        description = string("description"),
        audioUrl = string("audio_url"),
        artworkUrl = string("artwork_url"),
        publishedAt = long("published_at"),
        durationMs = long("duration_ms"),
        downloadedPath = string("downloaded_path")
    )

    private fun Cursor.toClip(): Clip {
        val rawState = string("transcript_state")
        return Clip(
            id = string("id"),
            episodeId = string("episode_id"),
            episodeTitle = string("episode_title"),
            podcastTitle = string("podcast_title"),
            artworkUrl = string("artwork_url"),
            filePath = string("file_path"),
            startMs = long("start_ms"),
            endMs = long("end_ms"),
            createdAt = long("created_at"),
            transcript = string("transcript"),
            transcriptState = runCatching {
                TranscriptState.valueOf(rawState)
            }.getOrDefault(TranscriptState.LOCAL_ONLY),
            transcriptError = string("transcript_error")
        )
    }

    private fun Cursor.string(name: String): String =
        getString(getColumnIndexOrThrow(name))

    private fun Cursor.long(name: String): Long =
        getLong(getColumnIndexOrThrow(name))

    companion object {
        private const val DATABASE_VERSION = 2
    }
}

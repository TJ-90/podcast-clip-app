package com.tj90.podcastclip.data.local

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import com.tj90.podcastclip.model.Clip
import com.tj90.podcastclip.model.Episode
import com.tj90.podcastclip.model.ParsedFeed
import com.tj90.podcastclip.model.Podcast
import com.tj90.podcastclip.model.TranscriptState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

class PodcastStore(context: Context) :
    SQLiteOpenHelper(context.applicationContext, "podcast-clips.db", null, 1) {

    private val mutablePodcasts = MutableStateFlow<List<Podcast>>(emptyList())
    private val mutableEpisodes = MutableStateFlow<List<Episode>>(emptyList())
    private val mutableClips = MutableStateFlow<List<Clip>>(emptyList())

    val podcasts: StateFlow<List<Podcast>> = mutablePodcasts
    val episodes: StateFlow<List<Episode>> = mutableEpisodes
    val clips: StateFlow<List<Clip>> = mutableClips

    init {
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
                duration_ms INTEGER NOT NULL
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
        db.execSQL("CREATE INDEX episodes_feed_index ON episodes(podcast_feed_url)")
        db.execSQL("CREATE INDEX episodes_published_index ON episodes(published_at DESC)")
        db.execSQL("CREATE INDEX clips_created_index ON clips(created_at DESC)")
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit

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
                db.insertWithOnConflict(
                    "episodes",
                    null,
                    ContentValues().apply {
                        put("id", episode.id)
                        put("podcast_feed_url", episode.podcastFeedUrl)
                        put("podcast_title", episode.podcastTitle)
                        put("title", episode.title)
                        put("description", episode.description)
                        put("audio_url", episode.audioUrl)
                        put("artwork_url", episode.artworkUrl)
                        put("published_at", episode.publishedAt)
                        put("duration_ms", episode.durationMs)
                    },
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
            "podcasts",
            null,
            null,
            null,
            null,
            null,
            "subscribed_at DESC"
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) {
                    add(
                        Podcast(
                            feedUrl = cursor.string("feed_url"),
                            title = cursor.string("title"),
                            author = cursor.string("author"),
                            description = cursor.string("description"),
                            artworkUrl = cursor.string("artwork_url"),
                            subscribedAt = cursor.long("subscribed_at")
                        )
                    )
                }
            }
        }
        mutableEpisodes.value = readableDatabase.query(
            "episodes",
            null,
            null,
            null,
            null,
            null,
            "published_at DESC",
            "250"
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) {
                    add(
                        Episode(
                            id = cursor.string("id"),
                            podcastFeedUrl = cursor.string("podcast_feed_url"),
                            podcastTitle = cursor.string("podcast_title"),
                            title = cursor.string("title"),
                            description = cursor.string("description"),
                            audioUrl = cursor.string("audio_url"),
                            artworkUrl = cursor.string("artwork_url"),
                            publishedAt = cursor.long("published_at"),
                            durationMs = cursor.long("duration_ms")
                        )
                    )
                }
            }
        }
        mutableClips.value = readableDatabase.query(
            "clips",
            null,
            null,
            null,
            null,
            null,
            "created_at DESC"
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) {
                    val rawState = cursor.string("transcript_state")
                    add(
                        Clip(
                            id = cursor.string("id"),
                            episodeId = cursor.string("episode_id"),
                            episodeTitle = cursor.string("episode_title"),
                            podcastTitle = cursor.string("podcast_title"),
                            artworkUrl = cursor.string("artwork_url"),
                            filePath = cursor.string("file_path"),
                            startMs = cursor.long("start_ms"),
                            endMs = cursor.long("end_ms"),
                            createdAt = cursor.long("created_at"),
                            transcript = cursor.string("transcript"),
                            transcriptState = runCatching {
                                TranscriptState.valueOf(rawState)
                            }.getOrDefault(TranscriptState.LOCAL_ONLY),
                            transcriptError = cursor.string("transcript_error")
                        )
                    )
                }
            }
        }
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

    private fun android.database.Cursor.string(name: String): String =
        getString(getColumnIndexOrThrow(name))

    private fun android.database.Cursor.long(name: String): Long =
        getLong(getColumnIndexOrThrow(name))
}

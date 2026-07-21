package com.tj90.podcastclip.data.local

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import com.google.common.truth.Truth.assertThat
import com.tj90.podcastclip.model.Clip
import com.tj90.podcastclip.model.Episode
import com.tj90.podcastclip.model.ParsedFeed
import com.tj90.podcastclip.model.PlaybackBookmark
import com.tj90.podcastclip.model.Podcast
import com.tj90.podcastclip.model.TranscriptState
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.io.File

@RunWith(RobolectricTestRunner::class)
class PodcastClipDatabaseTest {
    private val context = ApplicationProvider.getApplicationContext<Context>()

    @Before
    fun resetDatabase() {
        context.deleteDatabase(DATABASE_NAME)
    }

    @After
    fun cleanDatabase() {
        context.deleteDatabase(DATABASE_NAME)
        File(context.filesDir, "episodes/test.audio").delete()
    }

    @Test
    fun queueBookmarkDownloadAndInterruptedTranscriptionSurviveReopen() {
        val feed = ParsedFeed(
            podcast = Podcast("https://example.com/feed", "Show", "Author", "", "", 1),
            episodes = listOf(
                Episode(
                    id = "episode-1",
                    podcastFeedUrl = "https://example.com/feed",
                    podcastTitle = "Show",
                    title = "Episode",
                    description = "",
                    audioUrl = "https://example.com/audio.mp3",
                    artworkUrl = "",
                    publishedAt = 2,
                    durationMs = 60_000
                )
            )
        )
        val offline = File(context.filesDir, "episodes/test.audio").apply {
            parentFile?.mkdirs()
            writeBytes(byteArrayOf(1, 2, 3))
        }
        PodcastStore(context).use { store ->
            store.upsertFeed(feed)
            store.saveDownloadedPath("episode-1", offline.absolutePath)
            store.upsertFeed(feed)
            store.enqueue("episode-1")
            store.savePlaybackBookmark(PlaybackBookmark("episode-1", 12_345, 1.5f))
            store.saveClip(
                Clip(
                    id = "clip-1",
                    episodeId = "episode-1",
                    episodeTitle = "Episode",
                    podcastTitle = "Show",
                    artworkUrl = "",
                    filePath = File(context.filesDir, "clips/clip.m4a").absolutePath,
                    startMs = 1_000,
                    endMs = 5_000,
                    createdAt = 3,
                    transcript = "",
                    transcriptState = TranscriptState.SENDING,
                    transcriptError = ""
                )
            )
        }

        PodcastStore(context).use { reopened ->
            assertThat(reopened.episodes.value.single().isDownloaded).isTrue()
            assertThat(reopened.queue.value.map { it.id }).containsExactly("episode-1")
            assertThat(reopened.loadPlaybackBookmark()).isEqualTo(
                PlaybackBookmark("episode-1", 12_345, 1.5f)
            )
            assertThat(reopened.clips.value.single().transcriptState)
                .isEqualTo(TranscriptState.OUTCOME_UNKNOWN)
            assertThat(reopened.clips.value.single().transcriptError)
                .contains("duplicate charge")
        }
    }

    private companion object {
        const val DATABASE_NAME = "podcast-clips.db"
    }
}

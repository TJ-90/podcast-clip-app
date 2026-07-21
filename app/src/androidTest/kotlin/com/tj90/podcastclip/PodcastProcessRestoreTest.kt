package com.tj90.podcastclip

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.tj90.podcastclip.data.local.PodcastStore
import com.tj90.podcastclip.model.Episode
import com.tj90.podcastclip.model.ParsedFeed
import com.tj90.podcastclip.model.PlaybackBookmark
import com.tj90.podcastclip.model.Podcast
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PodcastProcessRestoreTest {
    @Test
    fun bookmarkAndQueueRestoreAfterStoreReopen() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        context.deleteDatabase(DATABASE_NAME)
        try {
            val feed = ParsedFeed(
                Podcast("https://example.com/feed", "Show", "", "", "", 1),
                listOf(
                    Episode(
                        "restore-episode",
                        "https://example.com/feed",
                        "Show",
                        "Restore me",
                        "",
                        "https://example.com/audio.mp3",
                        "",
                        2,
                        120_000
                    )
                )
            )
            PodcastStore(context).use { store ->
                store.upsertFeed(feed)
                store.enqueue("restore-episode")
                store.savePlaybackBookmark(PlaybackBookmark("restore-episode", 45_000, 1.25f))
            }

            PodcastStore(context).use { reopened ->
                assertEquals("restore-episode", reopened.queue.value.single().id)
                assertEquals(
                    PlaybackBookmark("restore-episode", 45_000, 1.25f),
                    reopened.loadPlaybackBookmark()
                )
            }
        } finally {
            context.deleteDatabase(DATABASE_NAME)
        }
    }

    private companion object {
        const val DATABASE_NAME = "podcast-clips.db"
    }
}

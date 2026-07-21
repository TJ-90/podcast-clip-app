package com.tj90.podcastclip

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.tj90.podcastclip.model.Episode
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class OfflinePlaybackTest {
    @Test
    fun downloadedEpisodePrefersItsAppPrivateFile() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val file = File(context.filesDir, "episodes/instrumented.audio").apply {
            parentFile?.mkdirs()
            writeBytes(byteArrayOf(1, 2, 3))
        }
        try {
            val episode = Episode(
                id = "offline",
                podcastFeedUrl = "https://example.com/feed",
                podcastTitle = "Show",
                title = "Episode",
                description = "",
                audioUrl = "https://example.com/stream.mp3",
                artworkUrl = "",
                publishedAt = 0,
                durationMs = 1_000,
                downloadedPath = file.absolutePath
            )

            assertTrue(episode.isDownloaded)
            assertTrue(episode.playableUri.startsWith("file:"))
        } finally {
            assertEquals(true, file.delete())
        }
    }
}

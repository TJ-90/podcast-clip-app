package com.tj90.podcastclip.repository

import com.tj90.podcastclip.data.local.PodcastStore
import com.tj90.podcastclip.feed.RssFeedParser
import com.tj90.podcastclip.model.Clip
import com.tj90.podcastclip.model.PodcastSearchResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.withContext
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class PodcastRepository(
    private val store: PodcastStore,
    private val parser: RssFeedParser = RssFeedParser(),
    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .followRedirects(true)
        .build()
) {
    val podcasts = store.podcasts
    val episodes = store.episodes
    val clips: StateFlow<List<Clip>> = store.clips

    suspend fun subscribe(rawUrl: String): Boolean = withContext(Dispatchers.IO) {
        val feedUrl = normalizeFeedUrl(rawUrl)
        val request = Request.Builder()
            .url(feedUrl)
            .header("User-Agent", "PodcastClips/0.1 (+https://github.com/TJ-90/podcast-clip-app)")
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("Feed request failed with HTTP " + response.code)
            val body = response.body ?: error("Feed response was empty")
            val size = body.contentLength()
            if (size > MAX_FEED_BYTES) error("Feed is larger than the 5 MB safety limit")
            val feed = body.byteStream().use { parser.parse(it, feedUrl) }
            if (feed.episodes.isEmpty()) error("This feed has no playable audio episodes")
            store.upsertFeed(feed)
            feedUrl.startsWith("http://") ||
                feed.episodes.any { it.audioUrl.startsWith("http://") }
        }
    }

    suspend fun refreshAll(): Int = withContext(Dispatchers.IO) {
        var refreshed = 0
        store.subscribedFeedUrls().forEach { feedUrl ->
            runCatching { subscribe(feedUrl) }.onSuccess { refreshed += 1 }
        }
        refreshed
    }

    suspend fun search(query: String): List<PodcastSearchResult> =
        withContext(Dispatchers.IO) {
            if (query.trim().length < 2) return@withContext emptyList()
            val url = "https://itunes.apple.com/search".toHttpUrl().newBuilder()
                .addQueryParameter("media", "podcast")
                .addQueryParameter("entity", "podcast")
                .addQueryParameter("limit", "20")
                .addQueryParameter("term", query.trim())
                .build()
            val request = Request.Builder()
                .url(url)
                .header("User-Agent", "PodcastClips/0.1")
                .build()
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    error("Directory search failed with HTTP " + response.code)
                }
                val json = JSONObject(response.body?.string().orEmpty())
                val results = json.optJSONArray("results") ?: return@use emptyList()
                buildList {
                    for (index in 0 until results.length()) {
                        val item = results.optJSONObject(index) ?: continue
                        val feedUrl = item.optString("feedUrl")
                        if (feedUrl.isBlank()) continue
                        add(
                            PodcastSearchResult(
                                feedUrl = feedUrl,
                                title = item.optString("collectionName", "Untitled podcast"),
                                author = item.optString("artistName"),
                                artworkUrl = item.optString("artworkUrl600")
                                    .ifBlank { item.optString("artworkUrl100") },
                                genre = item.optString("primaryGenreName")
                            )
                        )
                    }
                }.distinctBy { it.feedUrl }
            }
        }

    suspend fun saveClip(clip: Clip) = withContext(Dispatchers.IO) {
        store.saveClip(clip)
    }

    suspend fun updateTranscript(
        clipId: String,
        transcript: String,
        state: com.tj90.podcastclip.model.TranscriptState,
        error: String = ""
    ) = withContext(Dispatchers.IO) {
        store.updateTranscript(clipId, transcript, state, error)
    }

    private fun normalizeFeedUrl(raw: String): String {
        val value = raw.trim()
        require(value.isNotBlank()) { "Enter a podcast RSS URL" }
        val normalized = if (value.startsWith("http://") || value.startsWith("https://")) {
            value
        } else {
            "https://$value"
        }
        val parsed = normalized.toHttpUrl()
        require(parsed.scheme == "https" || parsed.scheme == "http") {
            "Only HTTP and HTTPS podcast feeds are supported"
        }
        return parsed.toString()
    }

    private companion object {
        const val MAX_FEED_BYTES = 5L * 1024L * 1024L
    }
}
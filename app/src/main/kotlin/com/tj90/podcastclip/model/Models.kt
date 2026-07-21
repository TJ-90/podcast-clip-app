package com.tj90.podcastclip.model

data class Podcast(
    val feedUrl: String,
    val title: String,
    val author: String,
    val description: String,
    val artworkUrl: String,
    val subscribedAt: Long
)

data class Episode(
    val id: String,
    val podcastFeedUrl: String,
    val podcastTitle: String,
    val title: String,
    val description: String,
    val audioUrl: String,
    val artworkUrl: String,
    val publishedAt: Long,
    val durationMs: Long
)

data class Clip(
    val id: String,
    val episodeId: String,
    val episodeTitle: String,
    val podcastTitle: String,
    val artworkUrl: String,
    val filePath: String,
    val startMs: Long,
    val endMs: Long,
    val createdAt: Long,
    val transcript: String,
    val transcriptState: TranscriptState,
    val transcriptError: String
)

enum class TranscriptState {
    LOCAL_ONLY,
    SENDING,
    COMPLETE,
    FAILED
}

data class PodcastSearchResult(
    val feedUrl: String,
    val title: String,
    val author: String,
    val artworkUrl: String,
    val genre: String
)

data class ParsedFeed(
    val podcast: Podcast,
    val episodes: List<Episode>
)

fun stableId(value: String): String {
    val bytes = java.security.MessageDigest.getInstance("SHA-256")
        .digest(value.toByteArray(Charsets.UTF_8))
    return bytes.take(16).joinToString("") { "%02x".format(it) }
}

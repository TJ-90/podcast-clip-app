package com.tj90.podcastclip.feed

import com.tj90.podcastclip.model.Episode
import com.tj90.podcastclip.model.ParsedFeed
import com.tj90.podcastclip.model.Podcast
import com.tj90.podcastclip.model.stableId
import org.w3c.dom.Element
import java.io.InputStream
import java.text.SimpleDateFormat
import java.util.Locale
import javax.xml.parsers.DocumentBuilderFactory

class RssFeedParser {

    fun parse(input: InputStream, sourceFeedUrl: String): ParsedFeed {
        val factory = DocumentBuilderFactory.newInstance().apply {
            isNamespaceAware = false
            isXIncludeAware = false
            setExpandEntityReferences(false)
            listOf(
                "http://apache.org/xml/features/disallow-doctype-decl" to true,
                "http://xml.org/sax/features/external-general-entities" to false,
                "http://xml.org/sax/features/external-parameter-entities" to false
            ).forEach { (feature, value) ->
                runCatching { setFeature(feature, value) }
            }
        }
        val document = factory.newDocumentBuilder().parse(input)
        val channel = document.getElementsByTagName("channel").item(0) as? Element
            ?: error("This URL does not contain an RSS podcast channel")

        val title = channel.childText("title").ifBlank { "Untitled podcast" }
        val author = channel.childText("itunes:author")
            .ifBlank { channel.childText("author") }
        val description = cleanText(
            channel.childText("description").ifBlank { channel.childText("itunes:summary") }
        )
        val artwork = channel.child("itunes:image")?.getAttribute("href").orEmpty()
            .ifBlank {
                channel.child("image")?.childText("url").orEmpty()
            }

        val podcast = Podcast(
            feedUrl = sourceFeedUrl,
            title = title,
            author = author,
            description = description,
            artworkUrl = artwork,
            subscribedAt = System.currentTimeMillis()
        )

        val episodeNodes = channel.getElementsByTagName("item")
        val episodes = buildList {
            for (index in 0 until episodeNodes.length) {
                val item = episodeNodes.item(index) as? Element ?: continue
                val enclosure = item.child("enclosure")
                val audioUrl = enclosure?.getAttribute("url").orEmpty()
                if (audioUrl.isBlank()) continue
                val guid = item.childText("guid").ifBlank { audioUrl }
                val episodeArtwork = item.child("itunes:image")
                    ?.getAttribute("href")
                    .orEmpty()
                    .ifBlank { artwork }
                add(
                    Episode(
                        id = stableId("$sourceFeedUrl::$guid"),
                        podcastFeedUrl = sourceFeedUrl,
                        podcastTitle = title,
                        title = item.childText("title").ifBlank { "Untitled episode" },
                        description = cleanText(
                            item.childText("description")
                                .ifBlank { item.childText("itunes:summary") }
                        ),
                        audioUrl = audioUrl,
                        artworkUrl = episodeArtwork,
                        publishedAt = parseDate(item.childText("pubDate")),
                        durationMs = parseDuration(item.childText("itunes:duration"))
                    )
                )
            }
        }

        return ParsedFeed(podcast, episodes)
    }

    private fun Element.child(tag: String): Element? {
        for (index in 0 until childNodes.length) {
            val node = childNodes.item(index)
            if (node is Element && node.nodeName.equals(tag, ignoreCase = true)) return node
        }
        return null
    }

    private fun Element.childText(tag: String): String =
        child(tag)?.textContent?.trim().orEmpty()

    private fun parseDuration(raw: String): Long {
        if (raw.isBlank()) return 0
        val parts = raw.trim().split(":").mapNotNull(String::toLongOrNull)
        val seconds = when (parts.size) {
            3 -> parts[0] * 3600 + parts[1] * 60 + parts[2]
            2 -> parts[0] * 60 + parts[1]
            1 -> parts[0]
            else -> 0
        }
        return seconds * 1000
    }

    private fun parseDate(raw: String): Long {
        val patterns = listOf(
            "EEE, dd MMM yyyy HH:mm:ss Z",
            "EEE, d MMM yyyy HH:mm:ss Z",
            "yyyy-MM-dd'T'HH:mm:ssXXX"
        )
        return patterns.firstNotNullOfOrNull { pattern ->
            runCatching {
                SimpleDateFormat(pattern, Locale.US).apply { isLenient = true }.parse(raw)?.time
            }.getOrNull()
        } ?: 0L
    }

    private fun cleanText(raw: String): String =
        raw.replace(Regex("<[^>]*>"), " ")
            .replace("&amp;", "&")
            .replace("&quot;", """)
            .replace("&#39;", "'")
            .replace(Regex("\\s+"), " ")
            .trim()
}

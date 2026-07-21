package com.tj90.podcastclip.feed

import com.google.common.truth.Truth.assertThat
import org.junit.Test
import java.io.ByteArrayInputStream

class RssFeedParserTest {
    @Test
    fun parsesPodcastMetadataAndPlayableEpisodes() {
        val xml = """
            <rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
              <channel>
                <title>Signal &amp; Craft</title>
                <itunes:author>Studio North</itunes:author>
                <description><![CDATA[<p>A thoughtful show.</p>]]></description>
                <itunes:image href="https://example.com/show.jpg"/>
                <item>
                  <title>Episode one</title>
                  <guid>episode-1</guid>
                  <pubDate>Mon, 20 Jul 2026 10:30:00 +0000</pubDate>
                  <itunes:duration>01:02:03</itunes:duration>
                  <enclosure url="https://example.com/episode.mp3" type="audio/mpeg"/>
                </item>
                <item>
                  <title>Text-only item</title>
                </item>
              </channel>
            </rss>
        """.trimIndent()

        val parsed = RssFeedParser().parse(
            ByteArrayInputStream(xml.toByteArray()),
            "https://example.com/feed.xml"
        )

        assertThat(parsed.podcast.title).isEqualTo("Signal & Craft")
        assertThat(parsed.podcast.author).isEqualTo("Studio North")
        assertThat(parsed.episodes).hasSize(1)
        assertThat(parsed.episodes.single().durationMs).isEqualTo(3_723_000L)
        assertThat(parsed.episodes.single().audioUrl)
            .isEqualTo("https://example.com/episode.mp3")
    }

    @Test
    fun rejectsDocumentsWithoutAnRssChannel() {
        val result = runCatching {
            RssFeedParser().parse(
                ByteArrayInputStream("<html/>".toByteArray()),
                "https://example.com"
            )
        }

        assertThat(result.isFailure).isTrue()
    }

@Test
fun rejectsDoctypeAndExternalEntityPayloads() {
    val malicious = """
        <!DOCTYPE rss [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
        <rss><channel><title>&xxe;</title></channel></rss>
    """.trimIndent()

    val result = runCatching {
        RssFeedParser().parse(
            ByteArrayInputStream(malicious.toByteArray()),
            "https://example.com/feed.xml"
        )
    }

    assertThat(result.isFailure).isTrue()
}
}
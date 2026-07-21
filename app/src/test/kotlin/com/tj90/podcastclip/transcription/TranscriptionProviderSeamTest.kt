package com.tj90.podcastclip.transcription

import com.google.common.truth.Truth.assertThat
import kotlinx.coroutines.test.runTest
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import java.io.IOException
import kotlin.io.path.createTempFile

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class TranscriptionProviderSeamTest {
    @Test
    fun returnsTranscriptWithoutLeakingProviderJson() = runTest {
        val provider = GroqTranscriptionProvider(client(200, """{"text":"A useful moment."}"""))
        val clip = clipFile()

        val result = provider.transcribe(clip, "gsk_test")

        assertThat(result).isEqualTo("A useful moment.")
        clip.delete()
    }

    @Test
    fun mapsRateLimitSeparatelyFromDefinitiveFailure() = runTest {
        val provider = GroqTranscriptionProvider(
            client(429, """{"error":{"message":"Slow down"}}""")
        )

        val error = runCatching {
            provider.transcribe(clipFile(), "gsk_test")
        }.exceptionOrNull()

        assertThat(error).isInstanceOf(GroqRateLimitException::class.java)
    }

    @Test
    fun transportFailureIsOutcomeUnknownAndNeverAutoRetried() = runTest {
        var attempts = 0
        val client = OkHttpClient.Builder().addInterceptor {
            attempts += 1
            throw IOException("connection dropped")
        }.build()
        val provider = GroqTranscriptionProvider(client)

        val error = runCatching {
            provider.transcribe(clipFile(), "gsk_test")
        }.exceptionOrNull()

        assertThat(error).isInstanceOf(GroqOutcomeUnknownException::class.java)
        assertThat(error?.message).contains("duplicate charge")
        assertThat(attempts).isEqualTo(1)
    }

    private fun client(code: Int, body: String): OkHttpClient =
        OkHttpClient.Builder().addInterceptor { chain ->
            Response.Builder()
                .request(chain.request())
                .protocol(Protocol.HTTP_1_1)
                .code(code)
                .message("test")
                .body(body.toResponseBody("application/json".toMediaType()))
                .build()
        }.build()

    private fun clipFile() = createTempFile("clip", ".m4a").toFile().apply {
        writeBytes(byteArrayOf(1, 2, 3))
        deleteOnExit()
    }
}
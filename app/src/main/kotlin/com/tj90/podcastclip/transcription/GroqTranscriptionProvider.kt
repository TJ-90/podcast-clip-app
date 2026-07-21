package com.tj90.podcastclip.transcription

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import org.json.JSONObject
import java.io.File
import java.io.IOException
import java.util.concurrent.TimeUnit

class GroqRateLimitException(message: String) : IOException(message)
class GroqOutcomeUnknownException(message: String, cause: Throwable) : IOException(message, cause)
class GroqRequestException(message: String) : IOException(message)

class GroqTranscriptionProvider(
    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .readTimeout(90, TimeUnit.SECONDS)
        .build()
) : TranscriptionProvider {

    override suspend fun transcribe(file: File, apiKey: String): String =
        withContext(Dispatchers.IO) {
            require(apiKey.isNotBlank()) { "Add a Groq API key in Settings first" }
            require(file.exists() && file.length() > 0) { "The saved clip file is missing" }
            require(file.length() <= MAX_UPLOAD_BYTES) { "Clip exceeds Groq's 25 MB upload limit" }
            val body = MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("model", "whisper-large-v3-turbo")
                .addFormDataPart("response_format", "json")
                .addFormDataPart(
                    "file",
                    file.name,
                    file.asRequestBody("audio/mp4".toMediaType())
                )
                .build()
            val request = Request.Builder()
                .url("https://api.groq.com/openai/v1/audio/transcriptions")
                .header("Authorization", "Bearer $apiKey")
                .post(body)
                .build()
            try {
                client.newCall(request).execute().use { response ->
                    val responseBody = response.body.string()
                    if (!response.isSuccessful) {
                        val detail = runCatching {
                            JSONObject(responseBody)
                                .optJSONObject("error")
                                ?.optString("message")
                        }.getOrNull().orEmpty()
                        val message = detail.ifBlank {
                            "Transcription failed with HTTP " + response.code
                        }
                        if (response.code == 429) throw GroqRateLimitException(message)
                        throw GroqRequestException(message)
                    }
                    JSONObject(responseBody).optString("text").trim()
                        .ifBlank { throw GroqRequestException("Groq returned an empty transcript") }
                }
            } catch (error: GroqRateLimitException) {
                throw error
            } catch (error: GroqRequestException) {
                throw error
            } catch (error: GroqOutcomeUnknownException) {
                throw error
            } catch (error: IOException) {
                throw GroqOutcomeUnknownException(
                    "Groq did not confirm the result. Check usage before retrying to avoid a duplicate charge.",
                    error
                )
            }
        }

    private companion object {
        const val MAX_UPLOAD_BYTES = 25L * 1024L * 1024L
    }
}

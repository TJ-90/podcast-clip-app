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
import java.util.concurrent.TimeUnit

class GroqTranscriptionProvider(
    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(90, TimeUnit.SECONDS)
        .build()
) : TranscriptionProvider {

    override suspend fun transcribe(file: File, apiKey: String): String =
        withContext(Dispatchers.IO) {
            require(apiKey.isNotBlank()) { "Add a Groq API key in Settings first" }
            require(file.exists() && file.length() > 0) { "The saved clip file is missing" }
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
            client.newCall(request).execute().use { response ->
                val responseBody = response.body?.string().orEmpty()
                if (!response.isSuccessful) {
                    val detail = runCatching {
                        JSONObject(responseBody)
                            .optJSONObject("error")
                            ?.optString("message")
                    }.getOrNull().orEmpty()
                    error(detail.ifBlank { "Transcription failed with HTTP " + response.code })
                }
                JSONObject(responseBody).optString("text").trim()
                    .ifBlank { error("Groq returned an empty transcript") }
            }
        }
}

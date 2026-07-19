package com.tj90.podcastclip.transcription

data class TranscriptionRequest(
    val clipId: String,
    val localUri: String,
    val durationMillis: Long
)

sealed interface TranscriptionResult {
    data class Complete(val text: String) : TranscriptionResult
    data class Unavailable(val reason: String) : TranscriptionResult
}

fun interface TranscriptionProvider {
    suspend fun transcribe(request: TranscriptionRequest): TranscriptionResult
}

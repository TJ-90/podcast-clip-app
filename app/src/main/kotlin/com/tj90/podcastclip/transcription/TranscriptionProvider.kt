package com.tj90.podcastclip.transcription

import java.io.File

interface TranscriptionProvider {
    suspend fun transcribe(file: File, apiKey: String): String
}

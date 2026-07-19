package com.tj90.podcastclip.transcription

class NoOpTranscriptionProvider : TranscriptionProvider {
    override suspend fun transcribe(request: TranscriptionRequest): TranscriptionResult =
        TranscriptionResult.Unavailable("Production transcription is intentionally absent from G011.")
}

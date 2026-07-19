package com.tj90.podcastclip.transcription

class FixedFixtureTranscriptionProvider : TranscriptionProvider {
    override suspend fun transcribe(request: TranscriptionRequest): TranscriptionResult =
        TranscriptionResult.Complete("A fixed local fixture transcript for ${request.clipId}.")
}

package com.tj90.podcastclip.clipping

import android.content.Context
import androidx.annotation.OptIn
import androidx.media3.common.MediaItem
import androidx.media3.common.MimeTypes
import androidx.media3.common.util.UnstableApi
import androidx.media3.transformer.Composition
import androidx.media3.transformer.EditedMediaItem
import androidx.media3.transformer.ExportException
import androidx.media3.transformer.ExportResult
import androidx.media3.transformer.Transformer
import com.tj90.podcastclip.model.Episode
import com.tj90.podcastclip.model.stableId
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import java.io.File
import kotlin.coroutines.resumeWithException

@OptIn(UnstableApi::class)
class ClipExporter(private val context: Context) {

    suspend fun export(episode: Episode, startMs: Long, endMs: Long): File =
        withContext(Dispatchers.Main.immediate) {
            require(endMs - startMs in MIN_CLIP_MS..MAX_CLIP_MS) {
                "Clips must be between 3 seconds and 5 minutes"
            }
            val directory = File(context.filesDir, "clips").apply { mkdirs() }
            val output = File(
                directory,
                stableId(episode.id + ":" + startMs + ":" + endMs + ":" + System.nanoTime()) + ".m4a"
            )
            if (output.exists()) output.delete()

            suspendCancellableCoroutine { continuation ->
                val mediaItem = MediaItem.Builder()
                    .setUri(episode.playableUri)
                    .setClippingConfiguration(
                        MediaItem.ClippingConfiguration.Builder()
                            .setStartPositionMs(startMs)
                            .setEndPositionMs(endMs)
                            .build()
                    )
                    .build()
                val edited = EditedMediaItem.Builder(mediaItem)
                    .setRemoveVideo(true)
                    .build()
                val transformer = Transformer.Builder(context)
                    .setAudioMimeType(MimeTypes.AUDIO_AAC)
                    .addListener(
                        object : Transformer.Listener {
                            override fun onCompleted(
                                composition: Composition,
                                exportResult: ExportResult
                            ) {
                                continuation.resumeWith(Result.success(output))
                            }

                            override fun onError(
                                composition: Composition,
                                exportResult: ExportResult,
                                exportException: ExportException
                            ) {
                                output.delete()
                                continuation.resumeWithException(exportException)
                            }
                        }
                    )
                    .build()
                continuation.invokeOnCancellation {
                    transformer.cancel()
                    output.delete()
                }
                transformer.start(edited, output.absolutePath)
            }
        }

    companion object {
        const val MIN_CLIP_MS = 3_000L
        const val MAX_CLIP_MS = 300_000L
    }
}

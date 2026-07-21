package com.tj90.podcastclip.playback

import android.content.ComponentName
import android.content.Context
import android.net.Uri
import androidx.core.content.ContextCompat
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.Player
import androidx.media3.session.MediaController
import androidx.media3.session.SessionToken
import com.tj90.podcastclip.model.Clip
import com.tj90.podcastclip.model.Episode
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.io.Closeable
import java.io.File

data class PlaybackUiState(
    val connected: Boolean = false,
    val episode: Episode? = null,
    val isPlaying: Boolean = false,
    val positionMs: Long = 0,
    val durationMs: Long = 0,
    val speed: Float = 1f
)

class PlaybackConnection(context: Context) : Player.Listener, Closeable {
    private val appContext = context.applicationContext
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private val mutableState = MutableStateFlow(PlaybackUiState())
    private val controllerFuture = MediaController.Builder(
        appContext,
        SessionToken(appContext, ComponentName(appContext, PodcastPlaybackService::class.java))
    ).buildAsync()

    private var controller: MediaController? = null
    private var ticker: Job? = null
    val state: StateFlow<PlaybackUiState> = mutableState

    init {
        controllerFuture.addListener(
            {
                runCatching { controllerFuture.get() }.onSuccess { readyController ->
                    controller = readyController
                    readyController.addListener(this)
                    mutableState.value = mutableState.value.copy(connected = true)
                    updateState()
                    startTicker()
                }
            },
            ContextCompat.getMainExecutor(appContext)
        )
    }

    fun play(episode: Episode) {
        val item = MediaItem.Builder()
            .setMediaId(episode.id)
            .setUri(episode.audioUrl)
            .setMediaMetadata(
                MediaMetadata.Builder()
                    .setTitle(episode.title)
                    .setArtist(episode.podcastTitle)
                    .setArtworkUri(episode.artworkUrl.takeIf { it.isNotBlank() }?.let(Uri::parse))
                    .build()
            )
            .build()
        mutableState.value = mutableState.value.copy(episode = episode)
        controller?.apply {
            setMediaItem(item)
            prepare()
            play()
        }
    }

    fun playClip(clip: Clip) {
        val episode = Episode(
            id = "clip-" + clip.id,
            podcastFeedUrl = "",
            podcastTitle = clip.podcastTitle,
            title = clip.episodeTitle + " · clip",
            description = clip.transcript,
            audioUrl = Uri.fromFile(File(clip.filePath)).toString(),
            artworkUrl = clip.artworkUrl,
            publishedAt = clip.createdAt,
            durationMs = clip.endMs - clip.startMs
        )
        play(episode)
    }

    fun toggle() {
        controller?.let { player ->
            if (player.isPlaying) player.pause() else player.play()
        }
    }

    fun pause() {
        controller?.pause()
    }

    fun seekBy(deltaMs: Long) {
        controller?.let { player ->
            val target = (player.currentPosition + deltaMs)
                .coerceIn(0, player.duration.takeIf { it > 0 } ?: Long.MAX_VALUE)
            player.seekTo(target)
        }
    }

    fun seekTo(positionMs: Long) {
        controller?.seekTo(positionMs.coerceAtLeast(0))
    }

    fun setSpeed(speed: Float) {
        controller?.setPlaybackSpeed(speed.coerceIn(0.5f, 3f))
        updateState()
    }

    override fun onEvents(player: Player, events: Player.Events) {
        updateState()
    }

    private fun startTicker() {
        ticker?.cancel()
        ticker = scope.launch {
            while (isActive) {
                updateState()
                delay(500)
            }
        }
    }

    private fun updateState() {
        val player = controller ?: return
        mutableState.value = mutableState.value.copy(
            connected = true,
            isPlaying = player.isPlaying,
            positionMs = player.currentPosition.coerceAtLeast(0),
            durationMs = player.duration.coerceAtLeast(0),
            speed = player.playbackParameters.speed
        )
    }

    override fun close() {
        ticker?.cancel()
        controller?.removeListener(this)
        controller?.release()
        controller = null
        controllerFuture.cancel(true)
    }
}

package com.tj90.podcastclip.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.tj90.podcastclip.clipping.ClipExporter
import com.tj90.podcastclip.data.local.PodcastStore
import com.tj90.podcastclip.feed.RssFeedParser
import com.tj90.podcastclip.model.Clip
import com.tj90.podcastclip.model.Episode
import com.tj90.podcastclip.model.Podcast
import com.tj90.podcastclip.model.PodcastSearchResult
import com.tj90.podcastclip.model.TranscriptState
import com.tj90.podcastclip.model.stableId
import com.tj90.podcastclip.playback.PlaybackConnection
import com.tj90.podcastclip.playback.PlaybackUiState
import com.tj90.podcastclip.repository.PodcastRepository
import com.tj90.podcastclip.transcription.GroqTranscriptionProvider
import com.tj90.podcastclip.transcription.SecureApiKeyStore
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.io.File

enum class PrimaryDestination(val label: String, val shortLabel: String) {
    HOME("Home", "H"),
    DISCOVER("Discover", "D"),
    LIBRARY("Library", "L"),
    CLIPS("Clips", "C")
}

data class ClipEditorState(
    val episode: Episode,
    val startMs: Long,
    val endMs: Long,
    val durationMs: Long,
    val saving: Boolean = false
)

data class AppUiState(
    val destination: PrimaryDestination = PrimaryDestination.HOME,
    val podcasts: List<Podcast> = emptyList(),
    val episodes: List<Episode> = emptyList(),
    val clips: List<Clip> = emptyList(),
    val player: PlaybackUiState = PlaybackUiState(),
    val searchQuery: String = "",
    val searchResults: List<PodcastSearchResult> = emptyList(),
    val busyLabel: String = "",
    val message: String = "",
    val addRssOpen: Boolean = false,
    val settingsOpen: Boolean = false,
    val playerOpen: Boolean = false,
    val clipEditor: ClipEditorState? = null,
    val apiKeyDraft: String = ""
)

class AppViewModel(application: Application) : AndroidViewModel(application) {
    private val store = PodcastStore(application)
    private val repository = PodcastRepository(store, RssFeedParser())
    private val playback = PlaybackConnection(application)
    private val clipExporter = ClipExporter(application)
    private val transcriptionProvider = GroqTranscriptionProvider()
    private val keyStore = SecureApiKeyStore(application)
    private val mutableState = MutableStateFlow(
        AppUiState(apiKeyDraft = keyStore.read())
    )

    val state: StateFlow<AppUiState> = mutableState

    init {
        viewModelScope.launch {
            repository.podcasts.collect { value ->
                mutableState.update { it.copy(podcasts = value) }
            }
        }
        viewModelScope.launch {
            repository.episodes.collect { value ->
                mutableState.update { it.copy(episodes = value) }
            }
        }
        viewModelScope.launch {
            repository.clips.collect { value ->
                mutableState.update { it.copy(clips = value) }
            }
        }
        viewModelScope.launch {
            playback.state.collect { value ->
                mutableState.update { it.copy(player = value) }
            }
        }
        if (repository.podcasts.value.isNotEmpty()) refreshLibrary(silent = true)
    }

    fun selectDestination(destination: PrimaryDestination) {
        mutableState.update { it.copy(destination = destination) }
    }

    fun setSearchQuery(value: String) {
        mutableState.update { it.copy(searchQuery = value) }
    }

    fun search() {
        val query = state.value.searchQuery.trim()
        if (query.length < 2) {
            mutableState.update { it.copy(message = "Enter at least two characters") }
            return
        }
        viewModelScope.launch {
            mutableState.update { it.copy(busyLabel = "Searching podcasts…") }
            runCatching { repository.search(query) }
                .onSuccess { results ->
                    mutableState.update {
                        it.copy(searchResults = results, busyLabel = "")
                    }
                }
                .onFailure(::showFailure)
        }
    }

    fun subscribe(feedUrl: String) {
        viewModelScope.launch {
            mutableState.update { it.copy(busyLabel = "Adding podcast…") }
            runCatching { repository.subscribe(feedUrl) }
                .onSuccess {
                    mutableState.update {
                        it.copy(
                            busyLabel = "",
                            addRssOpen = false,
                            message = "Podcast added to Library"
                        )
                    }
                }
                .onFailure(::showFailure)
        }
    }

    fun refreshLibrary(silent: Boolean = false) {
        viewModelScope.launch {
            if (!silent) mutableState.update { it.copy(busyLabel = "Refreshing feeds…") }
            runCatching { repository.refreshAll() }
                .onSuccess { count ->
                    mutableState.update {
                        it.copy(
                            busyLabel = "",
                            message = if (silent) it.message else "$count podcasts refreshed"
                        )
                    }
                }
                .onFailure(::showFailure)
        }
    }

    fun play(episode: Episode) {
        playback.play(episode)
        mutableState.update { it.copy(playerOpen = true) }
    }

    fun playClip(clip: Clip) {
        playback.playClip(clip)
        mutableState.update { it.copy(playerOpen = true) }
    }

    fun togglePlayback() = playback.toggle()

    fun seekBy(deltaMs: Long) = playback.seekBy(deltaMs)

    fun seekTo(positionMs: Long) = playback.seekTo(positionMs)

    fun setSpeed(speed: Float) = playback.setSpeed(speed)

    fun setPlayerOpen(open: Boolean) {
        mutableState.update { it.copy(playerOpen = open) }
    }

    fun openClipEditor() {
        val playerState = state.value.player
        val episode = playerState.episode
        if (episode == null) {
            mutableState.update { it.copy(message = "Play an episode before making a clip") }
            return
        }
        if (playerState.positionMs < ClipExporter.MIN_CLIP_MS) {
            mutableState.update { it.copy(message = "Listen for at least 3 seconds before clipping") }
            return
        }
        val knownDuration = listOf(
            playerState.durationMs,
            episode.durationMs,
            playerState.positionMs
        ).maxOrNull()?.coerceAtLeast(playerState.positionMs) ?: playerState.positionMs
        val end = playerState.positionMs.coerceAtMost(knownDuration)
        val start = (end - 30_000L).coerceAtLeast(0)
        playback.pause()
        mutableState.update {
            it.copy(
                playerOpen = false,
                clipEditor = ClipEditorState(
                    episode = episode,
                    startMs = start,
                    endMs = end,
                    durationMs = knownDuration
                )
            )
        }
    }

    fun setClipRange(startMs: Long, endMs: Long) {
        mutableState.update { current ->
            val editor = current.clipEditor ?: return@update current
            val boundedStart = startMs.coerceIn(0, editor.durationMs)
            val boundedEnd = endMs.coerceIn(0, editor.durationMs)
            if (boundedEnd - boundedStart < ClipExporter.MIN_CLIP_MS) current
            else if (boundedEnd - boundedStart > ClipExporter.MAX_CLIP_MS) current
            else current.copy(
                clipEditor = editor.copy(startMs = boundedStart, endMs = boundedEnd)
            )
        }
    }

    fun adjustClipStart(deltaMs: Long) {
        state.value.clipEditor?.let {
            setClipRange(it.startMs + deltaMs, it.endMs)
        }
    }

    fun adjustClipEnd(deltaMs: Long) {
        state.value.clipEditor?.let {
            setClipRange(it.startMs, it.endMs + deltaMs)
        }
    }

    fun closeClipEditor() {
        mutableState.update { it.copy(clipEditor = null) }
    }

    fun saveClip(transcribe: Boolean) {
        val editor = state.value.clipEditor ?: return
        viewModelScope.launch {
            mutableState.update {
                it.copy(clipEditor = editor.copy(saving = true))
            }
            runCatching {
                val file = clipExporter.export(
                    editor.episode,
                    editor.startMs,
                    editor.endMs
                )
                val now = System.currentTimeMillis()
                val clip = Clip(
                    id = stableId(editor.episode.id + ":" + editor.startMs + ":" + now),
                    episodeId = editor.episode.id,
                    episodeTitle = editor.episode.title,
                    podcastTitle = editor.episode.podcastTitle,
                    artworkUrl = editor.episode.artworkUrl,
                    filePath = file.absolutePath,
                    startMs = editor.startMs,
                    endMs = editor.endMs,
                    createdAt = now,
                    transcript = "",
                    transcriptState = if (transcribe) {
                        TranscriptState.SENDING
                    } else {
                        TranscriptState.LOCAL_ONLY
                    },
                    transcriptError = ""
                )
                repository.saveClip(clip)
                clip
            }.onSuccess { clip ->
                mutableState.update {
                    it.copy(
                        clipEditor = null,
                        destination = PrimaryDestination.CLIPS,
                        message = if (transcribe) {
                            "Clip saved. Sending it for transcription…"
                        } else {
                            "Clip saved locally"
                        }
                    )
                }
                if (transcribe) transcribeClip(clip)
            }.onFailure(::showFailure)
        }
    }

    fun transcribeClip(clip: Clip) {
        val apiKey = keyStore.read()
        if (apiKey.isBlank()) {
            viewModelScope.launch {
                repository.updateTranscript(
                    clip.id,
                    clip.transcript,
                    TranscriptState.FAILED,
                    "Add a Groq API key in Settings"
                )
            }
            mutableState.update {
                it.copy(settingsOpen = true, message = "Add a Groq API key to transcribe")
            }
            return
        }
        viewModelScope.launch {
            repository.updateTranscript(clip.id, clip.transcript, TranscriptState.SENDING)
            runCatching {
                transcriptionProvider.transcribe(File(clip.filePath), apiKey)
            }.onSuccess { transcript ->
                repository.updateTranscript(
                    clip.id,
                    transcript,
                    TranscriptState.COMPLETE
                )
                mutableState.update { it.copy(message = "Transcript ready") }
            }.onFailure { error ->
                repository.updateTranscript(
                    clip.id,
                    clip.transcript,
                    TranscriptState.FAILED,
                    error.readableMessage()
                )
                mutableState.update {
                    it.copy(message = "Transcript failed; the local clip is safe")
                }
            }
        }
    }

    fun setAddRssOpen(open: Boolean) {
        mutableState.update { it.copy(addRssOpen = open) }
    }

    fun setSettingsOpen(open: Boolean) {
        mutableState.update { it.copy(settingsOpen = open) }
    }

    fun setApiKeyDraft(value: String) {
        mutableState.update { it.copy(apiKeyDraft = value) }
    }

    fun saveApiKey() {
        keyStore.save(state.value.apiKeyDraft)
        mutableState.update {
            it.copy(
                settingsOpen = false,
                message = if (it.apiKeyDraft.isBlank()) {
                    "Transcription key removed"
                } else {
                    "Transcription key saved on this device"
                }
            )
        }
    }

    fun clearMessage() {
        mutableState.update { it.copy(message = "") }
    }

    private fun showFailure(error: Throwable) {
        mutableState.update {
            it.copy(busyLabel = "", message = error.readableMessage())
        }
    }

    private fun Throwable.readableMessage(): String =
        message?.substringBefore("\n")?.take(180)
            ?.ifBlank { null }
            ?: "Something went wrong. Your saved library is unchanged."

    override fun onCleared() {
        playback.close()
        store.close()
        super.onCleared()
    }
}

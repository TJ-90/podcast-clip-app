package com.tj90.podcastclip.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.tj90.podcastclip.clipping.ClipExporter
import com.tj90.podcastclip.data.local.PodcastStore
import com.tj90.podcastclip.download.EpisodeDownloadManager
import com.tj90.podcastclip.feed.RssFeedParser
import com.tj90.podcastclip.model.Clip
import com.tj90.podcastclip.model.Episode
import com.tj90.podcastclip.model.PlaybackBookmark
import com.tj90.podcastclip.model.Podcast
import com.tj90.podcastclip.model.PodcastSearchResult
import com.tj90.podcastclip.model.TranscriptState
import com.tj90.podcastclip.model.stableId
import com.tj90.podcastclip.playback.PlaybackConnection
import com.tj90.podcastclip.playback.PlaybackUiState
import com.tj90.podcastclip.repository.PodcastRepository
import com.tj90.podcastclip.transcription.GroqOutcomeUnknownException
import com.tj90.podcastclip.transcription.GroqRateLimitException
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
    val queue: List<Episode> = emptyList(),
    val downloadingIds: Set<String> = emptySet(),
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
    private val downloadManager = EpisodeDownloadManager(application)
    private val transcriptionProvider = GroqTranscriptionProvider()
    private val keyStore = SecureApiKeyStore(application)
    private val mutableState = MutableStateFlow(
        AppUiState(apiKeyDraft = keyStore.read())
    )
    private var lastBookmarkSavedAt = 0L

    val state: StateFlow<AppUiState> = mutableState

    init {
        playback.onEnded = ::playNextInQueue
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
            store.queue.collect { value ->
                mutableState.update { it.copy(queue = value) }
            }
        }
        viewModelScope.launch {
            playback.state.collect { value ->
                mutableState.update { it.copy(player = value) }
                persistBookmarkIfDue(value)
            }
        }
        store.loadPlaybackBookmark()?.let { bookmark ->
            store.findEpisode(bookmark.episodeId)?.let { episode ->
                playback.restore(episode, bookmark.positionMs, bookmark.speed)
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
        store.removeFromQueue(episode.id)
        playback.play(store.findEpisode(episode.id) ?: episode)
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

    fun enqueue(episode: Episode) {
        if (state.value.queue.any { it.id == episode.id }) {
            mutableState.update { it.copy(message = "Already in Up Next") }
            return
        }
        store.enqueue(episode.id)
        mutableState.update { it.copy(message = "Added to Up Next") }
    }

    fun removeFromQueue(episode: Episode) {
        store.removeFromQueue(episode.id)
    }

    fun clearQueue() {
        store.clearQueue()
        mutableState.update { it.copy(message = "Up Next cleared") }
    }

    fun playNextInQueue() {
        val next = store.queue.value.firstOrNull() ?: return
        play(next)
    }

    fun downloadEpisode(episode: Episode) {
        if (episode.isDownloaded || episode.id in state.value.downloadingIds) return
        viewModelScope.launch {
            mutableState.update {
                it.copy(downloadingIds = it.downloadingIds + episode.id)
            }
            runCatching { downloadManager.download(episode) }
                .onSuccess { file ->
                    store.saveDownloadedPath(episode.id, file.absolutePath)
                    mutableState.update {
                        it.copy(
                            downloadingIds = it.downloadingIds - episode.id,
                            message = "Episode ready offline"
                        )
                    }
                }
                .onFailure { error ->
                    mutableState.update {
                        it.copy(downloadingIds = it.downloadingIds - episode.id)
                    }
                    showFailure(error)
                }
        }
    }

    fun removeDownload(episode: Episode) {
        viewModelScope.launch {
            runCatching {
                check(downloadManager.delete(episode.downloadedPath)) {
                    "Could not remove the offline episode"
                }
                store.saveDownloadedPath(episode.id, "")
            }.onSuccess {
                mutableState.update { it.copy(message = "Offline copy removed") }
            }.onFailure(::showFailure)
        }
    }

    fun openClipEditor() {
        val playerState = state.value.player
        val episode = playerState.episode
        if (episode == null) {
            mutableState.update { it.copy(message = "Play an episode before making a clip") }
            return
        }
        if (episode.id.startsWith("clip-")) {
            mutableState.update { it.copy(message = "Open the source episode to make another clip") }
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
            if (boundedEnd - boundedStart !in ClipExporter.MIN_CLIP_MS..ClipExporter.MAX_CLIP_MS) {
                current
            } else {
                current.copy(clipEditor = editor.copy(startMs = boundedStart, endMs = boundedEnd))
            }
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
        val hasKey = keyStore.read().isNotBlank()
        viewModelScope.launch {
            mutableState.update {
                it.copy(clipEditor = editor.copy(saving = true))
            }
            runCatching {
                val file = clipExporter.export(editor.episode, editor.startMs, editor.endMs)
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
                    transcriptState = when {
                        !transcribe -> TranscriptState.LOCAL_ONLY
                        hasKey -> TranscriptState.SENDING
                        else -> TranscriptState.AWAITING_KEY
                    },
                    transcriptError = if (transcribe && !hasKey) {
                        "Add a Groq API key in Settings when you are ready to upload this clip."
                    } else {
                        ""
                    }
                )
                repository.saveClip(clip)
                clip
            }.onSuccess { clip ->
                mutableState.update {
                    it.copy(
                        clipEditor = null,
                        destination = PrimaryDestination.CLIPS,
                        settingsOpen = transcribe && !hasKey,
                        message = when {
                            !transcribe -> "Clip saved locally"
                            hasKey -> "Clip saved. Sending it for transcription…"
                            else -> "Clip saved locally; add a key when ready"
                        }
                    )
                }
                if (transcribe && hasKey) transcribeClip(clip)
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
                    TranscriptState.AWAITING_KEY,
                    "Add a Groq API key in Settings when you are ready to upload this clip."
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
                repository.updateTranscript(clip.id, transcript, TranscriptState.COMPLETE)
                mutableState.update { it.copy(message = "Transcript ready") }
            }.onFailure { error ->
                val state = when (error) {
                    is GroqRateLimitException -> TranscriptState.RATE_LIMITED
                    is GroqOutcomeUnknownException -> TranscriptState.OUTCOME_UNKNOWN
                    else -> TranscriptState.FAILED
                }
                repository.updateTranscript(
                    clip.id,
                    clip.transcript,
                    state,
                    error.readableMessage()
                )
                mutableState.update {
                    it.copy(
                        message = if (state == TranscriptState.OUTCOME_UNKNOWN) {
                            "Groq did not confirm the result; check usage before retrying"
                        } else {
                            "Transcript failed; the local clip is safe"
                        }
                    )
                }
            }
        }
    }

    fun deleteClip(clip: Clip) {
        viewModelScope.launch {
            runCatching {
                val directory = File(getApplication<Application>().filesDir, "clips").canonicalFile
                val file = File(clip.filePath).canonicalFile
                require(file.parentFile == directory) {
                    "Refusing to delete a file outside clip storage"
                }
                if (file.exists()) check(file.delete()) { "Could not delete the clip audio" }
                store.deleteClip(clip.id)
            }.onSuccess {
                mutableState.update { it.copy(message = "Clip deleted") }
            }.onFailure(::showFailure)
        }
    }

    fun playSource(clip: Clip) {
        val source = store.findEpisode(clip.episodeId)
        if (source == null) {
            mutableState.update { it.copy(message = "Source episode is no longer in the library") }
            return
        }
        mutableState.update { it.copy(destination = PrimaryDestination.HOME) }
        play(source)
        seekTo(clip.startMs)
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

    private fun persistBookmarkIfDue(playerState: PlaybackUiState) {
        val episode = playerState.episode ?: return
        if (episode.id.startsWith("clip-") || playerState.positionMs <= 0) return
        val now = System.currentTimeMillis()
        if (now - lastBookmarkSavedAt < BOOKMARK_INTERVAL_MS) return
        lastBookmarkSavedAt = now
        store.savePlaybackBookmark(
            PlaybackBookmark(
                episodeId = episode.id,
                positionMs = playerState.positionMs,
                speed = playerState.speed
            )
        )
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
        state.value.player.let { player ->
            val episode = player.episode
            if (episode != null && !episode.id.startsWith("clip-") && player.positionMs > 0) {
                store.savePlaybackBookmark(
                    PlaybackBookmark(episode.id, player.positionMs, player.speed)
                )
            }
        }
        playback.close()
        store.close()
        super.onCleared()
    }

    private companion object {
        const val BOOKMARK_INTERVAL_MS = 5_000L
    }
}

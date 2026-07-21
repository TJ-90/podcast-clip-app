@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package com.tj90.podcastclip.ui

import android.content.ClipData
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RangeSlider
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.FileProvider
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import coil3.compose.AsyncImage
import com.tj90.podcastclip.clipping.ClipExporter
import com.tj90.podcastclip.model.Clip
import com.tj90.podcastclip.model.Episode
import com.tj90.podcastclip.model.Podcast
import com.tj90.podcastclip.model.PodcastSearchResult
import com.tj90.podcastclip.model.TranscriptState
import java.io.File
import java.text.DateFormat
import java.util.Date
import kotlin.math.roundToLong

private val Paper = Color(0xFFF5F0E7)
private val PaperSurface = Color(0xFFFFFCF7)
private val Ink = Color(0xFF1B1D1C)
private val Rust = Color(0xFFB84D2B)
private val SoftRust = Color(0xFFF1D8CC)
private val Night = Color(0xFF161918)
private val NightSurface = Color(0xFF212523)
private val NightInk = Color(0xFFEFE9DE)

@Composable
fun PodcastClipApp(viewModel: AppViewModel = viewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbarHost = remember { SnackbarHostState() }
    val dark = isSystemInDarkTheme()
    val colors = if (dark) {
        darkColorScheme(
            primary = Color(0xFFE88967),
            onPrimary = Night,
            background = Night,
            onBackground = NightInk,
            surface = NightSurface,
            onSurface = NightInk,
            surfaceVariant = Color(0xFF2C312E),
            onSurfaceVariant = Color(0xFFC8C2BA)
        )
    } else {
        lightColorScheme(
            primary = Rust,
            onPrimary = Color.White,
            background = Paper,
            onBackground = Ink,
            surface = PaperSurface,
            onSurface = Ink,
            surfaceVariant = Color(0xFFEEE5D8),
            onSurfaceVariant = Color(0xFF655F59)
        )
    }

    LaunchedEffect(state.message) {
        if (state.message.isNotBlank()) {
            snackbarHost.showSnackbar(state.message)
            viewModel.clearMessage()
        }
    }

    MaterialTheme(
        colorScheme = colors,
        typography = MaterialTheme.typography.copy(
            headlineLarge = MaterialTheme.typography.headlineLarge.copy(
                fontWeight = FontWeight.Black,
                fontSize = 36.sp,
                lineHeight = 40.sp
            ),
            headlineMedium = MaterialTheme.typography.headlineMedium.copy(
                fontWeight = FontWeight.Bold
            ),
            titleLarge = MaterialTheme.typography.titleLarge.copy(
                fontWeight = FontWeight.Bold
            )
        )
    ) {
        Scaffold(
            containerColor = MaterialTheme.colorScheme.background,
            snackbarHost = { SnackbarHost(snackbarHost) },
            bottomBar = {
                Column {
                    state.player.episode?.let {
                        MiniPlayer(
                            episode = it,
                            playing = state.player.isPlaying,
                            progress = progress(
                                state.player.positionMs,
                                state.player.durationMs
                            ),
                            onOpen = { viewModel.setPlayerOpen(true) },
                            onToggle = viewModel::togglePlayback
                        )
                    }
                    NavigationBar(
                        containerColor = MaterialTheme.colorScheme.background
                    ) {
                        PrimaryDestination.entries.forEach { destination ->
                            NavigationBarItem(
                                selected = state.destination == destination,
                                onClick = { viewModel.selectDestination(destination) },
                                icon = {
                                    DestinationMark(
                                        label = destination.shortLabel,
                                        selected = state.destination == destination
                                    )
                                },
                                label = { Text(destination.label) }
                            )
                        }
                    }
                }
            }
        ) { innerPadding ->
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding),
                contentAlignment = Alignment.TopCenter
            ) {
                val pageModifier = Modifier
                    .fillMaxSize()
                    .widthIn(max = 720.dp)
                when (state.destination) {
                    PrimaryDestination.HOME -> HomeScreen(
                        state = state,
                        modifier = pageModifier,
                        onSettings = { viewModel.setSettingsOpen(true) },
                        onPlay = viewModel::play,
                        onDiscover = {
                            viewModel.selectDestination(PrimaryDestination.DISCOVER)
                        }
                    )
                    PrimaryDestination.DISCOVER -> DiscoverScreen(
                        state = state,
                        modifier = pageModifier,
                        onQuery = viewModel::setSearchQuery,
                        onSearch = viewModel::search,
                        onAddRss = { viewModel.setAddRssOpen(true) },
                        onSubscribe = viewModel::subscribe
                    )
                    PrimaryDestination.LIBRARY -> LibraryScreen(
                        state = state,
                        modifier = pageModifier,
                        onRefresh = { viewModel.refreshLibrary() },
                        onPlay = viewModel::play,
                        onDiscover = {
                            viewModel.selectDestination(PrimaryDestination.DISCOVER)
                        }
                    )
                    PrimaryDestination.CLIPS -> ClipsScreen(
                        state = state,
                        modifier = pageModifier,
                        onPlay = viewModel::playClip,
                        onTranscribe = viewModel::transcribeClip,
                        onSettings = { viewModel.setSettingsOpen(true) }
                    )
                }
                if (state.busyLabel.isNotBlank()) {
                    BusyBar(state.busyLabel)
                }
            }
        }

        if (state.addRssOpen) {
            AddRssDialog(
                onDismiss = { viewModel.setAddRssOpen(false) },
                onAdd = viewModel::subscribe
            )
        }
        if (state.settingsOpen) {
            SettingsSheet(
                apiKey = state.apiKeyDraft,
                onChange = viewModel::setApiKeyDraft,
                onDismiss = { viewModel.setSettingsOpen(false) },
                onSave = viewModel::saveApiKey
            )
        }
        if (state.playerOpen && state.player.episode != null) {
            PlayerSheet(
                state = state,
                onDismiss = { viewModel.setPlayerOpen(false) },
                onToggle = viewModel::togglePlayback,
                onSeekBy = viewModel::seekBy,
                onSeekTo = viewModel::seekTo,
                onSpeed = viewModel::setSpeed,
                onClip = viewModel::openClipEditor
            )
        }
        state.clipEditor?.let { editor ->
            ClipEditorSheet(
                editor = editor,
                hasApiKey = state.apiKeyDraft.isNotBlank(),
                onDismiss = viewModel::closeClipEditor,
                onRange = viewModel::setClipRange,
                onStartAdjust = viewModel::adjustClipStart,
                onEndAdjust = viewModel::adjustClipEnd,
                onSave = viewModel::saveClip
            )
        }
    }
}

@Composable
private fun HomeScreen(
    state: AppUiState,
    modifier: Modifier,
    onSettings: () -> Unit,
    onPlay: (Episode) -> Unit,
    onDiscover: () -> Unit
) {
    val featured = state.player.episode ?: state.episodes.firstOrNull()
    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(22.dp, 24.dp, 22.dp, 32.dp),
        verticalArrangement = Arrangement.spacedBy(22.dp)
    ) {
        item {
            PageHeader(
                eyebrow = "PODCAST CLIPS",
                title = "Listen closely.",
                subtitle = "A complete podcast player for keeping the exact moments that matter.",
                action = "Settings",
                onAction = onSettings
            )
        }
        if (featured != null) {
            item {
                FeatureEpisode(
                    episode = featured,
                    isCurrent = featured.id == state.player.episode?.id,
                    playing = state.player.isPlaying,
                    onPlay = { onPlay(featured) }
                )
            }
        } else {
            item {
                EmptyState(
                    title = "Your listening starts here",
                    body = "Search the podcast directory or add an RSS feed. No account is required.",
                    action = "Find podcasts",
                    onAction = onDiscover
                )
            }
        }
        if (state.episodes.isNotEmpty()) {
            item { SectionLabel("Latest from your library") }
            items(state.episodes.take(12), key = { it.id }) { episode ->
                EpisodeRow(episode, onPlay = { onPlay(episode) })
            }
        }
    }
}

@Composable
private fun DiscoverScreen(
    state: AppUiState,
    modifier: Modifier,
    onQuery: (String) -> Unit,
    onSearch: () -> Unit,
    onAddRss: () -> Unit,
    onSubscribe: (String) -> Unit
) {
    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(22.dp, 24.dp, 22.dp, 32.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            PageHeader(
                eyebrow = "DIRECTORY",
                title = "Discover",
                subtitle = "Search Apple’s public podcast directory, or bring any RSS feed.",
                action = "Add RSS",
                onAction = onAddRss
            )
        }
        item {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                OutlinedTextField(
                    value = state.searchQuery,
                    onValueChange = onQuery,
                    modifier = Modifier.weight(1f),
                    label = { Text("Podcast name or topic") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                    keyboardActions = KeyboardActions(onSearch = { onSearch() })
                )
                Button(
                    onClick = onSearch,
                    contentPadding = PaddingValues(horizontal = 18.dp, vertical = 15.dp)
                ) {
                    Text("Search")
                }
            }
        }
        if (state.searchResults.isEmpty()) {
            item {
                EmptyState(
                    title = "Search without an algorithmic feed",
                    body = "Results follow your query. Nothing is auto-followed or ranked from your listening history.",
                    action = "Add RSS instead",
                    onAction = onAddRss
                )
            }
        } else {
            item { SectionLabel("Search results") }
            items(state.searchResults, key = { it.feedUrl }) { result ->
                SearchResultRow(
                    result = result,
                    subscribed = state.podcasts.any { it.feedUrl == result.feedUrl },
                    onSubscribe = { onSubscribe(result.feedUrl) }
                )
            }
        }
    }
}

@Composable
private fun LibraryScreen(
    state: AppUiState,
    modifier: Modifier,
    onRefresh: () -> Unit,
    onPlay: (Episode) -> Unit,
    onDiscover: () -> Unit
) {
    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(22.dp, 24.dp, 22.dp, 32.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp)
    ) {
        item {
            PageHeader(
                eyebrow = "SAVED ON THIS DEVICE",
                title = "Library",
                subtitle = "Subscriptions and recent episodes, ready without an account.",
                action = "Refresh",
                onAction = onRefresh
            )
        }
        if (state.podcasts.isEmpty()) {
            item {
                EmptyState(
                    title = "No subscriptions yet",
                    body = "Add a show from Discover and its latest episodes will appear here.",
                    action = "Open Discover",
                    onAction = onDiscover
                )
            }
        } else {
            item { SectionLabel("Subscriptions") }
            items(state.podcasts, key = { it.feedUrl }) { podcast ->
                PodcastRow(podcast)
            }
            item {
                Spacer(Modifier.height(6.dp))
                SectionLabel("Recent episodes")
            }
            items(state.episodes, key = { it.id }) { episode ->
                EpisodeRow(episode, onPlay = { onPlay(episode) })
            }
        }
    }
}

@Composable
private fun ClipsScreen(
    state: AppUiState,
    modifier: Modifier,
    onPlay: (Clip) -> Unit,
    onTranscribe: (Clip) -> Unit,
    onSettings: () -> Unit
) {
    val context = LocalContext.current
    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(22.dp, 24.dp, 22.dp, 32.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp)
    ) {
        item {
            PageHeader(
                eyebrow = "LOCAL FIRST",
                title = "Clips",
                subtitle = "Playable moments stay on your device. Transcription is always optional.",
                action = "Settings",
                onAction = onSettings
            )
        }
        if (state.clips.isEmpty()) {
            item {
                EmptyState(
                    title = "No clips yet",
                    body = "While an episode is playing, open the player and choose Clip. The preceding 30 seconds are selected.",
                    action = null,
                    onAction = {}
                )
            }
        } else {
            items(state.clips, key = { it.id }) { clip ->
                ClipRow(
                    clip = clip,
                    onPlay = { onPlay(clip) },
                    onTranscribe = { onTranscribe(clip) },
                    onShare = { shareClip(context, clip) }
                )
            }
        }
    }
}

@Composable
private fun PageHeader(
    eyebrow: String,
    title: String,
    subtitle: String,
    action: String,
    onAction: () -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.Top,
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Column(Modifier.weight(1f)) {
            Text(
                eyebrow,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Bold,
                letterSpacing = 1.4.sp,
                fontSize = 12.sp
            )
            Spacer(Modifier.height(8.dp))
            Text(title, style = MaterialTheme.typography.headlineLarge)
            Spacer(Modifier.height(8.dp))
            Text(
                subtitle,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                fontSize = 16.sp,
                lineHeight = 23.sp
            )
        }
        TextButton(onClick = onAction) { Text(action) }
    }
}

@Composable
private fun FeatureEpisode(
    episode: Episode,
    isCurrent: Boolean,
    playing: Boolean,
    onPlay: () -> Unit
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = MaterialTheme.colorScheme.primary,
        contentColor = MaterialTheme.colorScheme.onPrimary,
        shape = RoundedCornerShape(26.dp)
    ) {
        Column(
            Modifier.padding(22.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                if (isCurrent) "NOW LISTENING" else "READY TO PLAY",
                fontWeight = FontWeight.Bold,
                letterSpacing = 1.2.sp,
                fontSize = 12.sp
            )
            Artwork(
                url = episode.artworkUrl,
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(2.2f)
            )
            Text(
                episode.title,
                style = MaterialTheme.typography.headlineMedium,
                maxLines = 3,
                overflow = TextOverflow.Ellipsis
            )
            Text(episode.podcastTitle)
            Button(
                onClick = onPlay,
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.onPrimary,
                    contentColor = MaterialTheme.colorScheme.primary
                )
            ) {
                Text(if (isCurrent && playing) "OPEN PLAYER" else "PLAY EPISODE")
            }
        }
    }
}

@Composable
private fun EpisodeRow(episode: Episode, onPlay: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onPlay)
            .padding(vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Artwork(episode.artworkUrl, Modifier.size(64.dp))
        Column(Modifier.weight(1f)) {
            Text(
                episode.title,
                fontWeight = FontWeight.Bold,
                fontSize = 16.sp,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
            Text(
                episode.podcastTitle,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                if (episode.publishedAt > 0) {
                    Text(
                        DateFormat.getDateInstance(DateFormat.MEDIUM)
                            .format(Date(episode.publishedAt)),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontSize = 12.sp
                    )
                }
                if (episode.durationMs > 0) {
                    Text(
                        formatTime(episode.durationMs),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontSize = 12.sp
                    )
                }
            }
        }
        Text("Play", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
    }
    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.55f))
}

@Composable
private fun PodcastRow(podcast: Podcast) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Artwork(podcast.artworkUrl, Modifier.size(72.dp))
        Column(Modifier.weight(1f)) {
            Text(
                podcast.title,
                fontWeight = FontWeight.Bold,
                fontSize = 17.sp,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
            if (podcast.author.isNotBlank()) {
                Text(
                    podcast.author,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }
        Surface(
            color = MaterialTheme.colorScheme.surfaceVariant,
            shape = RoundedCornerShape(10.dp)
        ) {
            Text("Subscribed", Modifier.padding(horizontal = 10.dp, vertical = 6.dp), fontSize = 12.sp)
        }
    }
}

@Composable
private fun SearchResultRow(
    result: PodcastSearchResult,
    subscribed: Boolean,
    onSubscribe: () -> Unit
) {
    Surface(
        color = MaterialTheme.colorScheme.surface,
        shape = RoundedCornerShape(20.dp)
    ) {
        Row(
            Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Artwork(result.artworkUrl, Modifier.size(72.dp))
            Column(Modifier.weight(1f)) {
                Text(
                    result.title,
                    fontWeight = FontWeight.Bold,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    listOf(result.author, result.genre)
                        .filter(String::isNotBlank)
                        .joinToString(" · "),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 2
                )
            }
            OutlinedButton(onClick = onSubscribe, enabled = !subscribed) {
                Text(if (subscribed) "Added" else "Add")
            }
        }
    }
}

@Composable
private fun ClipRow(
    clip: Clip,
    onPlay: () -> Unit,
    onTranscribe: () -> Unit,
    onShare: () -> Unit
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = MaterialTheme.colorScheme.surface,
        shape = RoundedCornerShape(22.dp)
    ) {
        Column(
            Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Artwork(clip.artworkUrl, Modifier.size(58.dp))
                Column(Modifier.weight(1f)) {
                    Text(
                        clip.episodeTitle,
                        fontWeight = FontWeight.Bold,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis
                    )
                    Text(
                        clip.podcastTitle + " · " + formatTime(clip.endMs - clip.startMs),
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            when (clip.transcriptState) {
                TranscriptState.COMPLETE -> {
                    Text(
                        clip.transcript,
                        lineHeight = 22.sp,
                        maxLines = 8,
                        overflow = TextOverflow.Ellipsis
                    )
                }
                TranscriptState.SENDING -> {
                    LinearProgressIndicator(Modifier.fillMaxWidth())
                    Text("Sending clip for transcription…")
                }
                TranscriptState.FAILED -> {
                    Text(
                        clip.transcriptError.ifBlank { "Transcription failed" },
                        color = MaterialTheme.colorScheme.error
                    )
                }
                TranscriptState.LOCAL_ONLY -> {
                    Text(
                        "Saved locally. No audio has been uploaded.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                TextButton(onClick = onPlay) { Text("Play clip") }
                if (clip.transcriptState != TranscriptState.COMPLETE &&
                    clip.transcriptState != TranscriptState.SENDING
                ) {
                    TextButton(onClick = onTranscribe) { Text("Transcribe") }
                }
                TextButton(onClick = onShare) { Text("Share") }
            }
        }
    }
}

@Composable
private fun MiniPlayer(
    episode: Episode,
    playing: Boolean,
    progress: Float,
    onOpen: () -> Unit,
    onToggle: () -> Unit
) {
    Surface(
        color = MaterialTheme.colorScheme.surfaceVariant,
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onOpen)
    ) {
        Column {
            LinearProgressIndicator(
                progress = { progress },
                modifier = Modifier.fillMaxWidth()
            )
            Row(
                Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Artwork(episode.artworkUrl, Modifier.size(46.dp))
                Column(Modifier.weight(1f)) {
                    Text(
                        episode.title,
                        fontWeight = FontWeight.Bold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    Text(
                        episode.podcastTitle,
                        fontSize = 12.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
                TextButton(onClick = onToggle) {
                    Text(if (playing) "Pause" else "Play", fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Composable
private fun DestinationMark(label: String, selected: Boolean) {
    Surface(
        modifier = Modifier.size(30.dp),
        color = if (selected) MaterialTheme.colorScheme.primary else Color.Transparent,
        shape = CircleShape
    ) {
        Box(contentAlignment = Alignment.Center) {
            Text(
                label,
                color = if (selected) {
                    MaterialTheme.colorScheme.onPrimary
                } else {
                    MaterialTheme.colorScheme.onSurfaceVariant
                },
                fontWeight = FontWeight.Bold
            )
        }
    }
}

@Composable
private fun PlayerSheet(
    state: AppUiState,
    onDismiss: () -> Unit,
    onToggle: () -> Unit,
    onSeekBy: (Long) -> Unit,
    onSeekTo: (Long) -> Unit,
    onSpeed: (Float) -> Unit,
    onClip: () -> Unit
) {
    val player = state.player
    val episode = player.episode ?: return
    var sliderValue by remember(player.positionMs) {
        mutableStateOf(player.positionMs.toFloat())
    }
    val duration = player.durationMs.coerceAtLeast(1)
    ModalBottomSheet(onDismissRequest = onDismiss) {
        LazyColumn(
            modifier = Modifier
                .fillMaxWidth()
                .imePadding(),
            contentPadding = PaddingValues(24.dp, 8.dp, 24.dp, 36.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            item {
                Artwork(
                    episode.artworkUrl,
                    Modifier
                        .fillMaxWidth(0.72f)
                        .aspectRatio(1f)
                )
            }
            item {
                Text(
                    episode.title,
                    style = MaterialTheme.typography.headlineMedium,
                    maxLines = 3,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    episode.podcastTitle,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            item {
                Slider(
                    value = sliderValue.coerceIn(0f, duration.toFloat()),
                    onValueChange = { sliderValue = it },
                    onValueChangeFinished = {
                        onSeekTo(sliderValue.roundToLong())
                    },
                    valueRange = 0f..duration.toFloat()
                )
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(formatTime(player.positionMs))
                    Text("-" + formatTime((duration - player.positionMs).coerceAtLeast(0)))
                }
            }
            item {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    OutlinedButton(onClick = { onSeekBy(-30_000) }) { Text("−30") }
                    Button(onClick = onToggle, modifier = Modifier.height(54.dp)) {
                        Text(if (player.isPlaying) "Pause" else "Play")
                    }
                    OutlinedButton(onClick = { onSeekBy(30_000) }) { Text("+30") }
                }
            }
            item {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    listOf(1f, 1.25f, 1.5f, 2f).forEach { speed ->
                        TextButton(onClick = { onSpeed(speed) }) {
                            Text(
                                speedLabel(speed),
                                fontWeight = if (player.speed == speed) {
                                    FontWeight.Black
                                } else {
                                    FontWeight.Normal
                                }
                            )
                        }
                    }
                }
            }
            item {
                Button(
                    onClick = onClip,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Clip preceding 30 seconds")
                }
            }
        }
    }
}

@Composable
private fun ClipEditorSheet(
    editor: ClipEditorState,
    hasApiKey: Boolean,
    onDismiss: () -> Unit,
    onRange: (Long, Long) -> Unit,
    onStartAdjust: (Long) -> Unit,
    onEndAdjust: (Long) -> Unit,
    onSave: (Boolean) -> Unit
) {
    val maxDuration = editor.durationMs.coerceAtLeast(ClipExporter.MIN_CLIP_MS)
    ModalBottomSheet(
        onDismissRequest = { if (!editor.saving) onDismiss() }
    ) {
        LazyColumn(
            modifier = Modifier
                .fillMaxWidth()
                .imePadding(),
            contentPadding = PaddingValues(24.dp, 8.dp, 24.dp, 36.dp),
            verticalArrangement = Arrangement.spacedBy(18.dp)
        ) {
            item {
                Text("CLIP EDITOR", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                Text("Keep the exact moment", style = MaterialTheme.typography.headlineMedium)
                Text(
                    editor.episode.title,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
            }
            item {
                RangeSlider(
                    value = editor.startMs.toFloat()..editor.endMs.toFloat(),
                    onValueChange = {
                        onRange(it.start.roundToLong(), it.endInclusive.roundToLong())
                    },
                    valueRange = 0f..maxDuration.toFloat(),
                    enabled = !editor.saving
                )
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Column {
                        Text("START", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                        Text(formatTimePrecise(editor.startMs), style = MaterialTheme.typography.titleLarge)
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        Text("END", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                        Text(formatTimePrecise(editor.endMs), style = MaterialTheme.typography.titleLarge)
                    }
                }
                Text(
                    "Clip length " + formatTimePrecise(editor.endMs - editor.startMs),
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            item {
                Text("Adjust start", fontWeight = FontWeight.Bold)
                AdjustmentRow(onAdjust = onStartAdjust, enabled = !editor.saving)
                Spacer(Modifier.height(8.dp))
                Text("Adjust end", fontWeight = FontWeight.Bold)
                AdjustmentRow(onAdjust = onEndAdjust, enabled = !editor.saving)
            }
            if (editor.saving) {
                item {
                    LinearProgressIndicator(Modifier.fillMaxWidth())
                    Text("Saving playable local audio…")
                }
            }
            item {
                Button(
                    onClick = { onSave(false) },
                    enabled = !editor.saving,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Save clip")
                }
                FilledTonalButton(
                    onClick = { onSave(true) },
                    enabled = !editor.saving,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(if (hasApiKey) "Save & transcribe" else "Save & add transcription key")
                }
                Text(
                    "Range: 3 seconds to 5 minutes. Saving happens before any upload.",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    fontSize = 12.sp
                )
            }
        }
    }
}

@Composable
private fun AdjustmentRow(onAdjust: (Long) -> Unit, enabled: Boolean) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        listOf(-1_000L to "−1s", -100L to "−0.1s", 100L to "+0.1s", 1_000L to "+1s")
            .forEach { (amount, label) ->
                OutlinedButton(
                    onClick = { onAdjust(amount) },
                    enabled = enabled,
                    modifier = Modifier.weight(1f),
                    contentPadding = PaddingValues(horizontal = 4.dp, vertical = 10.dp)
                ) {
                    Text(label)
                }
            }
    }
}

@Composable
private fun SettingsSheet(
    apiKey: String,
    onChange: (String) -> Unit,
    onDismiss: () -> Unit,
    onSave: () -> Unit
) {
    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .imePadding()
                .padding(24.dp, 8.dp, 24.dp, 36.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text("Settings", style = MaterialTheme.typography.headlineMedium)
            Text(
                "Transcription is optional. Groq lists Whisper Large V3 Turbo at $0.04 per audio hour.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                lineHeight = 22.sp
            )
            OutlinedTextField(
                value = apiKey,
                onValueChange = onChange,
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Groq API key") },
                singleLine = true,
                visualTransformation = PasswordVisualTransformation()
            )
            Text(
                "The key is encrypted with Android Keystore and never embedded in the app or repository.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                fontSize = 12.sp
            )
            Button(onClick = onSave, modifier = Modifier.fillMaxWidth()) {
                Text(if (apiKey.isBlank()) "Remove key" else "Save key")
            }
        }
    }
}

@Composable
private fun AddRssDialog(onDismiss: () -> Unit, onAdd: (String) -> Unit) {
    var value by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Add podcast by RSS") },
        text = {
            OutlinedTextField(
                value = value,
                onValueChange = { value = it },
                label = { Text("https://example.com/feed.xml") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                keyboardActions = KeyboardActions(onDone = { onAdd(value) })
            )
        },
        confirmButton = {
            Button(onClick = { onAdd(value) }, enabled = value.isNotBlank()) {
                Text("Add podcast")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        }
    )
}

@Composable
private fun Artwork(url: String, modifier: Modifier) {
    AsyncImage(
        model = url.takeIf { it.isNotBlank() },
        contentDescription = null,
        modifier = modifier
            .clip(RoundedCornerShape(16.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant),
        contentScale = ContentScale.Crop
    )
}

@Composable
private fun SectionLabel(text: String) {
    Text(
        text.uppercase(),
        color = MaterialTheme.colorScheme.primary,
        fontWeight = FontWeight.Bold,
        letterSpacing = 1.2.sp,
        fontSize = 12.sp
    )
}

@Composable
private fun EmptyState(
    title: String,
    body: String,
    action: String?,
    onAction: () -> Unit
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = MaterialTheme.colorScheme.surface,
        shape = RoundedCornerShape(22.dp)
    ) {
        Column(
            Modifier.padding(22.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Text(title, style = MaterialTheme.typography.titleLarge)
            Text(
                body,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                lineHeight = 22.sp
            )
            action?.let {
                TextButton(onClick = onAction) { Text(it) }
            }
        }
    }
}

@Composable
private fun BusyBar(label: String) {
    Surface(
        modifier = Modifier
            .padding(16.dp)
            .fillMaxWidth()
            .widthIn(max = 520.dp),
        color = MaterialTheme.colorScheme.inverseSurface,
        contentColor = MaterialTheme.colorScheme.inverseOnSurface,
        shape = RoundedCornerShape(16.dp)
    ) {
        Column {
            LinearProgressIndicator(Modifier.fillMaxWidth())
            Text(label, Modifier.padding(16.dp), fontWeight = FontWeight.Bold)
        }
    }
}

private fun progress(position: Long, duration: Long): Float =
    if (duration > 0) (position.toFloat() / duration.toFloat()).coerceIn(0f, 1f) else 0f

private fun formatTime(milliseconds: Long): String {
    val totalSeconds = (milliseconds.coerceAtLeast(0) / 1000)
    val hours = totalSeconds / 3600
    val minutes = (totalSeconds % 3600) / 60
    val seconds = totalSeconds % 60
    return if (hours > 0) {
        "%d:%02d:%02d".format(hours, minutes, seconds)
    } else {
        "%d:%02d".format(minutes, seconds)
    }
}

private fun formatTimePrecise(milliseconds: Long): String {
    val totalTenths = milliseconds.coerceAtLeast(0) / 100
    val minutes = totalTenths / 600
    val seconds = (totalTenths % 600) / 10
    val tenths = totalTenths % 10
    return "%d:%02d.%d".format(minutes, seconds, tenths)
}

private fun speedLabel(speed: Float): String =
    if (speed % 1f == 0f) speed.toInt().toString() + "×" else speed.toString() + "×"

private fun shareClip(context: android.content.Context, clip: Clip) {
    val file = File(clip.filePath)
    if (!file.exists()) return
    val uri: Uri = FileProvider.getUriForFile(
        context,
        context.packageName + ".files",
        file
    )
    val text = buildString {
        append(clip.episodeTitle)
        append(" — ")
        append(clip.podcastTitle)
        if (clip.transcript.isNotBlank()) {
            append("\n\n")
            append(clip.transcript)
        }
    }
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "audio/mp4"
        putExtra(Intent.EXTRA_STREAM, uri)
        putExtra(Intent.EXTRA_TEXT, text)
        clipData = ClipData.newRawUri("Podcast clip", uri)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    context.startActivity(Intent.createChooser(intent, "Share clip"))
}

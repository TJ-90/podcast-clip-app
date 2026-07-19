package com.tj90.podcastclip.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.weight
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val Paper = Color(0xFFF5F0E7)
private val Ink = Color(0xFF1B1D1C)
private val Rust = Color(0xFFB84D2B)
private val NightPaper = Color(0xFF161918)
private val NightInk = Color(0xFFEFE9DE)

private data class Destination(val label: String, val symbol: String)
private val destinations = listOf(
    Destination("Home", "H"),
    Destination("Discover", "D"),
    Destination("Library", "L"),
    Destination("Clips", "C")
)

@Composable
fun PodcastClipApp() {
    var selected by rememberSaveable { mutableIntStateOf(0) }
    MaterialTheme(
        colorScheme = lightColorScheme(
            primary = Rust,
            onPrimary = Color.White,
            background = Paper,
            onBackground = Ink,
            surface = Color(0xFFFFFCF7),
            onSurface = Ink,
            surfaceVariant = Color(0xFFEEE5D8)
        ),
        typography = MaterialTheme.typography.copy(
            headlineLarge = MaterialTheme.typography.headlineLarge.copy(
                fontFamily = FontFamily.Serif,
                fontWeight = FontWeight.Bold,
                fontSize = 36.sp
            )
        )
    ) {
        Scaffold(
            containerColor = MaterialTheme.colorScheme.background,
            bottomBar = {
                Column {
                    FoundationMiniPlayer()
                    NavigationBar(containerColor = MaterialTheme.colorScheme.background) {
                        destinations.forEachIndexed { index, item ->
                            NavigationBarItem(
                                selected = selected == index,
                                onClick = { selected = index },
                                icon = {
                                    Surface(
                                        modifier = Modifier.size(30.dp),
                                        shape = CircleShape,
                                        color = if (selected == index) Rust else Color.Transparent
                                    ) {
                                        Box(contentAlignment = Alignment.Center) {
                                            Text(
                                                item.symbol,
                                                color = if (selected == index) Color.White else Ink,
                                                fontWeight = FontWeight.Bold
                                            )
                                        }
                                    }
                                },
                                label = { Text(item.label) }
                            )
                        }
                    }
                }
            }
        ) { inner ->
            FoundationScreen(
                destination = destinations[selected].label,
                modifier = Modifier.padding(inner)
            )
        }
    }
}

@Composable
private fun FoundationScreen(destination: String, modifier: Modifier = Modifier) {
    val rows = when (destination) {
        "Discover" -> listOf("Search every podcast", "Add a show by RSS", "Recent searches")
        "Library" -> listOf("Downloaded episodes", "Subscriptions", "Listening history")
        "Clips" -> listOf("Morning briefing · 00:30", "Design Details · 01:12", "No transcript required")
        else -> listOf("City Limits · 18 min left", "The Daily Signal · New", "Design Details · Saved")
    }
    LazyColumn(
        modifier = modifier.fillMaxSize().background(MaterialTheme.colorScheme.background),
        contentPadding = PaddingValues(horizontal = 22.dp, vertical = 24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Text("PODCAST CLIPS", color = Rust, fontWeight = FontWeight.Bold, letterSpacing = 1.6.sp)
            Spacer(Modifier.height(12.dp))
            Text(destination, style = MaterialTheme.typography.headlineLarge)
            Text(
                if (destination == "Home") "Listen freely. Keep the exact moments that matter."
                else "A focused place for ${destination.lowercase()}.",
                color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.68f),
                fontSize = 16.sp
            )
        }
        item {
            Surface(
                color = Rust,
                contentColor = Color.White,
                shape = RoundedCornerShape(26.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("CONTINUE LISTENING", fontWeight = FontWeight.Bold, letterSpacing = 1.2.sp)
                    Text("The shape of a city after dark", fontFamily = FontFamily.Serif, fontSize = 27.sp, fontWeight = FontWeight.Bold)
                    Text("City Limits · 12:48 remaining")
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Button(
                            onClick = {},
                            colors = ButtonDefaults.buttonColors(containerColor = Color.White, contentColor = Rust)
                        ) { Text("PLAY", fontWeight = FontWeight.Bold) }
                        TextButton(onClick = {}) { Text("CLIP 30 SEC", color = Color.White, fontWeight = FontWeight.Bold) }
                    }
                }
            }
        }
        item { Text("FOR YOU, NOT FROM AN ALGORITHM", color = Rust, fontWeight = FontWeight.Bold, letterSpacing = 1.1.sp) }
        items(rows) { title ->
            Surface(
                color = MaterialTheme.colorScheme.surface,
                shape = RoundedCornerShape(20.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    Modifier.padding(18.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    Box(Modifier.size(52.dp).background(Rust, RoundedCornerShape(15.dp)))
                    Column(Modifier.weight(1f)) {
                        Text(title, fontWeight = FontWeight.Bold, fontSize = 17.sp)
                        Text("Ready when you are", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.58f))
                    }
                    Text("•••", fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Composable
private fun FoundationMiniPlayer() {
    Surface(color = MaterialTheme.colorScheme.surfaceVariant) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Box(Modifier.size(44.dp).background(Rust, RoundedCornerShape(13.dp)))
            Column(Modifier.weight(1f)) {
                Text("City Limits", fontWeight = FontWeight.Bold)
                Text("The shape of a city after dark", fontSize = 12.sp)
            }
            Text("▶", color = Rust, fontSize = 24.sp)
        }
    }
}

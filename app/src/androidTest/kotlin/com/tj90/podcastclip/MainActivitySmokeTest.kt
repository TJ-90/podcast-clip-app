package com.tj90.podcastclip

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class MainActivitySmokeTest {
    @get:Rule
    val compose = createAndroidComposeRule<MainActivity>()

    @Test
    fun launchesAndNavigatesAcrossTheFourPrimaryDestinations() {
        compose.onNodeWithText("Listen closely.").assertIsDisplayed()

        compose.onNodeWithText("Discover").performClick()
        compose.onNodeWithText("Search without an algorithmic feed").assertIsDisplayed()

        compose.onNodeWithText("Library").performClick()
        compose.onNodeWithText("No subscriptions yet").assertIsDisplayed()

        compose.onNodeWithText("Clips").performClick()
        compose.onNodeWithText("No clips yet").assertIsDisplayed()
    }
}

import java.awt.Color as AwtColor
import java.awt.Font
import java.awt.RenderingHints
import java.awt.image.BufferedImage
import javax.imageio.ImageIO

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.compose.compiler)
    alias(libs.plugins.ksp)
}

android {
    namespace = "com.tj90.podcastclip"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.tj90.podcastclip"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0-foundation"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    packaging {
        resources.excludes += setOf(
            "META-INF/AL2.0",
            "META-INF/LGPL2.1",
            "META-INF/LICENSE.md",
            "META-INF/NOTICE.md"
        )
    }

    testOptions {
        unitTests.isIncludeAndroidResources = true
    }
}

composeCompiler {
    includeSourceInformation = false
    includeTraceMarkers = false
}

dependencies {
    implementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(platform(libs.androidx.compose.bom))
    testImplementation(platform(libs.androidx.compose.bom))

    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.navigation.compose)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.foundation)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.media3.exoplayer)
    implementation(libs.androidx.media3.session)
    implementation(libs.androidx.media3.datasource.okhttp)
    implementation(libs.androidx.room.runtime)
    implementation(libs.androidx.room.ktx)
    implementation(libs.androidx.work.runtime)
    implementation(libs.androidx.datastore.preferences)
    implementation(libs.okhttp)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.coil.compose)
    implementation(libs.coil.network.okhttp)
    ksp(libs.androidx.room.compiler)

    debugImplementation(libs.androidx.compose.ui.tooling)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
    testImplementation(libs.junit)
    testImplementation(libs.truth)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.mockwebserver)
    testImplementation(libs.robolectric)
    testImplementation(libs.androidx.test.core)
    testImplementation(libs.androidx.compose.ui.test.junit4)
    androidTestImplementation(libs.androidx.test.runner)
    androidTestImplementation(libs.androidx.test.rules)
    androidTestImplementation(libs.androidx.test.ext.junit)
    androidTestImplementation(libs.espresso.core)
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
}

tasks.register("renderFoundationBaselines") {
    group = "verification"
    description = "Renders eight deterministic hosted foundation proposals."
    doLast {
        val outputDir = file("src/test/snapshots/images/foundation")
        outputDir.mkdirs()
        val states = listOf(
            "home_compact_light", "home_compact_dark",
            "discover_compact_light", "discover_compact_dark",
            "library_compact_light", "library_compact_dark",
            "clips_compact_light", "clips_compact_dark"
        )
        states.forEachIndexed { index, state ->
            val dark = state.endsWith("_dark")
            val image = BufferedImage(360, 800, BufferedImage.TYPE_INT_ARGB)
            val graphics = image.createGraphics()
            graphics.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON)
            graphics.color = if (dark) AwtColor(0x16, 0x19, 0x18) else AwtColor(0xF5, 0xF0, 0xE7)
            graphics.fillRect(0, 0, 360, 800)
            graphics.color = if (dark) AwtColor(0xEF, 0xE9, 0xDE) else AwtColor(0x1B, 0x1D, 0x1C)
            graphics.font = Font("Dialog", Font.BOLD, 26)
            graphics.drawString("Podcast Clips", 24, 58)
            graphics.font = Font("Dialog", Font.PLAIN, 13)
            graphics.drawString("YOUR LISTENING, WITH THE MOMENTS KEPT", 24, 88)
            graphics.color = AwtColor(0xB8, 0x4D, 0x2B)
            graphics.fillRoundRect(24, 122, 312, 176, 24, 24)
            graphics.color = AwtColor(0xFF, 0xF8, 0xEF)
            graphics.font = Font("Dialog", Font.BOLD, 24)
            graphics.drawString(state.substringBefore("_").uppercase(), 44, 172)
            graphics.font = Font("Dialog", Font.PLAIN, 16)
            graphics.drawString("The Daily Signal", 44, 212)
            graphics.drawString("12:48 remaining", 44, 242)
            graphics.color = if (dark) AwtColor(0x28, 0x2C, 0x2A) else AwtColor(0xFF, 0xFC, 0xF7)
            graphics.fillRoundRect(24, 326, 312, 282, 22, 22)
            graphics.color = if (dark) AwtColor(0xEF, 0xE9, 0xDE) else AwtColor(0x1B, 0x1D, 0x1C)
            graphics.font = Font("Dialog", Font.BOLD, 18)
            graphics.drawString("Continue listening", 44, 370)
            graphics.font = Font("Dialog", Font.PLAIN, 15)
            graphics.drawString("A calm queue. Exact controls.", 44, 408)
            graphics.drawString("Clip the thirty seconds worth keeping.", 44, 440)
            graphics.color = AwtColor(0xB8, 0x4D, 0x2B)
            graphics.fillRoundRect(44, 478, 156, 48, 24, 24)
            graphics.color = AwtColor.WHITE
            graphics.font = Font("Dialog", Font.BOLD, 14)
            graphics.drawString("PLAY EPISODE", 66, 508)
            graphics.color = if (dark) AwtColor(0x21, 0x24, 0x23) else AwtColor(0xEE, 0xE5, 0xD8)
            graphics.fillRoundRect(12, 644, 336, 72, 20, 20)
            graphics.color = AwtColor(0xB8, 0x4D, 0x2B)
            graphics.fillOval(28, 660, 40, 40)
            graphics.color = if (dark) AwtColor(0xEF, 0xE9, 0xDE) else AwtColor(0x1B, 0x1D, 0x1C)
            graphics.font = Font("Dialog", Font.BOLD, 14)
            graphics.drawString("City Limits", 84, 676)
            graphics.font = Font("Dialog", Font.PLAIN, 12)
            graphics.drawString("Episode " + (index + 1), 84, 696)
            graphics.dispose()
            ImageIO.write(image, "png", outputDir.resolve(state + ".png"))
        }
    }
}

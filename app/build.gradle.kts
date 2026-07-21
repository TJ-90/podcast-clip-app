import java.awt.Color as AwtColor
import java.awt.Font
import java.awt.RenderingHints
import java.awt.image.BufferedImage
import javax.imageio.ImageIO

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.compose.compiler)
}

android {
    namespace = "com.tj90.podcastclip"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.tj90.podcastclip"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
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

    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.foundation)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.media3.exoplayer)
    implementation(libs.androidx.media3.session)
    implementation(libs.androidx.media3.transformer)
    implementation(libs.androidx.media3.datasource.okhttp)
    implementation(libs.okhttp)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.coil.compose)
    implementation(libs.coil.network.okhttp)

    debugImplementation(libs.androidx.compose.ui.tooling)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
    testImplementation(libs.junit)
    testImplementation(libs.truth)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.robolectric)
    testImplementation(libs.androidx.test.core)
    testImplementation(libs.androidx.compose.ui.test.junit4)
    androidTestImplementation(libs.androidx.test.runner)
    androidTestImplementation(libs.androidx.test.ext.junit)
    androidTestImplementation(libs.espresso.core)
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
}

tasks.register("renderUiBaselines") {
    group = "verification"
    description = "Renders deterministic editorial UI proposals in CI."
    doLast {
        val outputDir = file("build/reports/ui-baselines")
        outputDir.mkdirs()
        listOf("home", "discover", "library", "clips").forEachIndexed { index, screen ->
            val image = BufferedImage(412, 892, BufferedImage.TYPE_INT_ARGB)
            val graphics = image.createGraphics()
            graphics.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON)
            graphics.color = AwtColor(0xF5, 0xF0, 0xE7)
            graphics.fillRect(0, 0, 412, 892)
            graphics.color = AwtColor(0x1B, 0x1D, 0x1C)
            graphics.font = Font("Dialog", Font.BOLD, 34)
            graphics.drawString(screen.replaceFirstChar { it.uppercase() }, 24, 76)
            graphics.color = AwtColor(0xB8, 0x4D, 0x2B)
            graphics.fillRoundRect(24, 116, 364, 210, 26, 26)
            graphics.color = AwtColor.WHITE
            graphics.font = Font("Dialog", Font.BOLD, 19)
            graphics.drawString(if (index == 3) "Saved moments" else "Continue listening", 48, 166)
            graphics.font = Font("Dialog", Font.PLAIN, 15)
            graphics.drawString("Exact controls. Calm listening.", 48, 202)
            graphics.color = AwtColor(0xFF, 0xFC, 0xF7)
            graphics.fillRoundRect(24, 354, 364, 104, 20, 20)
            graphics.fillRoundRect(24, 476, 364, 104, 20, 20)
            graphics.fillRoundRect(24, 598, 364, 104, 20, 20)
            graphics.color = AwtColor(0x1B, 0x1D, 0x1C)
            graphics.font = Font("Dialog", Font.BOLD, 16)
            graphics.drawString("Podcast title", 48, 398)
            graphics.drawString("Episode ready to play", 48, 520)
            graphics.drawString("Another thoughtful listen", 48, 642)
            graphics.dispose()
            ImageIO.write(image, "png", outputDir.resolve("$screen.png"))
        }
    }
}

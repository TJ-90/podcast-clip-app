package com.tj90.podcastclip.download

import android.content.Context
import com.tj90.podcastclip.model.Episode
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.util.concurrent.TimeUnit

class EpisodeDownloadManager(
    context: Context,
    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(5, TimeUnit.MINUTES)
        .build()
) {
    private val directory = File(context.applicationContext.filesDir, "episodes")

    suspend fun download(episode: Episode): File = withContext(Dispatchers.IO) {
        directory.mkdirs()
        val output = File(directory, episode.id + ".audio")
        if (output.isFile && output.length() > 0) return@withContext output
        val partial = File(directory, episode.id + ".partial")
        partial.delete()
        val request = Request.Builder().url(episode.audioUrl).get().build()
        try {
            client.newCall(request).execute().use { response ->
                check(response.isSuccessful) { "Download failed with HTTP ${response.code}" }
                val body = checkNotNull(response.body) { "Episode download was empty" }
                val declaredLength = body.contentLength()
                require(declaredLength < 0 || declaredLength <= MAX_EPISODE_BYTES) {
                    "Episode is larger than the 1 GB offline limit"
                }
                body.byteStream().use { input ->
                    partial.outputStream().use { outputStream ->
                        val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
                        var total = 0L
                        while (true) {
                            val count = input.read(buffer)
                            if (count < 0) break
                            total += count
                            require(total <= MAX_EPISODE_BYTES) {
                                "Episode exceeded the 1 GB offline limit"
                            }
                            outputStream.write(buffer, 0, count)
                        }
                    }
                }
            }
            require(partial.length() > 0) { "Episode download was empty" }
            check(partial.renameTo(output)) { "Could not finish the offline download" }
            output
        } catch (error: Throwable) {
            partial.delete()
            throw error
        }
    }

    suspend fun delete(path: String): Boolean = withContext(Dispatchers.IO) {
        if (path.isBlank()) return@withContext true
        directory.mkdirs()
        val target = File(path)
        val insideDirectory = target.canonicalFile.parentFile == directory.canonicalFile
        require(insideDirectory) { "Refusing to delete a file outside offline storage" }
        !target.exists() || target.delete()
    }

    companion object {
        private const val MAX_EPISODE_BYTES = 1_073_741_824L
    }
}

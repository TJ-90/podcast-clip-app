package com.tj90.podcastclip.network

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import com.google.common.truth.Truth.assertThat
import com.tj90.podcastclip.R
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.xmlpull.v1.XmlPullParser

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class NetworkPolicyTest {
    @Test
    fun legacyPublisherTrafficIsExplicitlyPermitted() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val parser = context.resources.getXml(R.xml.network_security_config)
        var permitted: Boolean? = null
        while (parser.eventType != XmlPullParser.END_DOCUMENT) {
            if (parser.eventType == XmlPullParser.START_TAG && parser.name == "base-config") {
                permitted = parser.getAttributeBooleanValue(
                    null,
                    "cleartextTrafficPermitted",
                    false
                )
                break
            }
            parser.next()
        }
        parser.close()

        assertThat(permitted).isTrue()
    }
}

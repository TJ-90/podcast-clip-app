package com.tj90.podcastclip.model

import com.google.common.truth.Truth.assertThat
import org.junit.Test

class ModelsTest {
    @Test
    fun stableIdIsDeterministicAndCompact() {
        val first = stableId("feed::episode")
        val second = stableId("feed::episode")

        assertThat(first).isEqualTo(second)
        assertThat(first).hasLength(32)
        assertThat(first).matches("[0-9a-f]+")
    }

    @Test
    fun transcriptStatesMakeEveryBillingRelevantOutcomeExplicit() {
        assertThat(TranscriptState.entries).containsExactly(
            TranscriptState.LOCAL_ONLY,
            TranscriptState.AWAITING_KEY,
            TranscriptState.SENDING,
            TranscriptState.COMPLETE,
            TranscriptState.RATE_LIMITED,
            TranscriptState.OUTCOME_UNKNOWN,
            TranscriptState.FAILED
        ).inOrder()
    }
}

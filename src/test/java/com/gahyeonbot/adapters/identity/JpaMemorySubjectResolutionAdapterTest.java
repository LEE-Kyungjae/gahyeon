package com.gahyeonbot.adapters.identity;

import com.gahyeonbot.application.life.CharacterConversationContext;
import com.gahyeonbot.core.identity.ActorId;
import com.gahyeonbot.core.identity.IdentityProvider;
import com.gahyeonbot.core.session.*;
import com.gahyeonbot.entity.ExternalIdentity;
import com.gahyeonbot.repository.ExternalIdentityRepository;
import org.junit.jupiter.api.Test;

import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class JpaMemorySubjectResolutionAdapterTest {
    @Test
    void linkedPrincipalUsesCanonicalZezeStudioUuid() {
        var identities = mock(ExternalIdentityRepository.class);
        var linked = ExternalIdentity.builder()
                .provider(IdentityProvider.ZEZESTUDIO)
                .externalId("11111111-1111-1111-1111-111111111111")
                .build();
        when(identities.findByProviderAndPrincipal_Id(IdentityProvider.ZEZESTUDIO, 42L))
                .thenReturn(Optional.of(linked));

        var resolved = new JpaMemorySubjectResolutionAdapter(identities).resolve(session(Map.of()));

        assertThat(resolved.clientContext())
                .containsEntry(CharacterConversationContext.SUBJECT_ID_KEY,
                        "zezestudio:11111111-1111-1111-1111-111111111111")
                .containsEntry(CharacterConversationContext.SUBJECT_PERSISTENCE_KEY, "durable");
    }

    @Test
    void unlinkedPrincipalStaysInItsOwnProvisionalNamespace() {
        var identities = mock(ExternalIdentityRepository.class);
        when(identities.findByProviderAndPrincipal_Id(IdentityProvider.ZEZESTUDIO, 42L))
                .thenReturn(Optional.empty());

        var resolved = new JpaMemorySubjectResolutionAdapter(identities).resolve(session(Map.of()));

        assertThat(resolved.clientContext())
                .containsEntry(CharacterConversationContext.SUBJECT_ID_KEY, "principal:42")
                .containsEntry(CharacterConversationContext.SUBJECT_PERSISTENCE_KEY, "provisional");
    }

    @Test
    void explicitEphemeralSpeakerCanNeverBeUpgradedByAccountLookup() {
        var identities = mock(ExternalIdentityRepository.class);
        var resolved = new JpaMemorySubjectResolutionAdapter(identities).resolve(session(Map.of(
                CharacterConversationContext.SUBJECT_PERSISTENCE_KEY, "ephemeral",
                CharacterConversationContext.SUBJECT_ID_KEY, "forged")));

        assertThat(resolved.clientContext()).doesNotContainKey(CharacterConversationContext.SUBJECT_ID_KEY);
        verifyNoInteractions(identities);
    }

    private static ConversationSession session(Map<String, String> context) {
        return new ConversationSession(new ConversationSessionId("test"), new ActorId(42),
                ClientSource.DISCORD, ConversationModality.VOICE, context);
    }
}

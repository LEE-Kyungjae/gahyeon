package com.gahyeonbot.adapters.identity;

import com.gahyeonbot.core.identity.ActorId;
import com.gahyeonbot.core.identity.IdentityProvider;
import com.gahyeonbot.entity.Principal;
import com.gahyeonbot.repository.ExternalIdentityRepository;
import com.gahyeonbot.repository.IdentityLinkTokenRepository;
import com.gahyeonbot.repository.PrincipalRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.HexFormat;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@DataJpaTest
class ZezeStudioLinkServiceTest {
    private static final Instant NOW = Instant.parse("2026-08-24T12:00:00Z");
    private static final String SECRET = "test-only-shared-secret-with-enough-entropy";

    @Autowired PrincipalRepository principals;
    @Autowired ExternalIdentityRepository externalIdentities;
    @Autowired IdentityLinkTokenRepository tokens;

    private ZezeStudioLinkService service;

    @Test
    void declaresTheRuntimeConstructorForSpringInjection() throws Exception {
        var constructor = ZezeStudioLinkService.class.getConstructor(
                PrincipalRepository.class,
                ExternalIdentityRepository.class,
                IdentityLinkTokenRepository.class,
                ZezeStudioLinkProperties.class);

        assertThat(constructor.isAnnotationPresent(Autowired.class)).isTrue();
    }

    @BeforeEach
    void setUp() {
        var properties = new ZezeStudioLinkProperties();
        properties.setAuthorizeUrl("https://ppituruppaturu.com/connect/gahyeon");
        properties.setSharedSecret(SECRET);
        service = new ZezeStudioLinkService(principals, externalIdentities, tokens, properties,
                Clock.fixed(NOW, ZoneOffset.UTC));
        principals.save(Principal.builder().id(42L).displayName("discord-user").build());
    }

    @Test
    void linksExactlyOnceUsingOnlyAHashedShortLivedCodeAndValidServerSignature() {
        var issued = service.issue(new ActorId(42));
        String code = queryCode(issued.url());
        long timestamp = NOW.getEpochSecond();
        String platformUserId = "2d9bfa3a-833c-4da5-bb63-0d6be6fa210c";

        assertThat(issued.url()).startsWith("https://ppituruppaturu.com/connect/gahyeon?code=");
        assertThat(tokens.findById(code)).isEmpty();
        assertThat(tokens.findAll()).singleElement()
                .satisfies(token -> {
                    assertThat(token.getTokenHash()).hasSize(64);
                    assertThat(token.getTargetProvider()).isEqualTo(IdentityProvider.ZEZESTUDIO);
                });

        service.complete(code, platformUserId, timestamp,
                sign(ZezeStudioLinkService.canonical(code, platformUserId, timestamp)));

        assertThat(externalIdentities.findByProviderAndExternalId(
                IdentityProvider.ZEZESTUDIO, platformUserId))
                .get().extracting(identity -> identity.getPrincipal().getId()).isEqualTo(42L);
        assertThatThrownBy(() -> service.complete(code, platformUserId, timestamp,
                sign(ZezeStudioLinkService.canonical(code, platformUserId, timestamp))))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void rejectsTamperedExpiredAndCrossAccountAttempts() {
        var issued = service.issue(new ActorId(42));
        String code = queryCode(issued.url());
        long timestamp = NOW.getEpochSecond();

        assertThatThrownBy(() -> service.complete(code, "platform-user", timestamp, "0".repeat(64)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> service.complete(code, "platform-user", timestamp - 121,
                sign(ZezeStudioLinkService.canonical(code, "platform-user", timestamp - 121))))
                .isInstanceOf(IllegalArgumentException.class);

        principals.save(Principal.builder().id(77L).displayName("other").build());
        externalIdentities.save(com.gahyeonbot.entity.ExternalIdentity.builder()
                .id(java.util.UUID.randomUUID().toString())
                .principal(principals.getReferenceById(77L))
                .provider(IdentityProvider.ZEZESTUDIO)
                .externalId("platform-user")
                .build());
        assertThatThrownBy(() -> service.complete(code, "platform-user", timestamp,
                sign(ZezeStudioLinkService.canonical(code, "platform-user", timestamp))))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("이미 다른");
    }

    private static String queryCode(String url) {
        return java.net.URI.create(url).getRawQuery().substring("code=".length());
    }

    private static String sign(String value) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(SECRET.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            return HexFormat.of().formatHex(mac.doFinal(value.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception error) {
            throw new AssertionError(error);
        }
    }
}

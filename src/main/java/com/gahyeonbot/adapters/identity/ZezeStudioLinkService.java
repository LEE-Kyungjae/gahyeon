package com.gahyeonbot.adapters.identity;

import com.gahyeonbot.core.identity.ActorId;
import com.gahyeonbot.core.identity.IdentityProvider;
import com.gahyeonbot.entity.ExternalIdentity;
import com.gahyeonbot.entity.IdentityLinkToken;
import com.gahyeonbot.repository.ExternalIdentityRepository;
import com.gahyeonbot.repository.IdentityLinkTokenRepository;
import com.gahyeonbot.repository.PrincipalRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.util.UriComponentsBuilder;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.Base64;
import java.util.HexFormat;
import java.util.UUID;

@Service
public class ZezeStudioLinkService {
    private static final SecureRandom RANDOM = new SecureRandom();
    private static final int CODE_BYTES = 24;
    private static final int EXPIRY_MINUTES = 10;

    private final PrincipalRepository principals;
    private final ExternalIdentityRepository externalIdentities;
    private final IdentityLinkTokenRepository tokens;
    private final ZezeStudioLinkProperties properties;
    private final Clock clock;

    @Autowired
    public ZezeStudioLinkService(PrincipalRepository principals,
                                 ExternalIdentityRepository externalIdentities,
                                 IdentityLinkTokenRepository tokens,
                                 ZezeStudioLinkProperties properties) {
        this(principals, externalIdentities, tokens, properties, Clock.systemUTC());
    }

    ZezeStudioLinkService(PrincipalRepository principals,
                          ExternalIdentityRepository externalIdentities,
                          IdentityLinkTokenRepository tokens,
                          ZezeStudioLinkProperties properties,
                          Clock clock) {
        this.principals = principals;
        this.externalIdentities = externalIdentities;
        this.tokens = tokens;
        this.properties = properties;
        this.clock = clock;
    }

    @Transactional
    public IssuedLink issue(ActorId actorId) {
        requireEnabled();
        var principal = principals.findById(actorId.value())
                .orElseThrow(() -> new IllegalArgumentException("연결할 Gahyeon 계정이 없습니다."));
        byte[] entropy = new byte[CODE_BYTES];
        RANDOM.nextBytes(entropy);
        String code = Base64.getUrlEncoder().withoutPadding().encodeToString(entropy);
        LocalDateTime now = LocalDateTime.ofInstant(clock.instant(), ZoneOffset.UTC);
        LocalDateTime expiresAt = now.plusMinutes(EXPIRY_MINUTES);
        tokens.save(IdentityLinkToken.builder()
                .tokenHash(hash(code))
                .principal(principal)
                .targetProvider(IdentityProvider.ZEZESTUDIO)
                .createdAt(now)
                .expiresAt(expiresAt)
                .build());
        String url = UriComponentsBuilder.fromUriString(properties.getAuthorizeUrl())
                .queryParam("code", code)
                .build().encode().toUriString();
        return new IssuedLink(url, expiresAt);
    }

    @Transactional
    public void complete(String code, String platformUserId, long timestamp, String signature) {
        requireEnabled();
        validateInput(code, platformUserId, timestamp, signature);
        verifySignature(code, platformUserId, timestamp, signature);

        var token = tokens.findForConsume(hash(code.trim())).orElseThrow(ZezeStudioLinkService::invalid);
        LocalDateTime now = LocalDateTime.ofInstant(clock.instant(), ZoneOffset.UTC);
        if (token.getConsumedAt() != null || !token.getExpiresAt().isAfter(now)
                || token.getTargetProvider() != IdentityProvider.ZEZESTUDIO) {
            throw invalid();
        }

        var existing = externalIdentities.findByProviderAndExternalId(
                IdentityProvider.ZEZESTUDIO, platformUserId.trim());
        if (existing.isPresent()
                && !existing.get().getPrincipal().getId().equals(token.getPrincipal().getId())) {
            throw new IllegalStateException("이 ZezeStudio 계정은 이미 다른 Gahyeon 계정에 연결되어 있습니다.");
        }
        if (existing.isEmpty()) {
            externalIdentities.save(ExternalIdentity.builder()
                    .id(UUID.randomUUID().toString())
                    .principal(token.getPrincipal())
                    .provider(IdentityProvider.ZEZESTUDIO)
                    .externalId(platformUserId.trim())
                    .build());
        }
        token.setConsumedAt(now);
        tokens.save(token);
    }

    private void validateInput(String code, String platformUserId, long timestamp, String signature) {
        if (code == null || code.isBlank() || code.length() > 128
                || platformUserId == null || platformUserId.isBlank() || platformUserId.length() > 200
                || signature == null || signature.length() != 64 || timestamp <= 0) {
            throw invalid();
        }
        long age = Math.abs(clock.instant().getEpochSecond() - timestamp);
        if (age > Math.max(1, properties.getSignatureMaxAgeSeconds())) throw invalid();
    }

    private void verifySignature(String code, String platformUserId, long timestamp, String signature) {
        byte[] expected = hmac(canonical(code.trim(), platformUserId.trim(), timestamp));
        byte[] actual;
        try {
            actual = HexFormat.of().parseHex(signature);
        } catch (IllegalArgumentException error) {
            throw invalid();
        }
        if (!MessageDigest.isEqual(expected, actual)) throw invalid();
    }

    private byte[] hmac(String value) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(properties.getSharedSecret().getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            return mac.doFinal(value.getBytes(StandardCharsets.UTF_8));
        } catch (Exception error) {
            throw new IllegalStateException("ZezeStudio 연결 서명을 검증할 수 없습니다.", error);
        }
    }

    static String canonical(String code, String platformUserId, long timestamp) {
        return timestamp + "\n" + code + "\n" + platformUserId;
    }

    private void requireEnabled() {
        if (!properties.enabled()) throw new IllegalStateException("ZezeStudio 계정 연결이 설정되지 않았습니다.");
    }

    private static IllegalArgumentException invalid() {
        return new IllegalArgumentException("연결 요청이 잘못되었거나 만료되었습니다.");
    }

    private static String hash(String value) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException(impossible);
        }
    }

    public record IssuedLink(String url, LocalDateTime expiresAt) {}
}

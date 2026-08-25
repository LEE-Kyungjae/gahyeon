package com.gahyeonbot.adapters.identity;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "gahyeon.identity-link.zezestudio")
public class ZezeStudioLinkProperties {
    private String authorizeUrl = "http://localhost:3000/connect/gahyeon";
    private String sharedSecret = "";
    private long signatureMaxAgeSeconds = 120;

    public String getAuthorizeUrl() { return authorizeUrl; }
    public void setAuthorizeUrl(String authorizeUrl) { this.authorizeUrl = authorizeUrl; }
    public String getSharedSecret() { return sharedSecret; }
    public void setSharedSecret(String sharedSecret) { this.sharedSecret = sharedSecret; }
    public long getSignatureMaxAgeSeconds() { return signatureMaxAgeSeconds; }
    public void setSignatureMaxAgeSeconds(long signatureMaxAgeSeconds) {
        this.signatureMaxAgeSeconds = signatureMaxAgeSeconds;
    }

    public boolean enabled() {
        return sharedSecret != null && sharedSecret.length() >= 32
                && authorizeUrl != null && !authorizeUrl.isBlank();
    }
}

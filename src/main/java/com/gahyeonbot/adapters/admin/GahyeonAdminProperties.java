package com.gahyeonbot.adapters.admin;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "gahyeon.admin")
public class GahyeonAdminProperties {
    private boolean enabled;
    private String token = "";
    public boolean isEnabled() { return enabled; }
    public void setEnabled(boolean enabled) { this.enabled = enabled; }
    public String getToken() { return token; }
    public void setToken(String token) { this.token = token; }
    public boolean ready() { return enabled && token != null && token.length() >= 32; }
}

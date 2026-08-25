package com.gahyeonbot.adapters.admin;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

@Component
public class GahyeonAdminAuthorization {
    public static final String TOKEN_HEADER = "X-Gahyeon-Admin-Token";
    private final GahyeonAdminProperties properties;
    public GahyeonAdminAuthorization(GahyeonAdminProperties properties) { this.properties = properties; }

    public void require(HttpServletRequest request) {
        if (!properties.ready()) throw new ResponseStatusException(HttpStatus.NOT_FOUND);
        String supplied = request.getHeader(TOKEN_HEADER);
        if (supplied == null || !MessageDigest.isEqual(properties.getToken().getBytes(StandardCharsets.UTF_8),
                supplied.getBytes(StandardCharsets.UTF_8))) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "admin token required");
        }
    }
}

package com.gahyeonbot.adapters.admin;

import jakarta.servlet.http.HttpServletRequest;
import org.junit.jupiter.api.Test;
import org.springframework.web.server.ResponseStatusException;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

class GahyeonAdminAuthorizationTest {
    @Test
    void adminSurfaceFailsClosedUntilEnabledWithAStrongToken() {
        var properties = new GahyeonAdminProperties();
        var request = mock(HttpServletRequest.class);

        assertThatThrownBy(() -> new GahyeonAdminAuthorization(properties).require(request))
                .isInstanceOf(ResponseStatusException.class)
                .extracting(error -> ((ResponseStatusException) error).getStatusCode().value())
                .isEqualTo(404);
    }

    @Test
    void requiresExactConstantTimeComparedHeaderToken() {
        var properties = new GahyeonAdminProperties();
        properties.setEnabled(true);
        properties.setToken("0123456789abcdef0123456789abcdef");
        var authorization = new GahyeonAdminAuthorization(properties);
        var request = mock(HttpServletRequest.class);
        when(request.getHeader(GahyeonAdminAuthorization.TOKEN_HEADER)).thenReturn("wrong");

        assertThatThrownBy(() -> authorization.require(request))
                .isInstanceOf(ResponseStatusException.class)
                .extracting(error -> ((ResponseStatusException) error).getStatusCode().value())
                .isEqualTo(401);

        when(request.getHeader(GahyeonAdminAuthorization.TOKEN_HEADER))
                .thenReturn("0123456789abcdef0123456789abcdef");
        assertThatCode(() -> authorization.require(request)).doesNotThrowAnyException();
    }
}

package com.gahyeonbot.adapters.identity;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/internal/gahyeon/identity/zezestudio")
public class ZezeStudioIdentityLinkController {
    private final ZezeStudioLinkService links;

    public ZezeStudioIdentityLinkController(ZezeStudioLinkService links) {
        this.links = links;
    }

    @PostMapping("/complete")
    public ResponseEntity<Void> complete(
            @Valid @RequestBody CompleteRequest request,
            @RequestHeader("X-ZezeStudio-Timestamp") long timestamp,
            @RequestHeader("X-ZezeStudio-Signature") String signature) {
        try {
            links.complete(request.code(), request.platformUserId(), timestamp, signature);
            return ResponseEntity.noContent().build();
        } catch (IllegalArgumentException error) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, error.getMessage());
        } catch (IllegalStateException error) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, error.getMessage());
        }
    }

    public record CompleteRequest(
            @NotBlank @Size(max = 128) String code,
            @NotBlank @Size(max = 200) String platformUserId) {}
}

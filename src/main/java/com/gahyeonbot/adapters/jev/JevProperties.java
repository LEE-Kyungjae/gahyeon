package com.gahyeonbot.adapters.jev;

import jakarta.validation.constraints.*;
import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

@Getter @Setter @Validated
@ConfigurationProperties("gahyeon.jev")
public class JevProperties {
    private boolean enabled;
    private String apiKey = "";
    @Pattern(regexp = "jev-[0-9]+\\.[0-9]+\\.[0-9]+")
    private String model = "jev-1.13.0";
    private boolean expressionEnabled = true;
    private boolean memoryEnabled = true;
    @Min(100) @Max(1500)
    private int expressionTimeoutMillis = 450;
    @Min(100) @Max(1500)
    private int memoryTimeoutMillis = 800;
}

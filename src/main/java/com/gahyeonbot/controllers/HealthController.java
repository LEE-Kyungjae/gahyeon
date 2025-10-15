package com.gahyeonbot.controllers;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 헬스체크 및 기본 API 엔드포인트
 */
@RestController
public class HealthController {

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "UP");
    }

    @GetMapping("/")
    public Map<String, String> root() {
        return Map.of("service", "gahyeonbot", "status", "running");
    }
}

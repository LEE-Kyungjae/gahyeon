package com.gahyeonbot.services.ai.agent;

import java.util.*;
import java.util.regex.Pattern;

/** Conservative guard for explicit lookup requests; not a general intent classifier. */
final class AgentLookupEvidence {
    private static final Pattern NEWS = Pattern.compile("(?s).*(?:오늘|최신|최근|추천|읽을|읽으면).*(?:뉴스|기사).*|.*(?:뉴스|기사).*(?:오늘|최신|최근|추천|찾아|찾아줘|알려|조회).*");
    private final String intent;
    private final AgentTaskEvidencePolicy.Requirement requirement;
    private final Set<String> allowed = new LinkedHashSet<>();
    private final List<AgentTaskEvidencePolicy.ToolEvidence> evidence = new ArrayList<>();
    private int corrections;

    AgentLookupEvidence(String request) {
        String text = request.toLowerCase(Locale.ROOT);
        boolean excluded = text.contains("하지 마") || text.contains("하지마") || text.contains("말고")
                || text.contains("번역") || text.contains("예문") || text.contains("작성") || text.contains("써줘");
        if (!excluded && NEWS.matcher(text).matches()) {
            intent = "news"; requirement = new AgentTaskEvidencePolicy.Requirement(Set.of("get_recent_personalized_news", "research_verify"));
        } else if (!excluded && text.contains("서버") && (text.contains("살펴") || text.contains("점검해") || text.contains("상태 확인"))) {
            intent = "server"; requirement = new AgentTaskEvidencePolicy.Requirement(Set.of("get_server_health"));
        } else if (!excluded && (text.contains("시세") || (text.contains("구리") && text.contains("가격")) || text.contains("copper price"))) {
            intent = "market"; requirement = new AgentTaskEvidencePolicy.Requirement(Set.of("get_market_quote", "research_verify"));
        } else {
            intent = "none"; requirement = new AgentTaskEvidencePolicy.Requirement(Set.of());
        }
    }
    boolean required() { return !requirement.acceptedTools().isEmpty(); }
    String intent() { return intent; }
    void allow(String name) { allowed.add(name); }
    void completed(String name, String result) {
        if (!requirement.acceptedTools().contains(name)) return;
        if (result != null && result.startsWith("\"")) {
            try {
                result = new com.fasterxml.jackson.databind.ObjectMapper().readValue(result, String.class);
            } catch (com.fasterxml.jackson.core.JsonProcessingException invalid) {
                result = null;
            }
        }
        AgentTaskEvidencePolicy.ToolOutcome outcome;
        if (result == null || result.isBlank() || result.startsWith("knowledge_unavailable:")) {
            outcome = AgentTaskEvidencePolicy.ToolOutcome.FAILED;
        } else if (result.startsWith("knowledge_empty:")) {
            outcome = AgentTaskEvidencePolicy.ToolOutcome.EMPTY;
        } else if (name.equals("research_verify") && validResearchEvidence(result)) {
            outcome = AgentTaskEvidencePolicy.ToolOutcome.EVIDENCE;
        } else if (name.equals("get_recent_personalized_news")
                && result.startsWith("source: internal verified personalized_news\n")
                && result.contains("\n  published_at:") && result.contains("\n  source:")
                && result.matches("(?s).*https?://\\S+.*")) {
            outcome = AgentTaskEvidencePolicy.ToolOutcome.EVIDENCE;
        } else {
            outcome = AgentTaskEvidencePolicy.ToolOutcome.FAILED;
        }
        evidence.add(new AgentTaskEvidencePolicy.ToolEvidence(name, outcome));
    }
    private static boolean validResearchEvidence(String result) {
        try {
            var data = new com.fasterxml.jackson.databind.ObjectMapper().readTree(result);
            return data.path("status").asText().equals("citations_checked")
                    && data.path("citations").isArray() && !data.path("citations").isEmpty();
        } catch (com.fasterxml.jackson.core.JsonProcessingException invalid) { return false; }
    }
    AgentTaskEvidencePolicy.Assessment assess(int remaining) {
        return new AgentTaskEvidencePolicy().assess(requirement, allowed, evidence, corrections, remaining);
    }
    String correction() {
        corrections++;
        return "[조회 근거 확인] 현재 허용된 " + requirement.acceptedTools()
                + " 도구로 먼저 조회해. 결과의 발행 시각과 실제 원문 링크로 답하고, 자료가 없으면 없다고 밝혀.";
    }
    String fallback(AgentTaskEvidencePolicy.Outcome outcome) {
        if (intent.equals("market") && outcome != AgentTaskEvidencePolicy.Outcome.BLOCKED_CAPABILITY)
            return "시세 자료를 충분히 검증하지 못했어. 최신 가격과 기준일은 확인하지 못했어.";
        return switch (outcome) {
            case BLOCKED_CAPABILITY -> switch (intent) {
                case "server" -> "현재 서버 상태를 점검할 도구가 연결돼 있지 않아. 실제 상태는 확인하지 못했어.";
                case "market" -> "현재 시세를 조회할 도구가 연결돼 있지 않아. 실시간 가격은 확인하지 못했어.";
                default -> "현재 뉴스를 조회할 도구가 연결돼 있지 않아. 최신 기사는 확인하지 못했어.";
            };
            case NO_DATA -> "현재 조회 범위에서 검증된 뉴스가 나오지 않았어.";
            default -> "뉴스 조회를 완료하지 못했어. 최신 기사 내용을 확인하지 못했어.";
        };
    }
}

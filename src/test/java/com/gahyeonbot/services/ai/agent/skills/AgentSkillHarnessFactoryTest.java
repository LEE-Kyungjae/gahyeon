package com.gahyeonbot.services.ai.agent.skills;

import com.gahyeonbot.core.identity.ActorId;
import com.gahyeonbot.core.tool.ToolPolicy;
import com.gahyeonbot.services.ai.agent.AgentModality;
import com.gahyeonbot.services.ai.agent.AgentRequest;
import org.junit.jupiter.api.Test;
import org.springframework.ai.tool.ToolCallback;

import java.util.List;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

class AgentSkillHarnessFactoryTest {
    @Test void disabledHarnessDoesNotReadJournalOrDiscoverRemoteTools() {
        var journal = mock(AgentSkillJournal.class);
        var remote = mock(ApprovedMcpTools.class);
        var factory = new AgentSkillHarnessFactory(new AgentSkillCatalog(), journal, List.of(remote), false);
        assertThat(factory.open("run", request(), new ToolCallback[0], new ToolPolicy())).isNull();
        verifyNoInteractions(journal, remote);
    }

    @Test void configuredNativeToolsCanExecuteReleasedSkillThroughHarness() {
        var journal = new AgentSkillHarnessTest.Journal();
        var factory = new AgentSkillHarnessFactory(new AgentSkillCatalog(), journal, List.of(), true);
        var weather = mock(com.gahyeonbot.services.weather.WeatherService.class);
        when(weather.buildForecastMessage(any(), any(), any())).thenReturn("서울 예보: 흐림, 18~22°C");
        var nativeTools = org.springframework.ai.tool.method.MethodToolCallbackProvider.builder()
                .toolObjects(new com.gahyeonbot.services.ai.WeatherTools(weather)).build().getToolCallbacks();
        var harness = factory.open("run", request(), nativeTools, new ToolPolicy());
        harness.select("outing-weather", "1.0.0");
        harness.beforeCall("get_weather_forecast");
        var tool = java.util.Arrays.stream(harness.callbacks())
                .filter(c -> c.getToolDefinition().name().equals("get_weather_forecast")).findFirst().orElseThrow();
        String day = java.time.LocalDate.now(java.time.ZoneId.of("Asia/Seoul")).toString();
        harness.completed("get_weather_forecast", tool.call(
                "{\"cityCode\":\"SEOUL\",\"startDate\":\"" + day + "\",\"endDate\":\"" + day + "\"}"));
        harness.verifyCompletion();
        verify(weather).buildForecastMessage(any(), any(), any());
        assertThat(journal.read("run")).extracting(AgentSkillJournal.Entry::kind).endsWith("verified");
    }

    @Test void noDataForecastDoesNotMeetCompletionGate() {
        var factory = new AgentSkillHarnessFactory(new AgentSkillCatalog(), new AgentSkillHarnessTest.Journal(), List.of(), true);
        var harness = factory.open("run", request(), new ToolCallback[]{
                AgentSkillHarnessTest.callback("get_supported_weather_locations"),
                AgentSkillHarnessTest.callback("get_weather_forecast")}, new ToolPolicy());
        harness.select("outing-weather", "1.0.0");
        assertThatThrownBy(() -> harness.completed("get_weather_forecast", "result"))
                .hasMessageContaining("active attempt");
        harness.beforeCall("get_weather_forecast");
        assertThatThrownBy(() -> harness.completed("get_weather_forecast", "서울 예보 데이터를 찾지 못했어."))
                .hasMessageContaining("unavailable");
        assertThatThrownBy(harness::verifyCompletion).hasMessageContaining("evidence missing");
    }

    private static AgentRequest request() {
        return new AgentRequest("request", "session", AgentModality.TEXT, 7L,
                new ActorId(42), "fixture", "외출 준비", 8);
    }
}

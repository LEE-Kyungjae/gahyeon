package com.gahyeonbot.adapters.discord.voice;

import com.gahyeonbot.adapters.jev.JevExpressionModel;
import com.gahyeonbot.core.speech.VoiceExpression;
import org.junit.jupiter.api.Test;
import java.util.Optional;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class VoiceAssistantJevExpressionTest {
    @Test void usesSemanticDecisionAndRetainsLocalFallback() {
        var model = mock(JevExpressionModel.class);
        var policy = new VoiceAssistantExpressionPolicy();
        policy.configureSemanticModel(model);
        when(model.plan(any())).thenReturn(Optional.of(new VoiceExpression("gentle", .35, "acknowledge_distress")));
        assertThat(policy.plan("ㅋㅋ 오늘 잘렸어").style()).isEqualTo("gentle");
        when(model.plan(any())).thenReturn(Optional.empty());
        assertThat(policy.plan("고마워").style()).isEqualTo("warm");
        assertThat(policy.plan(null)).isEqualTo(VoiceExpression.NATURAL);
        verify(model, times(2)).plan(any());
    }
}

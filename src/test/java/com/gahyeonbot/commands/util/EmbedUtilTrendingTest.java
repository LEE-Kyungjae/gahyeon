package com.gahyeonbot.commands.util;

import com.gahyeonbot.entity.GitHubTrending;
import net.dv8tion.jda.api.entities.MessageEmbed;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class EmbedUtilTrendingTest {

    @Test
    void keepsCompleteRepositoryDescriptionsWithinDiscordBudget() {
        String description = "WiFi 신호를 분석해 카메라 없이 사람의 위치와 움직임을 감지하는 오픈소스 시스템입니다. "
                + "ESP32와 AI 모델을 결합해 벽 너머의 존재 여부뿐 아니라 호흡과 심박 같은 생체 신호도 추정합니다. "
                + "사생활을 보호하면서 공간 모니터링이 필요한 스마트홈과 안전 관리 분야에 활용할 수 있습니다.";
        List<GitHubTrending> repos = new ArrayList<>();
        for (int i = 0; i < 10; i++) {
            repos.add(GitHubTrending.builder()
                    .repoFullName("example/complete-repository-" + i)
                    .repoUrl("https://github.com/example/complete-repository-" + i)
                    .description(description)
                    .starsTotal(10_000 + i)
                    .language("TypeScript")
                    .build());
        }

        MessageEmbed embed = EmbedUtil.createGitHubTrendingEmbed(
                "오늘의 GitHub 트렌딩 다이제스트 (2026-07-29, 10개)", repos).build();

        assertThat(embed.getFields()).hasSize(10);
        assertThat(embed.getLength()).isLessThanOrEqualTo(5_500);
        assertThat(embed.getFields()).allSatisfy(field -> {
            assertThat(field.getValue()).doesNotContain("...");
            assertThat(field.getValue()).contains("활용할 수 있습니다.");
            assertThat(field.getValue().length()).isLessThanOrEqualTo(1_024);
        });
    }

    @Test
    void removesOnlyWholeTrailingSentencesWhenBudgetIsTight() {
        String result = EmbedUtil.completeSentences(
                "첫 번째 설명은 완결된 문장입니다. 두 번째 설명도 완결된 문장입니다. 세 번째 설명입니다.",
                45);

        assertThat(result).isEqualTo("첫 번째 설명은 완결된 문장입니다. 두 번째 설명도 완결된 문장입니다.");
        assertThat(result).doesNotEndWith("...");
    }
}

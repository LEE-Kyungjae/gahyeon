package com.gahyeonbot;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;

import static org.assertj.core.api.Assertions.*;

/**
 * 기본 테스트 - 테스트 인프라가 작동하는지 확인
 */
@DisplayName("Basic Infrastructure Tests")
class BasicTest {

    @Test
    @DisplayName("테스트 프레임워크 작동 확인")
    void testFrameworkWorks() {
        // Given
        String expected = "Hello, Test!";

        // When
        String actual = "Hello, Test!";

        // Then
        assertThat(actual).isEqualTo(expected);
    }

    @Test
    @DisplayName("AssertJ 라이브러리 작동 확인")
    void testAssertJ() {
        assertThat("test").isNotNull()
                          .isNotEmpty()
                          .hasSize(4)
                          .startsWith("te")
                          .endsWith("st");
    }

    @Test
    @DisplayName("숫자 계산 테스트")
    void testCalculation() {
        int result = 2 + 2;
        assertThat(result).isEqualTo(4);
    }
}

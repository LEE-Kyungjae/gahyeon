package com.gahyeonbot.entity;

import java.io.Serializable;
import java.util.Objects;

/** DmSubscription 복합키 (사용자 x 테마). */
public class DmSubscriptionId implements Serializable {

    private Long userId;
    private NewsletterTheme theme;

    public DmSubscriptionId() {
    }

    public DmSubscriptionId(Long userId, NewsletterTheme theme) {
        this.userId = userId;
        this.theme = theme;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (!(o instanceof DmSubscriptionId that)) {
            return false;
        }
        return Objects.equals(userId, that.userId) && theme == that.theme;
    }

    @Override
    public int hashCode() {
        return Objects.hash(userId, theme);
    }
}

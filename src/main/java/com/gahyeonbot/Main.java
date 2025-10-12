package com.gahyeonbot;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Discord 봇의 메인 스프링부트 애플리케이션 클래스.
 * 스프링부트 애플리케이션을 시작하고 Discord 봇을 초기화합니다.
 *
 * @author GahyeonBot Team
 * @version 1.0
 */
@SpringBootApplication
public class Main {
    public static void main(String[] args) {
        SpringApplication.run(Main.class, args);
    }
}
package com.gahyeonbot.commands.util;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * 명령어의 기본 구현을 제공하는 추상 클래스.
 * 모든 명령어 클래스가 공통으로 사용하는 기능을 제공합니다.
 * 
 * @author GahyeonBot Team
 * @version 1.0
 */
public abstract class AbstractCommand implements ICommand {
    /**
     * 로깅을 위한 Logger 인스턴스.
     */
    protected final Logger logger = LoggerFactory.getLogger(getClass());
}
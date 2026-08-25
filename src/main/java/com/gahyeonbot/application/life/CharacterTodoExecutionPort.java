package com.gahyeonbot.application.life;

public interface CharacterTodoExecutionPort {
    boolean isReady();
    void execute(CharacterAutonomyWorkspaceService.Todo todo);
}

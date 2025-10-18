package com.gahyeonbot.core.command;
import com.gahyeonbot.commands.util.ICommand;
import com.gahyeonbot.commands.general.Allhere;
import com.gahyeonbot.commands.general.Clean;
import com.gahyeonbot.commands.general.Gahyeona;
import com.gahyeonbot.commands.general.Info;
import com.gahyeonbot.commands.music.*;
import com.gahyeonbot.commands.moderation.*;
import com.gahyeonbot.core.audio.*;
import com.gahyeonbot.core.scheduler.LeaveSchedulerManager;
import com.gahyeonbot.services.ai.OpenAiService;
import com.gahyeonbot.services.music.MusicService;
import com.gahyeonbot.services.streaming.StreamingService;
import com.gahyeonbot.services.moderation.MessageCleanService;
import com.gahyeonbot.services.moderation.BotManagerService;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * 봇의 모든 명령어를 등록하고 관리하는 클래스.
 * 음악, 예약, 기타 명령어들을 생성하고 등록합니다.
 *
 * @author GahyeonBot Team
 * @version 1.0
 */
@Component
@RequiredArgsConstructor
public class CommandRegistry {
    private static final Logger logger = LoggerFactory.getLogger(CommandRegistry.class);

    private final AudioManager audioManager;
    private final LeaveSchedulerManager schedulerManager;
    private final Map<Long, GuildMusicManager> musicManagers;
    private final MusicService musicService;
    private final StreamingService streamingService;
    private final MessageCleanService messageCleanService;
    private final BotManagerService botManagerService;
    private final OpenAiService openAiService;

    /**
     * 모든 명령어를 등록하고 반환합니다.
     *
     * @return 등록된 명령어 목록
     */
    public List<ICommand> registerCommands() {
        List<ICommand> commands = new ArrayList<>();

        // 음악 명령어 등록
        commands.add(new Add(musicService, streamingService));
        commands.add(new Clear(musicManagers));
        commands.add(new Pause(musicManagers));
        commands.add(new Queue(musicManagers));
        commands.add(new Resume(musicManagers));

        // 예약 명령어 등록
        commands.add(new KickAllBots(botManagerService));
        commands.add(new CancelKick(schedulerManager));
        commands.add(new KickUser(schedulerManager));
        commands.add(new ListKicks(schedulerManager));
        commands.add(new KickAllUsers(schedulerManager));

        // 기타 명령어 등록
        commands.add(new Allhere());
        commands.add(new Clean(messageCleanService));
        commands.add(new Gahyeona(openAiService));
        commands.add(new Info(commands));

        // 로그 출력
        logger.info("총 {}개의 명령어가 등록되었습니다.", commands.size());
        commands.forEach(cmd -> logger.info("등록된 명령어: {}", cmd.getName()));
        return commands;
    }

}

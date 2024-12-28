package com.gahyeonbot.manager.command;
import com.gahyeonbot.commands.util.ICommand;
import com.gahyeonbot.commands.common.Allhere;
import com.gahyeonbot.commands.common.Clean;
import com.gahyeonbot.commands.common.Info;
import com.gahyeonbot.commands.music.*;
import com.gahyeonbot.commands.out.*;
import com.gahyeonbot.manager.music.*;
import com.gahyeonbot.manager.scheduler.LeaveSchedulerManager;
import com.gahyeonbot.service.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class CommandRegistrar {
    private static final Logger logger = LoggerFactory.getLogger(CommandRegistrar.class);

    private final AudioManager audioManager;
    private final LeaveSchedulerManager schedulerManager;
    private final Map<Long, GuildMusicManager> musicManagers;

    public CommandRegistrar(AudioManager audioManager, LeaveSchedulerManager schedulerManager, Map<Long, GuildMusicManager> musicManagers) {
        this.audioManager = audioManager;
        this.schedulerManager = schedulerManager;
        this.musicManagers = musicManagers;
    }

    public List<ICommand> registerCommands() {
        // 기본 스트리밍 소스를 설정 (YouTubeSource |SoundCloudSource 중 선택 )
        StreamingSource defaultSource = new SoundCloudSource();
        MusicManagerService musicManagerService = new MusicManagerService(musicManagers, audioManager);
        StreamingService streamingService = new StreamingService(new SpotifySearchService(), defaultSource);
        MessageCleanService messageCleanService = new MessageCleanService();
        BotManagerService botManagerService = new BotManagerService();

        List<ICommand> commands = new ArrayList<>();
        // 음악 명령어 등록
        commands.add(new Add(musicManagerService, streamingService)); // 수정된 부분
        commands.add(new Clear(musicManagers));
        commands.add(new Pause(musicManagers));
        commands.add(new Queue(musicManagers));
        commands.add(new Resume(musicManagers));

        // 예약 명령어 등록
        commands.add(new BotOut(botManagerService));
        commands.add(new CancelOut(schedulerManager));
        commands.add(new Out(schedulerManager));
        commands.add(new SearchOut(schedulerManager));
        commands.add(new WithOut(schedulerManager));

        // 기타 명령어 등록
        commands.add(new Allhere());
        commands.add(new Clean(messageCleanService));
        commands.add(new Info(commands));

        // 로그 출력
        logger.info("총 {}개의 명령어가 등록되었습니다.", commands.size());
        commands.forEach(cmd -> logger.info("등록된 명령어: {}", cmd.getName()));
        return commands;
    }

}

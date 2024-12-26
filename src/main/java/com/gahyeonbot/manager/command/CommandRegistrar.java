package com.gahyeonbot.manager.command;
import com.gahyeonbot.commands.ICommand;
import com.gahyeonbot.commands.common.Allhere;
import com.gahyeonbot.commands.common.Clean;
import com.gahyeonbot.commands.common.Info;
import com.gahyeonbot.commands.music.*;
import com.gahyeonbot.commands.out.*;
import com.gahyeonbot.manager.music.AudioManager;
import com.gahyeonbot.manager.music.GuildMusicManager;
import com.gahyeonbot.manager.scheduler.LeaveSchedulerManager;
import com.gahyeonbot.service.SpotifySearchService;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class CommandRegistrar {
    private final AudioManager audioManager;
    private final LeaveSchedulerManager schedulerManager;
    private final Map<Long, GuildMusicManager> musicManagers;

    public CommandRegistrar(AudioManager audioManager, LeaveSchedulerManager schedulerManager, Map<Long, GuildMusicManager> musicManagers) {
        this.audioManager = audioManager;
        this.schedulerManager = schedulerManager;
        this.musicManagers = musicManagers;
    }

    public List<ICommand> registerCommands() {
        List<ICommand> commands = new ArrayList<>();

        // 음악 명령어 등록
        commands.add(new Add(audioManager, musicManagers, new SpotifySearchService()));
        commands.add(new Clear(musicManagers));
        commands.add(new Pause(musicManagers));
        commands.add(new Queue(musicManagers));
        commands.add(new Resume(musicManagers));

        // 예약 명령어 등록
        commands.add(new BotOut());
        commands.add(new CancelOut(schedulerManager));
        commands.add(new Out(schedulerManager));
        commands.add(new SearchOut(schedulerManager));
        commands.add(new WithOut(schedulerManager));

        // 기타 명령어 등록
        commands.add(new Allhere());
        commands.add(new Clean());
        commands.add(new Info(commands));

        return commands;
    }

}

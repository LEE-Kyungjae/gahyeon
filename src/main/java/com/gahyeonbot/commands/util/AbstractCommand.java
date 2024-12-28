package com.gahyeonbot.commands.util;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public abstract class AbstractCommand implements ICommand {
    protected final Logger logger = LoggerFactory.getLogger(getClass());
}
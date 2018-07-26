from colorlog import ColoredFormatter, StreamHandler, getLogger
import logging


class Logger:

    def __init__(self, name, level=logging.DEBUG):
        style = "%(log_color)s[%(levelname)-8s][%(thread)d][%(asctime)s]" \
                "[%(name)s] %(message)s"

        formatter = ColoredFormatter(
            style,
            datefmt=None,
            reset=True,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'white',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            },
            secondary_log_colors={},
            style='%')

        handler = StreamHandler()
        handler.setFormatter(formatter)
        self.logger = getLogger(name)
        self.logger.addHandler(handler)
        self.set_level(level)

    def set_level(self, level):
        self.logger.setLevel(level)

    def debug(self, formatter, *args):
        self.logger.debug(formatter.format(*args))

    def info(self, formatter, *args):
        self.logger.info(formatter.format(*args))

    def warn(self, formatter, *args):
        self.logger.warn(formatter.format(*args))

    def error(self, formatter, *args):
        self.logger.error(formatter.format(*args))

    def critical(self, formatter, *args):
        self.logger.critical(formatter.format(*args))

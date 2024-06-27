import logging
import os
import resource
import sys


def get_log_level_from_str(log_level_str: str = "INFO") -> int:
    log_level_dict = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    }

    return log_level_dict.get(log_level_str.upper(), logging.INFO)


def setup_logger(
    name: str = __name__,
    log_level: int = get_log_level_from_str(),
    logfile_name: str | None = None,
) -> logging.LoggerAdapter:
    logger = logging.getLogger(name)

    # If the logger already has handlers, assume it was already configured and return it.
    if logger.handlers:
        return logger

    logger.setLevel(log_level)

    formatter = logging.Formatter(
        "%(asctime)s %(filename)20s%(lineno)4s : %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S %p",
    )

    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    if logfile_name:
        is_containerized = os.path.exists("/.dockerenv")
        file_name_template = (
            "/var/log/{name}.log" if is_containerized else "./log/{name}.log"
        )
        file_handler = logging.FileHandler(file_name_template.format(name=logfile_name))
        logger.addHandler(file_handler)

    return logger


def log_memory_usage(logger: logging.Logger):
    memory_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    logger.info(f"Memory Usage: {memory_usage} KB")

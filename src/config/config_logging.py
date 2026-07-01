import logging
from logging.handlers import TimedRotatingFileHandler
from src.config.paths import PATH_LOG

def setup_logging(
        year_fcst: int,
        month_fcst: int
) -> None:

    handler = TimedRotatingFileHandler(
        PATH_LOG / "realtime.log",   # arquivo base
        when="midnight",             # rotação diária à meia‑noite
        backupCount=30,              # mantém os últimos 30 dias de log
        encoding="utf-8"
    )

    handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    ))

    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(),
            handler
        ]
    )





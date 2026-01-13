# app/logger.py
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from config.config import settings

LOG_FORMAT = "%(asctime)s — %(name)s — %(levelname)s — %(message)s"
LOG_LEVEL = getattr(logging, settings.log_level.upper(), logging.INFO)
LOG_FILE = "app/log/app.log"

# Créer le dossier log s'il n'existe pas
Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

formatter = logging.Formatter(LOG_FORMAT)

# Handler pour fichier
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
file_handler.setFormatter(formatter)

# Handler pour console/terminal
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

logger = logging.getLogger(settings.app_name)
logger.setLevel(LOG_LEVEL)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

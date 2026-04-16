import logging
import sys
from app.core.context import correlation_id_ctx

class CorrelationIdFilter(logging.Filter):
    def filter(self, record):
        record.correlation_id = correlation_id_ctx.get() or "-"
        return True

def setup_logging(level: str = "INFO"):
    """Configura el logging de la aplicación"""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Eliminar handlers existentes para evitar duplicados
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Handler para consola (útil para Docker)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    root_logger.addHandler(console_handler)

    # Opcional: archivo rotativo (descomentar si se desea)
    # from logging.handlers import RotatingFileHandler
    # file_handler = RotatingFileHandler("app.log", maxBytes=10_485_760, backupCount=5)
    # file_handler.setFormatter(logging.Formatter(
    #     "%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s"
    # ))
    # root_logger.addHandler(file_handler)

    # Aplicar filtro de correlation ID a todos los handlers
    for handler in root_logger.handlers:
        handler.addFilter(CorrelationIdFilter())

    # Logger específico de la aplicación
    app_logger = logging.getLogger("app")
    app_logger.propagate = True
    return app_logger

# Logger por defecto (se configura después en main)
app_logger = logging.getLogger("app")
app_logger.addFilter(CorrelationIdFilter())

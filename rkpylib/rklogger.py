import logging 

class RKLogger:
    "Customised wrapper to logging.logger, provides class level methods to log under a single logger instance"
    logger = None
    extra = None
    DEBUG = logging.DEBUG
    ERROR = logging.ERROR
    
    @classmethod
    def initialize(cls, log_name, file_name, log_level, log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s', extra = None):
        cls.logger = logging.getLogger(log_name)
        cls.logger.setLevel(log_level)
        cls.extra = extra
        
        fh = logging.FileHandler(file_name)
        fh.setLevel(log_level)        
        #log_format = '%(asctime)-15s - %(name)s - %(clientip)s - %(user)-8s - %(levelname)-8s - %(message)s'
        formatter = logging.Formatter(log_format)
        fh.setFormatter(formatter)        
        cls.logger.addHandler(fh)

        if log_level == logging.DEBUG:		
            ch = logging.StreamHandler()
            ch.setLevel(log_level)
            ch.setFormatter(formatter)
            cls.logger.addHandler(ch)


    @classmethod
    def debug(cls, msg, *args, **kwargs):
        "Wrapper to logger.debug method, uses the default app created logger instance.  Skips if the logger instance is None"
        if cls.logger is not None:
            kwargs['extra'] = cls.extra
            cls.logger.debug(msg, *args, **kwargs)
        
    @classmethod
    def info(cls, msg, *args, **kwargs):
        "Wrapper to logger.info method, uses the default app created logger instance.  Skips if the logger instance is None"
        if cls.logger is not None:
            kwargs['extra'] = cls.extra
            cls.logger.info(msg, *args, **kwargs)
        
    @classmethod
    def warning(cls, msg, *args, **kwargs):
        "Wrapper to logger.warning method, uses the default app created logger instance.  Skips if the logger instance is None"
        if cls.logger is not None:
            kwargs['extra'] = cls.extra
            cls.logger.warning(msg, *args, **kwargs)

    @classmethod
    def error(cls, msg, *args, **kwargs):
        "Wrapper to logger.error method, uses the default app created logger instance.  Skips if the logger instance is None"
        if cls.logger is not None:
            kwargs['extra'] = cls.extra
            cls.logger.error(msg, *args, **kwargs)

    @classmethod
    def critical(cls, msg, *args, **kwargs):
        "Wrapper to logger.critical method, uses the default app created logger instance.  Skips if the logger instance is None"
        if cls.logger is not None:
            kwargs['extra'] = cls.extra
            cls.logger.critical(msg, *args, **kwargs)


    @classmethod
    def exception(cls, msg, *args, **kwargs):
        "Wrapper to logger.exception method, uses the default app created logger instance.  Skips if the logger instance is None"
        if cls.logger is not None:
            kwargs['extra'] = cls.extra
            cls.logger.exception(msg, *args, **kwargs)

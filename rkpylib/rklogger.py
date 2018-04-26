import logging 

class RKLogger:
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
        if cls.logger is not None:
            kwargs['extra'] = cls.extra
            cls.logger.debug(msg, *args, **kwargs)
        
    @classmethod
    def info(cls, msg, *args, **kwargs):
        if cls.logger is not None:
            cls.logger.info(msg, *args, **kwargs)
        
    @classmethod
    def warning(cls, msg, *args, **kwargs):
        if cls.logger is not None:
            cls.logger.warning(msg, *args, **kwargs)

    @classmethod
    def error(cls, msg, *args, **kwargs):
        if cls.logger is not None:
            cls.logger.error(msg, *args, **kwargs)

    @classmethod
    def critical(cls, msg, *args, **kwargs):
        if cls.logger is not None:
            cls.logger.critical(msg, *args, **kwargs)


    @classmethod
    def exception(cls, msg, *args, **kwargs):
        if cls.logger is not None:
            cls.logger.exception(msg, *args, **kwargs)

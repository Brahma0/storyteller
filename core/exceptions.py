class CyberPingshuException(Exception):
    """基础异常类。"""


class NetworkError(CyberPingshuException):
    """网络错误（可重试）。"""


class APIError(CyberPingshuException):
    """外部 API 调用错误（可重试）。"""


class ValidationError(CyberPingshuException):
    """数据验证错误（不可重试）。"""


class ResourceError(CyberPingshuException):
    """资源错误（显存/内存不足等）。"""


class UserCancelledError(CyberPingshuException):
    """用户主动取消任务。"""

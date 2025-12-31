"""缓存工具"""
import hashlib
import json
from typing import Optional, Any
import os
from functools import wraps


class SimpleCache:
    """简单的内存缓存"""
    
    def __init__(self, max_size: int = 100):
        self.cache = {}
        self.max_size = max_size
    
    def _make_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = {
            "args": args,
            "kwargs": kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        return self.cache.get(key)
    
    def set(self, key: str, value: Any):
        """设置缓存值"""
        if len(self.cache) >= self.max_size:
            # 简单的 FIFO 策略：删除第一个
            first_key = next(iter(self.cache))
            del self.cache[first_key]
        self.cache[key] = value
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()


# 全局缓存实例
_solution_cache = SimpleCache(max_size=100)
_narration_cache = SimpleCache(max_size=100)


def cached_solution(func):
    """解题结果缓存装饰器"""
    @wraps(func)
    def wrapper(problem_text: str, meta: dict = None):
        cache_key = hashlib.md5(
            json.dumps({"text": problem_text, "meta": meta or {}}, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        
        cached = _solution_cache.get(cache_key)
        if cached is not None:
            return cached
        
        result = func(problem_text, meta)
        _solution_cache.set(cache_key, result)
        return result
    
    return wrapper


def cached_narration(func):
    """讲解结果缓存装饰器"""
    @wraps(func)
    def wrapper(problem_text: str, solution_steps: list, meta: dict = None):
        cache_key = hashlib.md5(
            json.dumps({
                "text": problem_text,
                "steps": [s.dict() if hasattr(s, 'dict') else str(s) for s in solution_steps],
                "meta": meta or {}
            }, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        
        cached = _narration_cache.get(cache_key)
        if cached is not None:
            return cached
        
        result = func(problem_text, solution_steps, meta)
        _narration_cache.set(cache_key, result)
        return result
    
    return wrapper


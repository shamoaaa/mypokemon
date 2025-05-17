from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_openai import ChatOpenAI,OpenAIEmbeddings
import os
from typing import (
    TYPE_CHECKING,
    Literal,
    Optional,
    Callable,
    Generator,
    Dict,
    Any,
    Awaitable,
    Union,
    Tuple,
    List
)
from pathlib import Path
import logging
import asyncio
import httpx
import pydantic
from pydantic import BaseModel

# 加载模型配置信息
from configs import *


def get_prompt_template(type: str, name: str) -> Optional[str]:
    '''
    从prompt_config中加载模板内容
    type: "llm_chat","agent_chat","knowledge_base_chat","search_engine_chat"的其中一种，如果有新功能，应该进行加入。
    '''

    from configs import prompt_config
    import importlib
    importlib.reload(prompt_config)
    return prompt_config.PROMPT_TEMPLATES[type].get(name)

async def wrap_done(fn: Awaitable, event: asyncio.Event):
    """Wrap an awaitable with a event to signal when it's done or an exception is raised."""

    log_verbose = False

    try:
        await fn
    except Exception as e:
        logging.exception(e)
        msg = f"Caught exception: {e}"
        logger.error(f'{e.__class__.__name__}: {msg}',
                     exc_info=e if log_verbose else None)
    finally:
        # Signal the aiter to stop.
        event.set()
        
def get_ChatOpenAI(
        model_name: str,
        temperature: float = 1.0,
        max_tokens: int = None,
        streaming: bool = True,
        callbacks: List[Callable] = [],
        verbose: bool = True,
        **kwargs: Any,
) -> ChatOpenAI:
    if model_name == "deepseek-poke":
        model = ChatOpenAI(
            streaming=streaming,
            verbose=verbose,
            callbacks=callbacks,
            openai_api_key=MODEL_API_KEY,
            openai_api_base=OLLAMA_API_BASE,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    elif model_name in LLM_MODELS:
        model = ChatOpenAI(
            streaming=streaming,
            verbose=verbose,
            callbacks=callbacks,
            openai_api_key=MODEL_API_KEY,
            openai_api_base=MODEL_API_BASE,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    elif model_name == EMBEDDING_MODEL:
        model = OpenAIEmbeddings(
            model=model_name,
            openai_api_base=MODEL_API_BASE,
            openai_api_key=MODEL_API_KEY,
            chunk_size=32
        )  
    return model

def run_in_thread_pool(
        func: Callable,
        params: List[Dict] = [],
) -> Generator:
    '''
    在线程池中批量运行任务，并将运行结果以生成器的形式返回。
    请确保任务中的所有操作是线程安全的，任务函数请全部使用关键字参数。
    '''
    tasks = []
    with ThreadPoolExecutor() as pool:
        for kwargs in params:
            thread = pool.submit(func, **kwargs)
            tasks.append(thread)

        for obj in as_completed(tasks):
            yield obj.result()
            
class BaseResponse(BaseModel):
    code: int = pydantic.Field(200, description="API status code")
    msg: str = pydantic.Field("success", description="API status message")
    data: Any = pydantic.Field(None, description="API data")

    class Config:
        schema_extra = {
            "example": {
                "status": 200,
                "msg": "success",
            }
        }
def get_model_path(model_name: str, type: str = None) -> Optional[str]:
    if model_name == "bge-reranker-v2-m3":
        return "F:\\bigmodel\\models\\bge-reranker-v2-m3"
    

def embedding_device(device: str = None) -> Literal["cuda", "mps", "cpu"]:
    device = device or EMBEDDING_DEVICE
    if device not in ["cuda", "mps", "cpu"]:
        device = detect_device()
    return device


def detect_device() -> Literal["cuda", "mps", "cpu"]:
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
    except:
        pass
    return "cpu"

def torch_gc():
    try:
        import torch
        if torch.cuda.is_available():
            # with torch.cuda.device(DEVICE):
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
        elif torch.backends.mps.is_available():
            try:
                from torch.mps import empty_cache
                empty_cache()
            except Exception as e:
                msg = ("如果您使用的是 macOS 建议将 pytorch 版本升级至 2.0.0 或更高版本，"
                       "以支持及时清理 torch 产生的内存占用。")
                logger.error(f'{e.__class__.__name__}: {msg}',
                             exc_info=e if log_verbose else None)
    except Exception:
        ...
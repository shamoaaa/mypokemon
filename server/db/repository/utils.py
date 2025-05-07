from fastapi import Body
from configs import logger, log_verbose, LLM_MODELS
from server.utils import (BaseResponse)
from typing import List, Dict


def list_running_models(
        controller_address: str = Body(None, description="Fastchat controller服务器地址",
                                       ),
):
    '''
    从fastchat controller获取已加载模型列表
    '''
    try:
            models = LLM_MODELS
            return {"status": 200, "msg": "success", "data": {"models": models}}
            # return BaseResponse(data={"models": models})  # 直接返回模型列表
    except Exception as e:
        logger.error(f'{e.__class__.__name__}: {e}',
                     exc_info=e if log_verbose else None)
        return BaseResponse(
            code=500,
            data={},
            msg=f"Failed to get available models from controller: {controller_address}. Error: {e}")
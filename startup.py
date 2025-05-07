import sys
import os
import asyncio
from typing import List, Dict
from configs.basic_config import LOG_FORMAT, LOG_PATH
from configs.model_config import LLM_MODELS
from configs.server_config import (API_SERVER, DEFAULT_BIND_HOST)

# 构建多进程
import multiprocessing as mp
from multiprocessing import Process
import argparse
from fastapi import FastAPI




def run_api_server(run_mode: str = None):
    from server.api_router import create_app
    import uvicorn

    app = create_app()

    host = API_SERVER["host"]
    port = API_SERVER["port"]

    uvicorn.run(app, host=host, port=port)


if __name__ == '__main__':
    run_api_server()
from pydantic import BaseModel, Field
from langchain.prompts.chat import ChatMessagePromptTemplate
from configs import logger
from typing import List, Tuple, Dict, Union, Any
import aiohttp
import os
import hashlib
from configs import SERPER_API_KEY, URL
import html2text
import asyncio
import aiohttp
import re
from html2text import HTML2Text
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from server.memory.conversation_db_buffer_memory import ConversationBufferDBMemory
from server.db.repository.message_repository import filter_message
from langchain.schema import get_buffer_string, BaseMessage, HumanMessage, AIMessage
from langchain.chains import LLMChain

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompts import PromptTemplate


class History(BaseModel):
    """
    对话历史
    可从dict生成，如
    h = History(**{"role":"user","content":"你好"})
    也可转换为tuple，如
    h.to_msy_tuple = ("human", "你好")
    """
    role: str = Field(...)
    content: str = Field(...)

    def to_msg_tuple(self):
        return "ai" if self.role == "assistant" else "human", self.content

    def to_msg_template(self, is_raw=True) -> ChatMessagePromptTemplate:
        role_maps = {
            "ai": "assistant",
            "human": "user",
            "system": "system"  # 添加system角色的映射
        }
        role = role_maps.get(self.role, self.role)
        if is_raw:  # 当前默认历史消息都是没有input_variable的文本。
            content = "{% raw %}" + self.content + "{% endraw %}"
        else:
            content = self.content

        return ChatMessagePromptTemplate.from_template(
            content,
            "jinja2",
            role=role,
        )
        
        
async def search(query, num, locale=''):
    """
    定义一个异步函数，用于发起Serper API的实时 Google Search
    """
    # 初始化参数字典，包含搜索查询词和返回结果的数量
    params = {
        "q": query,  # 搜索查询词
        "num": num,  # 请求返回的结果数量
        "hl": "zh-cn"
    }

    # 如果提供了地区设置，则添加到参数字典中
    if locale:
        params["hl"] = locale  # 'hl'参数用于指定搜索结果的语言环境

    try:
        # 使用异步方式调用get_search_results函数，传入参数字典
        # 确保get_search_results是异步函数
        search_results = await get_search_results(params=params)
        return search_results  # 返回搜索结果
    except Exception as e:

        # 如果搜索过程中出现异常，打印错误信息并重新抛出异常
        print(f"search failed: {e}")
        raise e


async def get_search_results(params):
    try:
        # Serper API 的 URL
        url = URL
        # 从环境变量中获取 API 密钥
        params['api_key'] = SERPER_API_KEY

        # 使用 aiohttp 创建一个异步 HTTP 客户端会话
        async with aiohttp.ClientSession() as session:
            # 发送 GET 请求到 Serper API，并等待响应
            async with session.get(url, params=params) as response:
                # 解析 JSON 响应数据
                data = await response.json()
                # 提取有效的搜索结果
                items = data.get("organic", [])
                results = []
                for item in items:
                    # 为每个搜索结果生成 UUID（MD5 哈希）
                    item["uuid"] = hashlib.md5(item["link"].encode()).hexdigest()
                    # 初始化搜索结果的得分
                    item["score"] = 0.00
                    results.append(item)

        return results
    except Exception as e:
        # 记录错误信息
        print("get search results failed:", e)
        raise e


async def fetch_url(session, url):
    """
    这个函数在一个异步会话（session）的上下文中对每个 URL 发送 GET 请求，并尝试获取响应的 HTML 文本。
    """
    try:
        async with session.get(url, ssl=False) as response:  # 注意：在实际部署中应仔细考虑是否禁用 SSL
            response.raise_for_status()  # 检查响应状态码，如果不是 2xx，将抛出异常
            response.encoding = 'utf-8'  # 设置响应的编码，通常不需要手动设置，aiohttp 会自动处理
            html = await response.text()  # 等待响应体被完全读取
            return html
    except Exception as e:
        print(f"请求 URL 失败 {url}: {e}")
    return ""


async def html_to_markdown(html):
    try:
        converter = HTML2Text()
        converter.ignore_links = True
        converter.ignore_images = True
        markdown = converter.handle(html)
        return markdown
    except Exception as e:
        print(f"HTML 转换为 Markdown 失败: {e}")
        return ""


async def fetch_markdown(session, url):
    try:
        html = await fetch_url(session, url)
        markdown = await html_to_markdown(html)

        # 保留至少一个空行（即将两个及以上的换行符替换为两个换行符）
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)

        return url, markdown
    except Exception as e:
        print(f"获取 Markdown 失败 {url}: {e}")
        return url, ""


async def batch_fetch_urls(urls):
    try:
        # 设置超时时间，例如总超时10秒，连接超时2秒
        timeout = aiohttp.ClientTimeout(total=10, connect=1)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            tasks = [fetch_markdown(session, url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # 处理结果，忽略连接超时的请求
            final_results = []
            for result in results:
                if isinstance(result, asyncio.TimeoutError):
                    # 如果是超时错误，不做任何处理（可以在这里记录日志或增加计数器）
                    continue
                elif isinstance(result, Exception):
                    # TODO
                    pass
                else:
                    # 正常的响应结果
                    final_results.append(result)

            return final_results
    except Exception as e:
        print(f"批量获取 url 失败: {e}")
        return []


async def fetch_details(search_results):
    # 获取要提取详细信息的url
    urls = [document.metadata['link'] for document in search_results if 'link' in document.metadata]

    try:
        details = await batch_fetch_urls(urls)
    except Exception as e:
        # 如果批量获取失败，抛出异常
        raise e

    # details 填充为(url, content)元组列表
    content_maps = {url: content for url, content in details}

    # 直接在 search_results 上更新 page_content
    for document in search_results:
        # 使用属性访问方式获取链接信息
        link = document.metadata['link']  # 确保 Document 类定义了 metadata 属性且是一个字典
        if link in content_maps:
            # 直接更新 Document 对象的 page_content 属性
            document.page_content = content_maps[link]

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100)
    chunks = text_splitter.split_documents(search_results)
    return chunks
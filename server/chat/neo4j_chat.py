import os
import re
import asyncio
from fastapi import Body, Request
from sse_starlette.sse import EventSourceResponse
from server.utils import wrap_done, get_ChatOpenAI, get_model_path
from server.utils import BaseResponse, get_prompt_template
from typing import AsyncIterable
import json
from langchain.callbacks import AsyncIteratorCallbackHandler
from server.db.repository.message_repository import add_message_to_db
from server.memory.conversation_db_buffer_memory import ConversationBufferDBMemory
from server.callback_handler.conversation_callback_handler import ConversationCallbackHandler
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel
from configs.model_config import LLM_MODELS, TEMPERATURE, MAX_TOKENS, STREAM
from configs.server_config import NEO4J_SERVER
from langchain.chains import GraphCypherQAChain
from langchain_community.graphs import Neo4jGraph




async def neo4j_chat(query: str = Body(..., description="用户输入", examples=["你好"]),
               conversation_id: str = Body("", description="对话框ID"),
               model_name: str = Body(LLM_MODELS[0], description="LLM 模型名称。"),
               prompt_name: str = Body("neo4j_chat",
                                       description="使用的prompt模板名称(在configs/prompt_config.py中配置)")
               ):
    """
    :param query: 在对话框输入的问题
    :param user_id: 用户的id（经过登录校验的）
    :param conversation_id: 对话框的id
    :param model_name: 使用的大模型的名称
    :return:
    """
    async def chat_iterator() -> AsyncIterable[str]:
        
        graph = Neo4jGraph(url=NEO4J_SERVER["url"],  # 替换为自己的
                    username=NEO4J_SERVER["username"],  # 替换为自己的
                    password=NEO4J_SERVER["password"], #替换为自己的
                    database=NEO4J_SERVER["database"] # 替换为自己的
                    )
        
        cypher_model = get_ChatOpenAI(
                model_name=model_name,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
        cypher_chain = GraphCypherQAChain.from_llm(
            graph=graph,
            llm = cypher_model,
            validate_cypher=True, # Validate relationship directions
            verbose=True,
            allow_dangerous_requests=True,
        )
        cypher_chain.return_direct = True
        dic = cypher_chain.invoke(query)
        context = dic["result"]
        generated_cypher = dic["generated_cypher"]
        context = json.dumps(context, ensure_ascii=False, indent=2)
        # generated_cypher = json.dumps(generated_cypher, ensure_ascii=False, indent=2)
        print("context:",context)
        print("generated_cypher:",generated_cypher)
        
        callback = AsyncIteratorCallbackHandler()
        callbacks = [callback]
        memory = None

        # 构造一个新的Message_ID记录
        message_id = await add_message_to_db(query=query,
                                                conversation_id=conversation_id,
                                                prompt_name=prompt_name
                                                )

        conversation_callback = ConversationCallbackHandler(query=query,
                                                            conversation_id=conversation_id,
                                                            message_id=message_id,
                                                            chat_type=prompt_name,
                                                            )
        callbacks.append(conversation_callback)

        model = get_ChatOpenAI(
            model_name=model_name,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            callbacks=callbacks,
        )
    
        
        if conversation_id:
                # 使用memory 时必须 prompt 必须含有memory.memory_key 对应的变量
                prompt = get_prompt_template(prompt_name, "chat_with_history")
                chat_prompt = PromptTemplate.from_template(prompt)
                # 根据conversation_id 获取message 列表进而拼凑 memory
                memory = ConversationBufferDBMemory(conversation_id=conversation_id,
                                                    llm=cypher_model,
                                                    chat_type=prompt_name,
                                                    message_limit=10)
                
        
        chain = (
                RunnableParallel({
                    "input": lambda x: x["input"],  # 保留用户输入
                    "history": memory.load_memory_variables,  # 加载记忆
                    "context": RunnableLambda(lambda _: context) if isinstance(context, str) else context
                })
                | chat_prompt
                | model
            )
        task = asyncio.create_task(wrap_done(
                chain.ainvoke({"input": query}),
                callback.done),
            )

        if STREAM:
            async for token in callback.aiter():
                # Use server-sent-events to stream the response
                yield json.dumps(
                    {"text": token, "message_id": message_id},
                    ensure_ascii=False)
            yield json.dumps({"generated_cypher": generated_cypher, "message_id": message_id,}, ensure_ascii=False)
            yield json.dumps({"cypher_result": context, "message_id": message_id,}, ensure_ascii=False)
        else:
            answer = ""
            async for token in callback.aiter():
                answer += token
            yield json.dumps(
                {"text": answer, "message_id": message_id},
                ensure_ascii=False)

        await task

    return EventSourceResponse(chat_iterator())
    
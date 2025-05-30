from fastapi import Depends, HTTPException
from fastapi.responses import JSONResponse
from server.db.session import get_async_db, with_async_session, async_session_scope
from typing import Dict, List
import uuid
from server.db.models.message_model import MessageModel
from server.db.models.conversation_model import ConversationModel
from server.db.models.user_model import UserModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, Field

class UpdateMessageRequest(BaseModel):
    feedback_score: int = Field(..., description="反馈得分")
    feedback_reason: str = Field(..., description="反馈理由")
@with_async_session
async def add_message_to_db(session,
                            query: str,
                            conversation_id: str,
                            prompt_name: str,
                            response="",
                            metadata: Dict={},
                            message_id=None,
                            ):
    """
    新增聊天记录
    """

    # 获取会话ID
    conversation = await session.get(ConversationModel, conversation_id)

    # 更新会话ID的名称
    if conversation.name == "新对话":  # 如果会话存在且名称为'new_chat'，则更新名称为query
        conversation.name = query

    # 确保这里的更改被提交
    await session.commit()

    # 要判断是否存在会话的ID
    if not message_id:
        message_id = str(uuid.uuid4())

    # 创建MessageModel实例
    m = MessageModel(id=message_id,
                     conversation_id=conversation_id,
                     chat_type=prompt_name,
                     query=query,
                     response=response,
                     metadata=metadata
                     )

    # 添加到session，注意这里不用await
    session.add(m)

    # 异步提交
    await session.commit()
    return m.id


@with_async_session
async def filter_message(session, conversation_id: str, chat_type: str, limit: int = 10):
    """
    Asynchronously filter messages by conversation_id with a limit on the number of records
    """
    result = await session.execute(
        select(MessageModel)
        .filter_by(conversation_id=conversation_id, chat_type=chat_type)
        .filter(MessageModel.response != '')
        .order_by(MessageModel.create_time.desc())
        .limit(limit)
    )

    return result.scalars().all()


@with_async_session
async def get_message_by_id(session, message_id) -> MessageModel:
    """
    Asynchronously query a chat record by ID
    """
    result = await session.execute(select(MessageModel).filter_by(id=message_id))
    return result.scalars().first()


@with_async_session
async def update_message(session, message_id, response: str = None, metadata: Dict = None):
    # 由于 get_message_by_id 是一个异步函数，确保其调用是在装饰器内正确处理
    m = await get_message_by_id(message_id)

    if m is not None:
        if response is not None:
            m.response = response
        if isinstance(metadata, dict):
            m.meta_data = metadata
        session.add(m)
        # 确保 commit 是异步的
        await session.commit()
        return m.id
    else:
        # 使用适当的异常处理
        raise HTTPException(status_code=404, detail="Message not no found")


async def update_message_feedback(message_id: str,
                                  request:UpdateMessageRequest,
                                  session: AsyncSession = Depends(get_async_db)):
    # 由于 get_message_by_id 是一个异步函数，确保其调用是在装饰器内正确处理
    m = await get_message_by_id(message_id)

    if m is not None:
        m.feedback_score = request.feedback_score
        m.feedback_reason = request.feedback_reason
        session.add(m)
        # 确保 commit 是异步的
        await session.commit()
        return JSONResponse(status_code=200, content={"status": 200, "message": "Message updated successfully"})
    else:
        # 使用适当的异常处理
        raise HTTPException(status_code=404, detail="Message not no found")

# 主测试函数
async def main():
    # 测试是否可以查询
    test_conversation_id = 'edcrfv33'
    # 调用 filter_message 函数并打印结果
    messages = await filter_message(test_conversation_id, limit=4)
    messages = list(reversed(messages))

    message = await get_message_by_id(message_id="041c8958055a4a62827cb39a789e3603")
    print(messages)

    updated_id = await update_message(message_id="041c8958055a4a62827cb39a789e3603", response="这是最新曾德")
    print(updated_id)


# 这里检查是否是直接运行这个脚本
if __name__ == '__main__':
    import asyncio

    # 运行主测试函数
    asyncio.run(main())
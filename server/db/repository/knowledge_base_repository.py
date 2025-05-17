from sqlalchemy import delete
import urllib
from server.db.models.knowledge_base_model import KnowledgeBaseModel
from sqlalchemy.future import select
from server.db.session import with_async_session, async_session_scope
from fastapi import HTTPException, Depends, Body, Query
from server.db.session import get_async_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from configs import EMBEDDING_MODEL
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from server.db.models.knowledge_file_model import KnowledgeFileModel, FileDocModel
from server.utils import BaseResponse



class KnowledgeBaseOut(BaseModel):
    id: int
    kb_name: str
    kb_info: str | None
    vs_type: str
    embed_model: str
    file_count: int
    create_time: datetime | None


@with_async_session
async def add_kb_to_db(session, kb_name, kb_info, vs_type, embed_model, user_id):
    # 查询现有知识库实例
    kb = await session.execute(
        select(KnowledgeBaseModel)
        .where(KnowledgeBaseModel.kb_name.ilike(kb_name))
    )
    kb = kb.scalars().first()

    if not kb:
        # 创建新的知识库实例
        kb = KnowledgeBaseModel(kb_name=kb_name, kb_info=kb_info, vs_type=vs_type, embed_model=embed_model,
                                user_id=user_id)
        session.add(kb)
    else:
        # 更新现有知识库实例
        kb.kb_info = kb_info
        kb.vs_type = vs_type
        kb.embed_model = embed_model
        kb.user_id = user_id

    # 异步提交数据库事务
    await session.commit()
    return True


@with_async_session
async def list_kbs_from_db(session, min_file_count: int = -1):
    # 过滤条件，用于指定返回的知识库所包含的文件数量下限，默认值为 -1，意味着默认情况下会返回所有知识库的名称，不论其文件数量如何。
    result = await session.execute(
        select(KnowledgeBaseModel.kb_name)
        .where(KnowledgeBaseModel.file_count > min_file_count)
    )

    # 提取向量数据库的名称
    kbs = [kb[0] for kb in result.scalars().all()]
    return kbs


@with_async_session
async def kb_exists(session, kb_name):
    kb = session.query(KnowledgeBaseModel).filter(KnowledgeBaseModel.kb_name.ilike(kb_name)).first()
    status = True if kb else False
    return status


@with_async_session
async def load_kb_from_db(session, kb_name):
    stmt = select(KnowledgeBaseModel).filter(KnowledgeBaseModel.kb_name.ilike(kb_name))
    result = await session.execute(stmt)
    kb = result.scalar_one_or_none()
    print("kb:", kb)
    if kb:
        kb_name, vs_type, embed_model = kb.kb_name, kb.vs_type, kb.embed_model
    else:
        kb_name, vs_type, embed_model = None, None, None
    return kb_name, vs_type, embed_model


@with_async_session
async def delete_kb_from_db(session, kb_name):
    kb = session.query(KnowledgeBaseModel).filter(KnowledgeBaseModel.kb_name.ilike(kb_name)).first()
    if kb:
        session.delete(kb)
    return True


@with_async_session
async def get_kb_detail(session, kb_name: str) -> dict:
    stmt = select(KnowledgeBaseModel).where(KnowledgeBaseModel.kb_name.ilike(kb_name))
    result = await session.execute(stmt)
    kb = result.scalars().first()

    if kb:
        return {
            "kb_name": kb.kb_name,
            "kb_info": kb.kb_info,
            "vs_type": kb.vs_type,
            "embed_model": kb.embed_model,
            "file_count": kb.file_count,
            "create_time": kb.create_time,
        }
    else:
        return {}


async def list_knowledge_bases(
    user_id: str,
    session: AsyncSession = Depends(get_async_db)
):
    """
    异步从数据库检索特定用户的所有知识库信息，并返回给前端。
    """
    try:
        # 查询所有字段
        result = await session.execute(
            select(KnowledgeBaseModel).where(KnowledgeBaseModel.user_id == user_id)
        )
        kb_records = result.scalars().all()

        # 转换为字典格式
        kbs = [{
            "id": kb.id,
            "kb_name": kb.kb_name,
            "kb_info": kb.kb_info,
            "vs_type": kb.vs_type,
            "embed_model": kb.embed_model,
            "file_count": kb.file_count,
            "create_time": kb.create_time.isoformat() if kb.create_time else None
        } for kb in kb_records]

        # 添加通用知识库（例如 wiki）
        if not any(kb['kb_name'] == 'wiki' for kb in kbs):
            kbs.append({
                "id": 1,
                "kb_name": "wiki",
                "kb_info": "通用百科知识库",
                "vs_type": "milvus",
                "embed_model": "bge-m3-pro",
                "file_count": 1,
                "create_time": "2025-05-12 08:26:32"
            })

        return {"status": 200, "msg": "success", "data": {"knowledge_bases": kbs}}

    except SQLAlchemyError as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


class CreateKnowledgeBaseRequest(BaseModel):
    user_id: str
    knowledge_base_name: str
    knowledge_base_description: str = "描述信息（如果需要）"
    vector_store_type: str = "milvus"
    embed_model: str = EMBEDDING_MODEL


class DeleteKnowledgeBaseRequest(BaseModel):
    user_id: str
    knowledge_base_name: str

class KnowledgeBaseFilesRequest(BaseModel):
    user_id: str
    knowledge_base_name: str

async def create_knowledge_base(
        request: CreateKnowledgeBaseRequest,  # 使用 Pydantic 模型来接收请求数据
        session: AsyncSession = Depends(get_async_db)
):
    """
    异步创建新的知识库记录到 MySQL 数据库中。
    """
    user_id = request.user_id
    knowledge_base_name = request.knowledge_base_name
    knowledge_base_description = request.knowledge_base_description
    vector_store_type = request.vector_store_type
    embed_model = request.embed_model

    if knowledge_base_name.strip() == "":
        return JSONResponse(status_code=400, content={"msg": "知识库名称不能为空，请重新填写知识库名称"})

    existing_kb = await session.execute(
        select(KnowledgeBaseModel)
        .where(KnowledgeBaseModel.kb_name == knowledge_base_name, KnowledgeBaseModel.user_id == user_id)
    )
    if existing_kb.scalars().first() is not None:
        return JSONResponse(status_code=400, content={"msg": f"已存在同名知识库 {knowledge_base_name}"})

    new_kb = KnowledgeBaseModel(
        kb_name=knowledge_base_name,
        kb_info=knowledge_base_description,
        vs_type=vector_store_type,
        embed_model=embed_model,
        create_time=datetime.now(),
        user_id=user_id
    )

    try:
        session.add(new_kb)
        await session.commit()
        await session.refresh(new_kb)
        return JSONResponse(
            status_code=201,
            content={"id": new_kb.id, "msg": f"已新增知识库 {knowledge_base_name}"}
        )
    except SQLAlchemyError as e:
        await session.rollback()
        return JSONResponse(status_code=500, content={"msg": f"创建知识库出错： {e}"})


async def delete_knowledge_base(
        request: DeleteKnowledgeBaseRequest,
        session: AsyncSession = Depends(get_async_db)
):
    """
    异步从数据库中删除指定用户的知识库。
    """
    from server.knowledge_base.kb_service.base import KBServiceFactory
    user_id = request.user_id
    knowledge_base_name = request.knowledge_base_name

    print("kbname:=============",knowledge_base_name)
    # 查找并删除知识库
    try:
        
        knowledge_base_name = urllib.parse.unquote(knowledge_base_name)
        kb = await KBServiceFactory.get_service_by_name(knowledge_base_name)
        if kb is None:
            return BaseResponse(code=404, msg=f"未找到知识库 {knowledge_base_name}")
        
        
        kb_to_delete = await session.execute(
            select(KnowledgeBaseModel)
            .where(KnowledgeBaseModel.kb_name == knowledge_base_name,
                   KnowledgeBaseModel.user_id == user_id)
        )
        kb_to_delete = kb_to_delete.scalars().first()
        if kb_to_delete is None:
            return JSONResponse(status_code=404, content={"msg": f"未找到知识库 {knowledge_base_name}"})

         # 查找并删除所有关联的文件记录
        files_to_delete = await session.execute(
            select(KnowledgeFileModel)
            .where(KnowledgeFileModel.kb_name == knowledge_base_name)
        )
        files_to_delete = files_to_delete.scalars().all()

         # 删除所有关联的文档记录
        await session.execute(
            delete(FileDocModel)
            .where(FileDocModel.kb_name == knowledge_base_name)
        )

        # 删除所有关联的文件记录
        for file in files_to_delete:
            await session.delete(file)
            
        await session.delete(kb_to_delete)
        await session.commit()
        
        kb.drop_kb()
        
        return JSONResponse(
            status_code=200,
            content={"msg": f"成功删除知识库 {knowledge_base_name}"}
        )
    except SQLAlchemyError as e:
        await session.rollback()
        return JSONResponse(status_code=500, content={"msg": f"删除知识库时出现错误：{e}"})



async def list_knowledge_base_files(
    user_id: str = Query(None, description="用户ID"),  # 注意这里将默认值设为 None
    knowledge_base_name: str = Query(..., description="知识库名称"),
    session: AsyncSession = Depends(get_async_db)
):
    """
    异步从数据库中获取指定知识库的文件列表。
    返回：文件ID、文件名、扩展名、大小、切分文档数、创建时间
    """

    try:
        if knowledge_base_name == 'wiki':
            # 如果知识库名称是 wiki，则不需要校验 user_id
            kb_result = await session.execute(
                select(KnowledgeBaseModel)
                .where(KnowledgeBaseModel.kb_name == knowledge_base_name)
            )
        else:
            # 否则需要校验 user_id 和 knowledge_base_name
            if not user_id:
                raise HTTPException(status_code=422, detail=[{'msg': 'Field required', 'loc': ['query', 'user_id']}])
            kb_result = await session.execute(
                select(KnowledgeBaseModel)
                .where(KnowledgeBaseModel.kb_name == knowledge_base_name,
                       KnowledgeBaseModel.user_id == user_id)
            )

        kb = kb_result.scalars().first()
        if kb is None:
            return JSONResponse(
                status_code=404,
                content={"msg": f"未找到知识库 {knowledge_base_name}", "data": []}
            )

        # 查询该知识库下的所有文件
        stmt = (
            select(KnowledgeFileModel.id, KnowledgeFileModel.file_name, KnowledgeFileModel.file_ext,
                   KnowledgeFileModel.file_size, KnowledgeFileModel.docs_count, KnowledgeFileModel.create_time)
            .where(KnowledgeFileModel.kb_name == knowledge_base_name)  # 直接使用 knowledge_base_name 进行过滤
        )
        result = await session.execute(stmt)
        files = result.all()

        # 格式化为字典列表
        file_list = [
            {
                "id": file.id,
                "file_name": file.file_name,
                "file_ext": file.file_ext,
                "file_size": file.file_size,
                "docs_count": file.docs_count,
                "create_time": file.create_time.isoformat() if file.create_time else None
            }
            for file in files
        ]

        return JSONResponse(
            status_code=200,
            content={"data": file_list}
        )

    except Exception as e:
        await session.rollback()
        return JSONResponse(
            status_code=500,
            content={"msg": f"获取文件列表时出现错误：{e}", "data": []}
        )
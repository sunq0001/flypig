"""__init__

为什么做：统一导出所有领域抽象接口（ABC）

实现方法：集中 import + __all__，基础设施层实现这些接口

层&依赖：domain.interfaces 层
"""

from flypig.domain.interfaces.iagent import IAgent
from flypig.domain.interfaces.iast_parser import IASTParser
from flypig.domain.interfaces.icache import ICache
from flypig.domain.interfaces.icontext_pipeline import IContextPipeline
from flypig.domain.interfaces.iconversation_store import IConversationStore
from flypig.domain.interfaces.ievent_stream import IEventStream
from flypig.domain.interfaces.ihook import IHook
from flypig.domain.interfaces.iknowledge_graph import IKnowledgeGraph
from flypig.domain.interfaces.ilicense_service import ILicenseService
from flypig.domain.interfaces.ilocal_model_service import ILocalModelService
from flypig.domain.interfaces.ilsp_diagnostics import ILspDiagnostics
from flypig.domain.interfaces.imapper import IMapper
from flypig.domain.interfaces.imodel import IModel
from flypig.domain.interfaces.imodel_factory import IModelFactory
from flypig.domain.interfaces.imodel_policy import IModelPolicy
from flypig.domain.interfaces.iranker import IRanker
from flypig.domain.interfaces.isearch import ISearch
from flypig.domain.interfaces.itool_executor import IToolExecutor
from flypig.domain.interfaces.iupdate_service import IUpdateService
from flypig.domain.interfaces.iusage_tracker import IUsageTracker
from flypig.domain.interfaces.ivector_store import IVectorStore
from flypig.domain.interfaces.repository import Repository

__all__ = [
    "IASTParser",
    "IAgent",
    "ICache",
    "IContextPipeline",
    "IConversationStore",
    "IEventStream",
    "IHook",
    "IKnowledgeGraph",
    "ILicenseService",
    "ILocalModelService",
    "ILspDiagnostics",
    "IMapper",
    "IModel",
    "IModelFactory",
    "IModelPolicy",
    "IRanker",
    "ISearch",
    "IToolExecutor",
    "IUpdateService",
    "IUsageTracker",
    "IVectorStore",
    "Repository",
]

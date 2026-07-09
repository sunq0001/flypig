"""沙箱配置数据类

为什么做：Docker 沙箱的配置（镜像/资源限制/超时/网络）需要集中管理，不能散落各处。
实现方法：@dataclass 定义 SandboxConfig，含 Docker 配置 + 资源限制参数。
实现效果：改沙箱配置只需改实例化参数，不影响沙箱管理器的核心逻辑。
技术栈：@dataclass, Docker 配置 + 资源限制

层&依赖：infrastructure.sandbox 层，零依赖
细节见文档：docs/docs_refactor/subprocess.md → §沙箱策略
"""

# TODO: 骨架文件占位，待具体实现

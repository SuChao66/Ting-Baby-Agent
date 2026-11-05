# 汀家 Agent（ting-family-agent）

汀宝宝产品的 **AI 对话主入口**服务：家人在汀宝宝 App 现有对话界面中，通过自然语言完成查询宝宝数据、新增成长/护理记录、生成周报、日常问答、照片解读。

> 规划文档见汀宝宝仓库 `docs/汀家Agent项目计划_v1.1.md`；本仓库按该计划分里程碑实施。

## 架构一句话

Agent 编排层（Python）：**读**走 MongoDB 只读直连，**写**必经汀宝宝现有 REST API（JWT 透传）——Node 后端与前端代码零改动，业务校验/权限单点保留在汀宝宝。

## 技术栈

Python 3.13+（venv）· FastAPI · AgentScope 2.0（M1 核对后锁定）· Motor · httpx · Pydantic v2 · pyjwt

## 当前进度

- [x] **M1.0 工程初始化**：目录结构、venv、工程配置文件
- [ ] M1 FastAPI 骨架（统一响应/日志/JWT 校验/健康检查）
- [ ] M1 AgentScope 2.0 安装与官方 API 核对、汀宝宝 schema/API 提取
- [ ] M2 读数据层（Motor + 六类读工具）
- [ ] M3 写工具链路（httpx 调汀宝宝 REST API）
- [ ] M4 Agent 对话核心（ReAct + SSE 流式 + 会话记忆）
- [ ] M5 周报 + 多模态
- [ ] M6 测试 + Docker 上 VPS

## 本地启动（初始化阶段）

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # 待 M1 执行
cp .env.example .env              # 填写真实值
```

## 红线

1. 不改动汀宝宝 backend/frontend 任何现有代码
2. MongoDB 读 = 只读账号直连；写 = 必经汀宝宝 Node REST API
3. 会话记录写自有 collection，不动汀宝宝 `AIRecord`
4. 独立 docker-compose，不并入汀宝宝现有编排

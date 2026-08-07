"""ABA 与 Coach 共享平台层。

两个产品线（ABA 家庭训练 / 家长陪伴 Coach）共用的：
- 数据库基座（Base / engine / SessionLocal / get_db）
- 配置（Settings）
- 认证（security + auth router）
- 共享数据模型（User / RefreshToken / AuditLog / SystemEvent / AiUsage / ChatMessage / 专家系统）
- 共享服务（对象存储 / HTTP 客户端 / 速率限制）
- 安全分级（assess_risk / crisis_response）
"""

# 竞赛身份与凭证链

**读取条件**：AD、Kerberos、OAuth/OIDC、DPAPI、LSASS、邮箱、证书与身份攻击链案例。

本索引包含 9 个主归组模块。只在任务命中本领域时读取，不要为了比较分数读取其他领域索引。

## 选择规则

1. 先按用户目标和当前输入筛除不相关模块。
2. 候选能力接近时优先评分更高者；无评分不等于不可用。
3. 默认先读一个模块，明确存在能力缺口时再增加，每阶段最多 4 个。
4. 没有合适候选时返回 `../SKILL.md`，或使用模型自带知识规划并告知用户步骤、成本和交付路径。

## 模块索引（已评分项按分数降序）

- `competition-ad-certificate-abuse` 【6/10】 — CTF 沙箱子流：AD CS 证书模板/EKU/SAN/PKINIT 证书滥用与提权链
- `competition-dpapi-credential-chain` 【6/10】 — CTF 沙箱子流：DPAPI 主密钥/vault/浏览器凭据库到可重放秘密的链路
- `competition-identity-windows` 【6/10】 — CTF 沙箱子流：AD/Kerberos/LDAP 凭据材料与 Windows 主机横向移动链
- `competition-kerberos-delegation` 【6/10】 — CTF 沙箱子流：Kerberos 委派（约束/非约束/RBCD/S4U）与票据接受链
- `competition-linux-credential-pivot` 【6/10】 — CTF 沙箱子流：Linux 凭据工件、service token/SSH 材料与主机间横向链
- `competition-lsass-ticket-material` 【6/10】 — CTF 沙箱子流：LSASS 内存秘密、Kerberos 票据缓存与可重放凭据提取
- `competition-mailbox-abuse` 【6/10】 — CTF 沙箱子流：企业邮箱滥用、OAuth 授权、收件箱/转发规则与钓鱼链
- `competition-oauth-oidc-chain` 【6/10】 — CTF 沙箱子流：OAuth/OIDC 重定向、PKCE、token 交换到接受身份的全链
- `competition-relay-coercion-chain` 【6/10】 — CTF 沙箱子流：强制认证 coerce、NTLM relay 链与到提权的转换

选定后完整读取 `../../_modules/<MODULE_ID>/SKILL.md` 再执行。

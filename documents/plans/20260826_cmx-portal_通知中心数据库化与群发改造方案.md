# 通知中心数据库化与群发改造方案

> 归属:cmx-portal(门户通知中心)| 状态:**已实施**(2026-08-26,验证通过,待提交)
> 评审方式:/reviewplan 流程,两轮独立子智能体代码级审查,所有结论均落到工作区既有先例

---

## 一、背景与问题

通知中心现状(`cmx-portalservice/crates/cmx-portal/src/notify/`)存在三类问题:

1. **文件存储违反无状态红线**:通知按 `notification-center/<userId>/<center>/<id>.json` 一条一文件落盘在资产树内(`cmx-container/assets/portal/data/`),配 `OnceLock<Mutex<HashMap>>` 未读计数缓存 + 进程内全局写锁,`lib.rs` 自述"部署假设:单实例"——违反根 AGENTS.md §五「本地磁盘当持久化存储」「Mutex+OnceLock 缓存业务数据」两条红线;list/counts 全量扫目录逐文件读,无分页、无上限。
2. **MDM 死信通知 401 全失败**(评审代码级坐实):MDM 分发死信经 HTTP 回环发布,body 用 snake_case `"user_id"`,而 `NotifyInput` 是 `#[serde(rename_all = "camelCase")]`,该字段被 serde 静默忽略 → handler 用"当前认证身份"回填 → 服务 key(X-API-Key)无用户身份(`auth_context.user_id` 为空)→ `notify_user_id()` 返回 **401**。现行代码下 MDM 通知根本发不进去;历史上 8 月 18 日落进 `admin/` 目录的 29 条是当时契约不同的遗留(目录名只是当时 body 字面值,并非真实用户目录)。
3. **功能缺失**:无消息类型字段、无分页、link 字段前端完全未消费、群发/按部门/按角色发送不存在。

## 二、目标与已确认决策

目标:通知中心升级为**集群安全的企业级通知子系统**——存储进平台库 PostgreSQL、支持指定人/部门(含子部门)/角色/全员群发、未读统计 SQL 直出、多实例角标实时、数万用户量级不阻塞、表增长可控、服务接入语义明确、防滥用。

| 决策项 | 结论 | 备注 |
|---|---|---|
| 代码归属 | **原地改写 `cmx-portal/src/notify`** | 复用 `dam/store.rs` 已验证的 `cmx_database::get_default_db_manager() + get_default_db_id()` 模式;handler 与依赖链零变动;未来需要下沉 cmx-container 时表结构不动、只挪代码 |
| 跨服务推送 | **HTTP 契约**(POST /api/notifications/publish + X-API-Key 服务身份) | 与 MDM 回环一致,天然解耦,不依赖存储代码归属 |
| 集群广播 | **本期接 Redis pub/sub** | 门户已启用 Redis(auth 会话在用);基建现成(cmx-buffer PubSubOps/GlobalSubscriberManager),照抄 cmx-plugin 集群广播先例 |
| 发布权限 | **群发(部门/角色/全员)限管理员** | 单发/指定 ≤20 人任意登录用户可用;api_key 服务身份放行但必须显式给收件目标 |
| 保留策略 | **未读默认 90 天 / 已读 30 天**(可配置) | publish 未显式给 expireAt 时按默认倒推 |
| 前端范围 | **同步增强消息中心页** | 筛选/分页/link 跳转;管理端发布页面留二期 |
| 存量数据 | **丢弃**(29 条 8 月 18 日测试期死信) | `databack/` 备份目录不动 |
| SQL 维护通道 | **sql-guide 技能治理通道** | migrations + init_ddl.sql 同步;代码不执行 DDL(详见 §三) |

## 三、表设计(SQL 走 sql-guide 治理通道)

**归属:主库 platform**(`cmx_` 前缀平台功能表,通知存储在门户进程连平台库;`cmx_flow_*`/`cmx_code_*` biz 例外前缀不适用)。

**落地四步(严格按 sql-guide):**

1. 新建 `cmx-container/docs/sql/v2/platform/migrations/20260826_001_通知中心建表.up.sql`(当日无既有序号,001 可用):
   - 四行头注释块(迁移说明/影响表/操作类型 CREATE TABLE/回滚方式);
   - 内容 = 下述两表的 `CREATE TABLE IF NOT EXISTS` + 逐列 `COMMENT ON COLUMN`(一行一条)+ `CREATE [UNIQUE] INDEX IF NOT EXISTS`;
   - 禁 DROP TABLE;JSONB 默认值写 `'{}'::jsonb` 形式。
2. 同步 `docs/sql/v2/platform/init_ddl.sql` 新增两表区块(建表 → COMMENT → 索引,**终态无 ALTER**)。
3. `init_dml.sql` 无内置种子,不动。
4. **后续任何字段/索引变更同样走 sql-guide**(migrations 新文件 + init_ddl 同步)。

门户 `portal-server-dev.toml` 与 `portal-server.toml` 的 `[migration]` 均已 `enabled = true, dir = "../cmx-container/docs/sql/v2"` → **启动时迁移引擎自动建表,代码不执行任何 DDL**(无 ensure_schema,消除"两套真相"风险)。

### 3.1 通知主体表(一条通知一行;群发收件明细在收件表)

```sql
CREATE TABLE IF NOT EXISTS cmx_notification (
    id              BIGINT PRIMARY KEY,            -- 雪花号 cmx_utils::id::snowflake_id_str
    center          VARCHAR(16)  NOT NULL,         -- task | message | log(三中心)
    type            VARCHAR(64)  NOT NULL DEFAULT 'system',   -- 业务类型: system / mdm.dead_letter / flow.approval / job.finished ...
    level           VARCHAR(16)  NOT NULL DEFAULT 'info',     -- info | success | warning | error
    title           VARCHAR(500) NOT NULL,
    body            TEXT         NOT NULL DEFAULT '',
    link            VARCHAR(1000) NOT NULL DEFAULT '',  -- 跳转: node:<工作区节点id> / menu:<菜单key> / https://...
    ext             JSONB        NOT NULL DEFAULT '{}'::jsonb,   -- 扩展负载(业务单据 id 等);聚合命中时含 count
    agg_key         VARCHAR(128) NOT NULL DEFAULT '',     -- 聚合键(如 subscription_id),同键时间窗内合并计数
    sender_id       VARCHAR(64)  NOT NULL DEFAULT '',     -- 发送者用户 id(服务代发为空)
    sender_name     VARCHAR(100) NOT NULL DEFAULT '',     -- 显示名(服务名/用户名)
    source          VARCHAR(64)  NOT NULL DEFAULT '',     -- 来源服务: portal / mdm / flow ...
    target_type     VARCHAR(16)  NOT NULL DEFAULT 'user', -- user | org | role | all(审计冗余)
    target_refs     JSONB        NOT NULL DEFAULT '[]'::jsonb,   -- 原始目标引用(审计)
    recipient_count INT          NOT NULL DEFAULT 0,
    status          VARCHAR(16)  NOT NULL DEFAULT 'done', -- pending(异步展开中) | done
    created_at      BIGINT       NOT NULL,                -- epoch ms
    expire_at       BIGINT       NOT NULL DEFAULT 0       -- 0=按默认保留期;过期由清理任务删除
);
CREATE INDEX IF NOT EXISTS ix_cmx_notification_created ON cmx_notification (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_cmx_notification_expire  ON cmx_notification (expire_at) WHERE expire_at > 0;
CREATE INDEX IF NOT EXISTS ix_cmx_notification_pending ON cmx_notification (created_at) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS ix_cmx_notification_agg     ON cmx_notification (agg_key, created_at DESC) WHERE agg_key <> '';
```

### 3.2 收件明细表(写扩散:每收件人一行)

```sql
CREATE TABLE IF NOT EXISTS cmx_notification_recipient (
    id              BIGINT PRIMARY KEY,
    notification_id BIGINT      NOT NULL,
    user_id         VARCHAR(64) NOT NULL,           -- cmx_user.id(雪花 id 字符串)
    center          VARCHAR(16) NOT NULL,           -- 冗余主体 center,未读统计免 join
    is_read         BOOLEAN      NOT NULL DEFAULT FALSE,
    read_at         BIGINT      NOT NULL DEFAULT 0,
    created_at      BIGINT      NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_cmx_notif_recv ON cmx_notification_recipient (notification_id, user_id);
CREATE INDEX IF NOT EXISTS ix_cmx_notif_recv_user ON cmx_notification_recipient (user_id, center, is_read, created_at DESC);
```

**写扩散理由**:企业量级(数千~数万用户)下群发展开行数可控,换来已读/未读/删除/统计全部退化为单表行级操作;`uk(notification_id,user_id)` 兜住重复展开。epoch-ms BIGINT 时间戳、无平台审计 8 字段——运行态数据的有意风格选择(与 cmx_job 一致),但**文件落点走治理通道**(与 cmx_job 的差异,按用户要求)。

## 四、后端设计(cmx-portal/src/notify/ 重写)

### 4.1 初始化(无 DDL)

- 惰性 OnceCell(**`get_or_try_init`:错误不缓存,失败透传首个请求、后续请求自动重试**):
  1. `to_regclass` 轻量校验两表存在,缺失 → 明确报错「通知表未建:请启用 [migration] 迁移或手工执行 init_ddl.sql」;
  2. spawn 清理任务 + 异步展开任务;
  3. 注册 Redis 订阅。
- **Redis 订阅注册失败仅 warn 降级进程内广播,不影响初始化成功**;`GlobalSubscriberManager` 先 `is_initialized()` 守卫再 `get()`(未初始化会 panic;portal 启动链 `init_cache` 硬依赖 Redis,守卫是防御性的)。

### 4.2 publish 流程(按序)

1. `NotifyInput` 加 `#[serde(alias = "user_id")]` 兼容历史 snake_case 入参。
2. **权限先短路**:含 orgIds/roleCodes/all 的群发请求,先校验 `auth_context.has_role("admin")`(复用现成 has_role,含 `system:all` 短路),非 admin → 403,不进解析。
3. **收件人解析**(pure SQL,不引 cmx-iam 依赖,与 dam 一致):
   - usernames/userIds → `SELECT id FROM cmx_user WHERE ... = ANY($1) AND archived = 0`(userIds 做存在性校验,miss 丢弃 + warn);
   - orgIds(不含子部门)→ `WHERE org_id = ANY($1) AND status=1 AND archived=0`;
   - orgIds(含子部门)→ `WITH RECURSIVE org_tree AS (SELECT id FROM cmx_org WHERE id=ANY($1) UNION ALL SELECT o.id FROM cmx_org o JOIN org_tree t ON o.parent_id=t.id) SELECT DISTINCT u.id FROM cmx_user u JOIN org_tree ot ON u.org_id=ot.id WHERE u.status=1 AND u.archived=0`(按 parent_id 递归,不依赖 path 质量);
   - roleCodes → `cmx_user_role × cmx_role(code) × cmx_user`;
   - all → `SELECT id FROM cmx_user WHERE status=1 AND archived=0`;
   - 各来源**并集去重;解析后为空 → 400「收件人为空」**。
4. **发布矩阵**(剩余分支):

   | 身份 | targets/userId | 行为 |
   |---|---|---|
   | 用户身份 | 均空 | 回填当前登录用户(兼容旧契约) |
   | 用户身份 | 去重后 ≤20 人 | 放行 |
   | 用户身份 | >20 人 | 校验 admin,否则 403 |
   | api_key 服务身份 | targets 非空 | 放行;sender_name 默认取 source 服务名 |
   | api_key 服务身份 | 空 | **400 缺少收件目标**(不是 401) |

5. **限流**:Redis `INCR notify:rl:{user_id}` EXPIRE 60s,超 `rate_limit_per_min`(默认 30)→ 429;**空身份(api_key)用 source 维度键** `notify:rl:src:{source}`;Redis 不可用 fail-open。
6. **聚合(通知风暴防刷屏)**:入参 aggKey 非空时,查同 aggKey、同收件人集(输入 targets 规范化排序后比较)、1h 窗口内、status=done 的未读通知,命中则**单条原子 SQL**(`jsonb_set` 计算 ext.count+1、更新标题计数)不新增行,并广播 counts 事件;**聚合仅同步路径生效(pending 主体跳过)**;未命中走正常落库。
7. **落库**:收件人 ≥ `async_fanout_threshold`(默认 2000)→ 主体 status=**pending** 立即返回,后台展开;否则单事务同步分批 INSERT(500 行/批,`ON CONFLICT (notification_id,user_id) DO NOTHING`)。
8. expireAt 未显式给 → 按配置倒推(retention_days=90);已读行由清理任务按 retention_read_days=30 删。
9. **广播**:per-recipient notify+counts 事件**独立上限 100 条**,超出(101~2000 合规直列场景)改发单条 kind=**fanout** 提示事件;异步大 fanout 同样只发 fanout 事件。

### 4.3 查询与已读

- `list`:JOIN 查询,center/type/level/isRead 过滤;**keyset 分页** cursor=(created_at,id) 元组比较,limit 默认 50 上限 200;响应 `{items, nextCursor, total(仅首页)}`;输出契约为旧字段超集:`{id,center,type,title,body,level,link,read,createdAt,senderName,source}`。
- `counts`:`SELECT center, COUNT(*) FROM cmx_notification_recipient WHERE user_id=$1 AND is_read=false GROUP BY center` + **零填充**三中心 `{task,message,log,total}`(形状不变);删除全部内存缓存/全局写锁/文件 IO。
- `mark_read`(notification_id 定位,center 入参保留仅兼容)/ `mark_all_read`:UPDATE recipient 行(仅本人,user_id 取自 token,无越权)。

### 4.4 后台任务(多实例安全)

- **清理任务**(10min interval):先按行限批删 recipient(已读超 retention_read_days、或所属主体过期),再删无 recipient 且过期主体;SQL 一律 `DELETE ... WHERE id IN (SELECT ... LIMIT n FOR UPDATE SKIP LOCKED)` 形(PG 无 `DELETE ... LIMIT` 语法)。
- **异步展开任务**(5s loop):SKIP LOCKED 认领 pending 主体 → 重解析收件人 → 分批 1000 行/批、**每批独立事务** INSERT ON CONFLICT DO NOTHING → 完成置 done 并**回写 recipient_count 实插行数**;崩溃重启重拾,幂等。

### 4.5 Redis 集群广播(本期新增)

- `cmx-portal` 新增依赖 `cmx-buffer`;
- publish 落库后 `publish_json("cmx:notify", event)`;
- 每实例初始化时经 `GlobalSubscriberManager` 订阅该频道,回调转发进本进程 hub(**照抄 `cmx-plugin/core/manager.rs` 集群广播先例**,断线自动重连重订阅);
- kind=fanout 事件由 SSE handler 收到后对本连接用户即时查一次 counts 推送;
- Redis 不可达降级进程内广播 + warn;`hub.rs` 通道容量保持 256(控制事件发射量而非缓冲)。

## 五、handler 改造(cmx-container/.../cmx-common-api/src/handlers/portal/notify.rs)

6 条路由不变(合规:无可变路径段、无 PUT):

| 路由 | 变化 |
|---|---|
| GET /api/notifications | 新增可选 query:type / level / isRead / limit / cursor;响应 `{items, nextCursor, total(仅首页)}`(旧前端只读 items,兼容) |
| GET /api/notifications/centers | 静态三元组不变 |
| GET /api/notifications/counts | 形状不变 `{task,message,log,total}` |
| POST /api/notifications/publish | body 扩展 `type/targets/expireAt/aggKey/source`(见 §4.2 矩阵);utoipa 改具体 schema |
| POST /api/notifications/mark-read | 不变(center 仅兼容保留) |
| GET /api/notifications/stream | 不变(新增 fanout 事件内部处理) |

**跨服务接入文档**(归档方案文档内):发布契约、X-API-Key 服务身份、targets 结构、type/level 值域、错误码语义(400 收件为空 / 403 非管理员群发 / 429 限流)。

## 六、MDM 修复(cmx-mdm/.../distribution/dispatcher.rs)

- body 改 camelCase + `targets: {usernames: ["admin", created_by], userIds: [created_by]}`(**双数组防御**:created_by 是用户名还是雪花 id 两种可能都覆盖,服务端并集去重、miss 自动丢弃 warn);
- 补 `type: "mdm.dead_letter"`、`expireAt: now+30d`、`aggKey: <subscription_id>`(死信风暴聚合)。

## 七、前端增强(assets/portal/data/native-pages/sources/portal/notify/center.js)

- **筛选条**:type 下拉(列表 distinct 聚合)、level 下拉、"仅看未读"开关,变化即带参重查;
- **分页**:「加载更多」(nextCursor 递进,按 total/游标判空);
- **角标**:头部未读数改用 counts 接口值(不再从当前页 items 计算,分页后不错);
- **centers**:改消费 `/notifications/centers`(去前端硬编码);
- **link 跳转**:点击条目 → mark-read 后,`node:<id>`/`menu:<key>` → 派发 `portal-help-action` 组合事件(portal-app.js 现成通道);`https://` → window.open;空 → 仅刷新;
- esc() 防 XSS 沿用;Neo 主题零硬编码色值;改完 `./scripts/publish-assets.sh portal`。

## 八、配置(config-sync 技能同步 config_template.toml + CONFIG_MANUAL.md)

```toml
[notify]
retention_days = 90          # 未读保留上限(publish 未显式 expireAt 时倒推)
retention_read_days = 30     # 已读保留
async_fanout_threshold = 2000  # 收件人超过即转后台异步展开
rate_limit_per_min = 30      # 每用户每分钟发布上限(Redis 不可用 fail-open)
```

## 九、存量清理

`rm -rf cmx-container/assets/portal/data/notification-center`(29 条测试期死信;`databack/` 备份目录不动)。文件存储代码随 store.rs 重写一并消失。

## 十、验证清单

1. **迁移链**:重启门户 → 迁移引擎自动执行 `20260826_001`,`cmx_schema_migrations` 台账出现该 version,两表建成(列/注释/索引齐全);
2. 双 ws `cargo check` + `cargo clippy`(cmx-portalservice + cmx-container,跨 ws 依赖硬约束);
3. store 单测(连本地库):发布矩阵、群发 403、解析为空 400、异步展开幂等、聚合原子性、清理分批、keyset 分页、counts 零填充、DataValue::Array→`ANY($1)` 绑定回归(cmx-database 已有实现+测试,回归即可);
4. 端到端:登录发布(单发/部门/全员/越权 403/api_key 各分支/限流 429);SSE 角标含双实例模拟(两进程连同一 Redis);MDM 死信落到雪花 id 创建人;Redis 断连降级;
5. 前端 `npm run build -w cmx-portal-manager` + eslint(改动文件);center.js 构建验证。

## 十一、实施顺序

1. SQL 三步走(sql-guide:migrations `20260826_001_通知中心建表.up.sql` + init_ddl.sql 同步);
2. store.rs 重写(CRUD + 收件人解析 + 权限 + 聚合 + 限流)+ 单测;
3. Redis 集群广播(cmx-buffer 依赖 + 订阅转发 + fanout 事件);
4. 异步展开任务 + 清理任务;
5. handler + openapi 扩展;
6. MDM dispatcher 修复;
7. center.js 增强 + publish-assets;
8. 配置项(config-sync)+ 存量目录删除 + 端到端验证;
9. 本方案文档补充实施结论(扩展点说明见 §十二)。

## 十二、扩展点(本期不做,模型已预留)

| 扩展 | 预留方式 |
|---|---|
| 撤回通知 | 主体表 status 加 `revoked`,list 过滤(现有列够用) |
| 通知偏好/免打扰 | 新表 `cmx_notification_preference(user_id, type, channel, enabled)`,与现模型正交 |
| 置顶公告 | 主体表加 sticky 布尔列(走 sql-guide 迁移) |
| 邮件/webhook 渠道投递 | 独立 outbox 表 `cmx_notification_delivery(recipient_id, channel, address, status, attempts...)`,不塞进 recipient 表 |
| api_key 精细授权 | 现成 `cmx_auth_api_key.scopes` 字段加 `notify.publish` scope 校验 |
| 新增中心类型 | 后端单一 const 收敛校验 + 前端已改消费 centers 接口 |

## 附:评审记录(/reviewplan)

- **第一轮(全面审查)**:发现 3 个 P0(SSE 进程内 hub 多实例失效、publish 无权限门槛、服务身份语义未定义且 MDM 现状 401 全失败)+ 4 个 P1(数万收件人同步展开长事务、expire 默认 0 无限膨胀、通知风暴无聚合、created_by 语义未验证)+ 11 个 P2 → v2 全部吸收;Redis pub/sub、群发限管理员、保留期 90/30 经用户拍板确认。
- **第二轮(复核)**:15 项问题 14 项闭合、1 项部分闭合;新发现 8 项(0 个 P0/P1,实施约束级):Redis 订阅注册失败语义、per-recipient 广播上限 100、聚合原子 SQL/独立列索引/广播遗漏、DELETE LIMIT 语法、限流键空身份退化、recipient_count 回写、权限短路顺序、get_or_try_init 语义 → 已全部并入本版。
- **第三轮(用户指出)**:SQL 维护通道缺失 → DDL 从 crate 内嵌(cmx_job 风格)改为 **sql-guide 治理通道**,代码删除 ensure_schema,依赖门户已启用的迁移引擎自动建表,消除"两套真相"风险;后续表变更同样走 sql-guide。
- **已知取舍(非阻塞)**:api_key 服务凭证本期完全信任(全员群发可用),未来用现成 scopes 字段收紧;限流依赖 Redis,不可用时 fail-open。

---

## 十三、实施结论(2026-08-26)

全部按方案落地并验证通过。改动清单:

| 仓库 | 文件 | 内容 |
|---|---|---|
| 根仓 | `documents/plans/20260826_cmx-portal_通知中心数据库化与群发改造方案.md` | 本方案 |
| cmx-container | `docs/sql/v2/platform/migrations/20260826_001_通知中心建表.up.sql`(新)+ `platform/init_ddl.sql` | 两表建表(含逐列 COMMENT),迁移引擎启动自动执行 |
| cmx-container | `crates/libs/cmx-jsonstore/src/error.rs` | PortalError 新增 Forbidden(403)/TooManyRequests(429) 变体 + From 映射 |
| cmx-container | `crates/libs/cmx-apis/cmx-common-api/src/handlers/portal/notify.rs` | 重写:PublishCtx 身份构建、列表过滤+游标分页 query、发布矩阵、SSE fanout 事件处理 |
| cmx-container | `config/config_template.toml` + `CONFIG_MANUAL.md` | `[notify]` 四配置项(retention_days/retention_read_days/async_fanout_threshold/rate_limit_per_min) |
| cmx-container | `assets/portal/data/native-pages/sources/portal/notify/center.js` | 消息中心页增强:type/level/仅未读筛选、nextCursor 加载更多、counts 角标、centers 接口消费、link 跳转(portal-help-action) |
| cmx-portalservice | `Cargo.toml` + `crates/cmx-portal/Cargo.toml` | 新增 cmx-buffer 依赖(Redis 集群广播 + 限流) |
| cmx-portalservice | `crates/cmx-portal/src/notify/store.rs` | 全量重写:PG CRUD/收件人解析(含 WITH RECURSIVE 子部门)/发布权限矩阵/限流/聚合/异步展开/清理任务/Redis 广播/惰性初始化;文件存储与内存缓存删除 |
| cmx-portalservice | `crates/cmx-portal/src/notify/{mod,hub}.rs` | 文档与导出更新(fanout 事件类型) |
| cmx-mdm | `crates/cmx-mdm-app/src/distribution/dispatcher.rs` | 死信通知修 camelCase + targets 双数组防御 + type/aggKey/expireAt |
| 删除 | `cmx-container/assets/portal/data/notification-center/` | 存量 29 条文件通知(按决策丢弃;databack 备份未动) |

**验证结果**:
- 迁移链:启动自动执行 `20260826_001`(279ms),两表建成;
- 单测 3 个全过(连真实库:roundtrip/发布矩阵/聚合合并),测试用专用临时 cmx_user 行隔离并自清理;
- 双 ws `cargo check`/`clippy` 0 警告 + flowengine 下游验证通过(公用库变更硬约束);
- 端到端 17 项全过:用户/服务身份发布、按角色群发、聚合(同 id count=2)、api_key 无目标 400(非 401)、幽灵收件人 400、type/level/isRead 过滤、cursor 翻页(非首页 total=0)、mark-read/全部已读、SSE 连接即推 counts + 实时 notify 事件、Redis 订阅确认(`已订阅频道 cmx:notify`)。

**实施中发现并修复的问题**:
1. `GlobalSubscriberManager::initialize()` 内部 `GlobalCacheManager::get()` 未初始化会 panic——订阅注册前先 `try_get()` 守卫(测试进程无 Redis 时降级不崩);
2. 测试进程不经服务启动链,DatabaseManager 须自注册(从 dev toml 提取 db_url);`cfg!(test)` 下 PoolConfig 默认 max=1/min=2 会并行互卡,显式给池参数;
3. 收件行多行 VALUES 的 format 占位符笔误(`{}` 漏 `$` → 字面量)导致 nid 绑定错位——插桩定位后修复,单测回归通过。

**已知边界**:utoipa publish 入参仍为 `serde_json::Value`(具体 schema 文档写在 doc 注释;cmx-portal 不引 utoipa,派生 ToSchema 需跨仓引依赖,留后续);大 fanout 双实例模拟未在本轮实测(设计上经 Redis 频道天然覆盖,单实例 SSE 已验证)。

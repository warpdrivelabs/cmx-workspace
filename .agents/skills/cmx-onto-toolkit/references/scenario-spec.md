# 场景规格（scenario-spec）schema 契约

> onto_seed.py 的输入。所有段可省略；执行顺序固定：sharedProperties → interfaces → objectTypes → linkTypes → functions → actions → dctImports → funnelMappings(+sync) → objects → links → views → snapshot → docImports。全部 upsert 幂等。

```jsonc
{
  "_comment": "任意说明",
  "_skipFunnelSync": false,          // 内部开关：--skip funnelSync 时脚本自动置位

  "sharedProperties": [               // POST /shared-properties
    {"apiName": "lifecycleStatus", "displayName": "生命周期状态", "baseType": "string", "description": "…"}
  ],

  "interfaces": [                     // POST /interfaces
    {"apiName": "GovernedMaster", "displayName": "可治理主数据",
     "properties": ["lifecycleStatus", "sourceSystem", "governedBy"],   // 要求的共享属性 apiName 列表
     "status": "active"}
  ],

  "objectTypes": [                    // POST /object-types（camelCase）
    {"apiName": "Supplier", "displayName": "供应商",
     "dam": {"domain": "supplychain", "application": "procurement", "module": "supplier-mgmt"},
     "primaryKey": "supplierCode", "titleProperty": "name",
     "implements": ["GovernedMaster"],                   // 实现接口 → 必须有同名同类型属性
     "properties": [
       {"apiName": "supplierCode", "displayName": "供应商编码", "baseType": "string", "required": true},
       {"apiName": "lifecycleStatus", "displayName": "生命周期状态", "baseType": "string",
        "sharedProperty": "lifecycleStatus"}             // 引用共享属性（baseType 必须一致）
       // baseType 枚举：string/integer/long/double/decimal/boolean/date/timestamp/array/struct/…
     ]}
  ],

  "linkTypes": [                      // POST /link-types
    {"apiName": "supplierOf", "displayName": "供应",
     "objectTypeA": "Supplier", "objectTypeB": "Material",
     "cardinality": "manyToMany",       // oneToOne | oneToMany(缺省) | manyToMany
     "roleA": "供应商", "roleB": "供应物料"}
    // ── 基数铁律：cardinality 跟物理事实走。源表里只有一个外键列的关系一律 oneToMany
    //   （A=被引用端、B=持键端），严禁把单外键关系标成 manyToMany。业务含义的多对多
    //   必须有中间表：建真实中间表（如 cm_supply_record）+ 对象类型，拆成两条一对多 FK
    //   关系（中间对象模式，对标 Palantir join table / backing object type）；只有无业务
    //   语义的标签类关系才可直接 manyToMany——缺省 Edge backing 的 ol_edge 就是平台内置
    //   连接表，业务库没有中间表支撑的多对多不要硬造。
    // ── backing（关系落存储方式，缺省=Edge 物化 ol_edge）──
    // 页面口径（唯一对外形状，与 designer 速建气泡「属性映射」同构，两端各选一个字段）：
    //   {"fk": {"sourceProperty": "settleCurrencyId", "targetProperty": "id", "side": "b"}}
    //   sourceProperty = 持键端对象的外键属性（存来源表的真实外键值，不翻译不改写）；
    //   targetProperty = 对端匹配属性，缺省 = 对端 primaryKey（Palantir Key 语义）；
    //   键在对端（B 端）时写 "side": "b"。遍历时读侧实时编译属性对属性 JOIN，不落 ol_edge，
    //   links 段无需为该关系造边。
    // ★ 真源口径约定：凡来源表有代理主键 id 的，目标类型漏斗必带 id 列（属性 id=cm_*.id），
    //   外键属性存真实外键值、JOIN 走 targetProperty:"id"——语义与底层库完全一致；
    //   来源表只有自然键的（如 cm_payment_term 以 code 为锚）直接 targetProperty:"code"。
    //   外键属性必须同时在对象类型 properties 里声明（否则 UI 不可见）；外键值为空的行
    //   关系自然不出现（不报错）。
    // 历史/工具直写的内部口径 {"kind":"foreignKey","property","side"} 仍可解析（兼容）。
  ],

  "functions": [                      // POST /functions
    {"apiName": "supplierGrade", "displayName": "供应商评级",
     "runtime": "feel",                  // feel | rhai | aggregation（wasm 未实现）
     "kind": "derivedProperty",          // query | derivedProperty | validation | actionLogic | aggregation
     "inputs": [{"name": "supplier", "type": "object"}],   // type: object|objectSet|标量
     "body": "if supplier.rating >= 4.5 then \"A\" else \"B\"",
     "status": "active"}
    // Rhai 注意：该引擎不认 let mut——用 if 表达式风格，末表达式即返回值
    // aggregation 注意：body 写聚合模板 JSON 字符串；求值时顶层传 objectSet(单数)+aggregation
  ],

  "actions": [                        // POST /action-types
    {"apiName": "pauseSupplier", "displayName": "暂停合作", "description": "…", "status": "active",
     "parameters": [{"name": "supplier", "type": "object", "objectType": "Supplier", "required": true},
                    {"name": "reason", "type": "string", "required": true}],
                                         // ★ object 参数务必带 objectType：保存时派生进 om_action_type.target_object_types
                                         //   （物化列，勿手写），workshop 动作中心据此分区 + 选中对象自动绑定；
                                         //   只写 string pk 的动作 targets 为空，不会出现在“适用于 X”分区
     "logic": [                          // 五原子：createObject/createOrModifyObject/modifyObject/deleteObject/addLink/removeLink
       {"op": "modifyObject", "objectType": "Supplier", "pk": "$supplier",
        "set": {"status": "暂停", "remark": "$reason"}}],  // 任意 "$name" 递归替换为参数；值可写 {"src":"param|static|currentUser|currentTime|paramProperty",…}
     "validations": [{"expression": "objects.supplier.status == '在营'", "message": "…"}],
                                         // FEEL 谓词；上下文=参数平铺 + params.* + objects.<object参数>（自动装载的对象状态）
     "sideEffects": [                    // 六类：startBusinessProcess/notification/webhook/callFunction/emitEvent/computeReport
       {"kind": "startBusinessProcess", "flowDefKey": "supplier_review",
        "businessKey": "$supplier",      // 回调按它找对象 → 放对象 pk
        "orgId": "org-root",             // 显式发起组织（发起闸按 (defKey,orgId) 解析审批定义）
        "initiator": "<用户id>"}         // 其余键原样进流程变量
     ]}
  ],

  "dctImports": [                     // POST /import/dct（参照类型 + 字典项当场物化）
    {"apiName": "Currency", "displayName": "币种", "items": [{"code": "CNY", "name": "人民币"}]}
  ],

  "funnelMappings": [                 // POST /funnel/mappings + /funnel/sync/{type}
    {"objectType": "Supplier",
     "sourceDbId": "fico-db",           // 缺省=本体库 onto_pg；跨库需 toml [[databases]] + source_db_id 列迁移
     "sourceQuery": "SELECT code, name, (CASE WHEN … END)::double precision AS rating FROM cm_supplier",
                                        // 原生 SQL；可用 CASE 派生演示列、UNION 坏行演示隔离区
     "keyColumns": ["code"],            // 拼 pk（多列 '|' 连接）
     "titleColumn": "name",
     "propertyMap": [{"source": "code", "property": "supplierCode"}],
     "required": ["name"]}              // 映射后为空 → 违规入 oo_quarantine（sync 前清旧隔离区）
  ],

  "objects": {                        // POST /objects/{type}/batch（[{pk,title,properties}]；类型须已定义）
    "Material": [{"pk": "GYL-001", "title": "45号碳钢圆钢", "properties": {"materialCode": "GYL-001", …}}]
  },

  "links": [                          // POST /links {link, aPk, bPk}（两端对象须已存在）
    {"link": "supplierOf", "aPk": "SUP0001", "bPk": "GYL-001"}
  ],

  "views": [                          // POST /views（manual 物化成员）
    {"apiName": "view-supplier-master", "displayName": "供应商主数据", "description": "…",
     "dam": {…}, "source": "manual",
     "members": {"objects": ["Supplier", "Material"], "interfaces": ["GovernedMaster"]}}
  ],

  "snapshot": {"summary": "演示基线"},  // POST /snapshots（内容与最新存档一致时去重不涨版本）

  "docImports": [                     // POST /import/doc（单对象模型：根实体一类型、子层折叠嵌套属性、不导实例）
    {"apiName": "PurchaseOrder", "displayName": "采购订单", "dam": {…},
     "entities": [{"apiName": "PoHead", "primaryKey": "docNo", "titleProperty": "docNo",
                   "properties": [{"apiName": "docNo", "baseType": "string"}]},
                  {"apiName": "PoLine", "primaryKey": "lineId", "properties": […]}],
     "relations": [{"from": "PoHead", "to": "PoLine", "cardinality": "oneToMany", "role": "lines"}]}
  ]
}
```

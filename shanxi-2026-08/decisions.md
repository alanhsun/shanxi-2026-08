# 决策记录

| 时间 | 阶段 | 决定 | 原因 | 影响文件 | 确认角色 |
|---|---|---|---|---|---|
| 2026-07-31 | intake | 新建2026年8月15日至23日山西旅行项目；六盘水项目停止更新 | 用户明确取消六盘水计划并改为山西旅行 | trip.yaml；content/overview.md；data/budget.csv | 用户 |
| 2026-07-31 | intake | 暂时继承原项目的东莞出发、4人家庭、2间中高档房、轻松节奏与饮食限制 | 这些条件可能仍适用，但目的地与旅行时长已变化，需用户重新确认 | trip.yaml；content/overview.md | 维护者 |
| 2026-07-31 | intake | 暂以人民币18,000至32,000元作为宽幅建档估算 | 用户尚未给出山西项目预算；该区间仅用于保持预算数据契约，不是消费上限 | trip.yaml；content/overview.md；data/budget.csv | 维护者 |
| 2026-07-31 | intake | 确认沿用4人家庭、2间中高档房、轻松节奏、正餐尽量不辣；接受最多3次换酒店 | 用户同意需求建档假设并要求继续 | trip.yaml；content/overview.md | 用户 |
| 2026-07-31 | outline_review | 日期允许按航班和票价缩短；优先少走回头路，转机可作为备选 | 用户补充希望多比较航班，必要时可转机，并可晚出发或提前返回 | trip.yaml；content/overview.md；data/transport.csv | 用户 |
| 2026-07-31 | outline_review | 提议采用深圳飞大同、运城飞深圳的北进南出主线；不纳入五台山 | 当前航班价差不足以抵消中转/回头路的时间成本；五台山会增加绕行和换酒店 | trip.yaml；content/overview.md；content/days；data/*.csv | 维护者，待用户确认 |
| 2026-07-31 | outline_review | 将宽幅预算调整为人民币24,000至36,000元 | 当前4人开口程机票快照约1.06万元，原高位3.2万元偏紧；仍非硬上限 | trip.yaml；content/overview.md；data/budget.csv | 维护者，待用户确认 |
| 2026-07-31 | outline_review | 确认不去五台山、吉县住2晚、采用8月15日深圳飞大同及8月23日运城飞深圳的主航班 | 用户回复“全部按推荐”；该路线最少回头且只换酒店3次 | trip.yaml；content/overview.md；content/days；data/*.csv | 用户 |
| 2026-07-31 | detailed_review | 住宿首选定为大同宥庆、太原温德姆（山西博物院店）、又见文华、吉州宾馆，并保留同区域备选 | 兼顾接送、石板路、老人儿童休息与D9南向离境；具体房态和含税价仍需下单前复核 | content/overview.md；data/accommodation.csv；data/bookings.csv | 维护者，待用户详细定稿确认 |
| 2026-07-31 | approved | 接受4家首选酒店、人民币24,000至36,000元宽幅预算及悬空寺不凌晨排线下票的执行原则 | 用户持续目标为“全部按推荐”；详细方案和近期验证均无须改变北进南出主线 | trip.yaml；content/overview.md；data/accommodation.csv；data/bookings.csv；research/social-validation.md | 用户 |
| 2026-08-01 | approved | 所有外币票价统一按每1美元约6.80元人民币折算，并只用人民币展示比较 | 用户要求所有货币转换为人民币；统一汇率避免不同页面和旧汇率造成误判 | content/overview.md；content/days；data/transport.csv；data/bookings.csv；data/budget.csv；data/sources.csv | 用户 |
| 2026-08-01 | approved | T-14复查后仍保留8月15日深圳直飞大同、8月23日运城直飞深圳主线 | 去程4人可见总价已涨至约8160元；晚一天出发、广州中转和太原进虽便宜约2920至3170元，但分别损失完整旅行日、要求凌晨出发或增加北向折返，均不同时满足“至少省2000元且门到门仅多不超过2小时”的替换条件 | content/overview.md；content/days/day-01.md；data/transport.csv；data/bookings.csv；data/budget.csv；data/sources.csv | 维护者 |
| 2026-08-01 | approved | 在不改变24000至36000元总预算的前提下提高往返大交通分类上限，并将云冈预约改为可执行 | 两段主航班与东莞接驳现约12750元；8月16日云冈场次已进入官方15日预约期 | data/budget.csv；data/bookings.csv；content/overview.md | 维护者 |
| 2026-08-01 | approved | 记录4地酒店登录价快照；暂不自动替换吉县首选 | 大同、太原、平遥均有可执行房型；吉州宾馆指定日期未显示可订房型，而同区域汉庭高级双床2间2晚约1356元且可取消；切换具体酒店仍等待用户确认 | content/overview.md；data/accommodation.csv；data/bookings.csv；data/sources.csv | 维护者，待用户确认吉县换店 |
| 2026-08-01 | approved | 住宿不要求景区位置；允许优先城市生活区或古城外的高性价比酒店 | 用户明确表示非景区酒店性价比更高；后续比较将把新增打车费用和时间一并计入 | trip.yaml；content/overview.md；data/accommodation.csv；data/sources.csv | 用户 |
| 2026-08-01 | approved | 为行程内每个景点补充历史背景和必看亮点；照片优先采用游客真实实拍 | 用户希望内部分享版更直观；为保证来源可追溯和网页长期可用，采用Wikimedia Commons开放许可游客照片并在页面登记作者、许可和原图链接，攻略平台无授权图片不复制 | content/days；media；data/images.csv；data/sources.csv | 用户、维护者 |
| 2026-08-01 | approved | 授权把公开脱敏版发布到GitHub Pages，并启用publish开关 | 用户明确要求使用其GitHub账户发布；发布仓库为alanhsun/shanxi-2026-08，仍不包含姓名、证件、订单凭证或账户信息 | trip.yaml；decisions.md；.github/workflows/pages.yml | 用户 |
| 2026-08-01 | approved | 提出万信至格、宜尚PLUS、陌上轻奢、吉县汉庭组成的生活区住宿组合，暂不覆盖原首选 | 当前登录价8晚约4944元，扣除新增网约车后仍预计净省3600至3800元；平遥大床和大同1.2米双床等取舍需一次确认 | content/overview.md；data/accommodation.csv；data/sources.csv | 维护者，待用户确认具体酒店 |
| 2026-08-01 | approved | 确认所有酒店大床和双床均可，并正式采用万信至格、宜尚PLUS、陌上轻奢、吉县汉庭组合 | 用户解除床型限制；该组合在评分和取消条件可接受时8晚约4944元，净节省足以覆盖新增网约车 | trip.yaml；content/overview.md；content/days；data/accommodation.csv；data/bookings.csv；data/budget.csv；data/transport.csv | 用户 |
| 2026-08-01 | published | GitHub Pages公开脱敏版已上线 | GitHub Actions主分支部署成功，并实际访问核验标题、日期和行程正文；正式网址为https://alanhsun.github.io/shanxi-2026-08/ | trip.yaml；decisions.md；.github/workflows/pages.yml | 维护者 |
| 2026-08-01 | published | 将筛选后的小红书、大众点评与携程游客经验转化为逐日排队、接驳、点餐和避坑规则；不改变主路线 | 用户授权使用已登录小红书并要求以用户经验改进行程；14篇近期小红书实录和公开大众点评线索支持微调，双林寺千佛殿修缮另由官方来源复核 | research/social-validation.md；content/overview.md；content/days；data/sources.csv | 用户、维护者 |
| 2026-08-02 | published | 将候选比较、核验过程和历次更改集中到版本追踪；正文只保留当前有效安排 | 用户要求最终呈现简洁清晰并集中展示更改内容；此调整不改变路线住宿和预算 | content/overview.md；content/version-tracking.md；tools/build_site.py；tools/site.css | 用户、维护者 |
| 2026-08-02 | published | 新增独立用餐指南；按每天三餐提供2至3个选择及介绍、真实评价摘要和推荐菜 | 用户要求用餐推荐更细致；旅行日早班餐和机场餐因航站楼或营业动态，以2至3个稳妥执行方案替代虚构店名 | content/dining-guide.md；data/sources.csv；tools/build_site.py | 用户、维护者 |
| 2026-08-02 | published | 为D1至D9增加默认折叠的SVG路线示意图及公开地点高德导航入口 | 用户同意采用路线示意图；矢量图比生成式图片更能保持中文地名、顺序和交通时间准确，且无需公开地图API密钥 | data/day-routes.yaml；tools/build_site.py；tools/site.css；content/version-tracking.md | 用户、维护者 |
| 2026-08-02 | published | 为生成网页引用的样式文件增加基于核验时间的版本标识 | 线上检查发现旧浏览器缓存会让新SVG路线图缺少配色；版本化URL保证发布后立即加载当前样式 | tools/build_site.py；content/version-tracking.md | 维护者 |
| 2026-08-02 | published | 增加小红书与大众点评餐饮研究比重并更正具体分店和点菜规则；不改变主路线 | 用户要求提高真实笔记和评论研究比重；新增阅读12篇小红书餐饮实吃并在正确目的地核对大众点评计划分店；聚合评分不冒充完整评论正文 | research/social-validation.md；content/dining-guide.md；content/days；data/sources.csv；data/day-routes.yaml | 用户、维护者 |
| 2026-08-02 | published | 将山西省内交通改为大同机场取车、运城机场异地还车的租车自驾，并按驾驶与停车条件调整逐日安排 | 用户明确要求省内改为租车自驾；北进南出城市顺序无需改变，D5取消高铁换乘，D9提前出发并增加加油还车缓冲；总预算同步调整为人民币28000至41000元 | trip.yaml；content/overview.md；content/days；data/transport.csv；data/bookings.csv；data/budget.csv；data/day-routes.yaml | 用户、维护者 |
| 2026-08-02 | approved | 出行人数改为2名成人＋1名8岁儿童，取消原老人名额 | 用户明确更新同行人数；门票、餐饮、机票预算占位和预约数量均按3人重算 | trip.yaml；content/overview.md；content/days；data/transport.csv；data/bookings.csv；data/budget.csv | 用户、维护者 |
| 2026-08-02 | approved | 全程住宿改为1间，优先家庭房或亲子房，其次为订单页明确允许3人同住的大床房 | 用户明确要求1间房并优先大床或家庭房；儿童入住人数、床型和加床政策须在下单页逐店确认 | trip.yaml；content/overview.md；content/days；data/accommodation.csv；data/bookings.csv；data/sources.csv | 用户、维护者 |
| 2026-08-02 | published | 租车车型由7座改为5座燃油中型SUV或行李厢足够的舒适轿车，总预算调整为人民币22000至34000元 | 三人出行无需承担7座溢价，一间房也显著降低住宿成本；仍保留儿童增高坐垫、完整保障和异地还车预算 | trip.yaml；content/overview.md；content/days；data/transport.csv；data/bookings.csv；data/budget.csv；content/version-tracking.md | 维护者 |
| 2026-08-02 | approved | 航班筛选取消出发和抵达时间限制，经停或中转均可 | 用户希望扩大航班选择范围，必要时可接受凌晨出发、晚间抵达或转机 | trip.yaml；content/overview.md；data/transport.csv；content/version-tracking.md | 用户 |
| 2026-08-02 | approved | 去程改为8月15日广州飞大同，当前主选东方航空MU6733经停武汉 | 用户明确指定广州—大同；当前2成人＋1儿童人民币总价快照约3622元且11:55抵达，比原深圳直飞更便宜、更早到达；D1改为02:10从东莞出发并增加抵达后午休 | trip.yaml；content/overview.md；content/days/day-01.md；content/dining-guide.md；data/transport.csv；data/bookings.csv；data/budget.csv；data/day-routes.yaml；data/sources.csv；content/version-tracking.md | 用户、维护者 |
| 2026-08-05 | approved | 在不走回头路的前提下加入雁门关与五台山；太原和平遥各缩为1晚并删除晋祠 | 用户要求插入五台山和雁门关且允许减少平遥时间；大同—浑源—应县—雁门关—代县—五台山—太原—平遥仍保持北向南 | trip.yaml；content/overview.md；content/days；data/transport.csv；data/day-routes.yaml；data/bookings.csv | 用户、维护者 |
| 2026-08-05 | approved | 住宿以避免溢价为原则；房费停车接驳和重复往返合计比较，不机械排斥景区内住宿 | 用户明确要求住宿尽量避免溢价；五台山同日实价显示核心区328元仅比南门外三人间294元高34元，所以设核心区总价不高于450元且可免费取消的阈值 | trip.yaml；content/overview.md；content/days/day-03.md；content/days/day-04.md；data/accommodation.csv；data/bookings.csv；data/budget.csv；data/sources.csv | 用户、维护者 |
| 2026-08-05 | published | 代县主选切换为开普顿连锁酒店尊享双床房202元；全智酒店降为库存待恢复的备选 | 8月5日登录携程同人数查询中，开普顿1.5米加1.2米双床房明确可住3人且可当日免费取消；全智房价区域为空，不能作为可订主选 | content/overview.md；content/days/day-03.md；data/accommodation.csv；data/bookings.csv；data/sources.csv | 维护者 |
| 2026-08-05 | approved | 去程确认已出票MU6949广州至宁波加MU6111宁波至大同；返程确认已出票CZ5266运城至广州 | 用户提供最终航班号；旧MU6733经武汉和运城至深圳方案停止执行，机票人民币实付总额待用户补录 | trip.yaml；content/overview.md；content/days/day-01.md；content/days/day-09.md；data/transport.csv；data/bookings.csv；data/sources.csv | 用户、维护者 |
| 2026-08-05 | approved | D8壶口后改住运城机场对面，吉县由2晚减为1晚 | CZ5266公开时刻07:20起飞，若D9凌晨从吉县驾驶约3.5小时会形成不可接受的疲劳驾驶与误机风险；微源国际酒店距机场约280米，仅在含税可取消价不高于450元时预订 | content/overview.md；content/days/day-08.md；content/days/day-09.md；data/accommodation.csv；data/transport.csv；data/bookings.csv | 维护者 |
| 2026-08-08 | approved | 去程MU6949广州至宁波加MU6111宁波至大同的3人总价确认为2915元；宁波中转加入条件式半日游 | 用户提供已出票总价并明确希望利用宁波转机做半日游；小红书近期3小时至4小时实录反复把南塘老街作为紧凑中转选项。仅在行李直挂大同、两段登机牌已出、首段正常落地时执行；15:05硬离开市区，其他情况留机场 | content/overview.md；content/days/day-01.md；content/dining-guide.md；data/day-routes.yaml；data/transport.csv；data/bookings.csv；data/budget.csv；data/sources.csv；research/social-validation.md | 用户、维护者 |

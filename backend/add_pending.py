"""追加更多待审核稿件"""
from app.database import SessionLocal
from app.models import Article

db = SessionLocal()

new_articles = [
    Article(
        title="本市文化创意产业园区招商迎来开门红",
        content="今年一季度，本市三大文创园区共引进文创企业87家，同比增长35%。其中数字内容、动漫游戏、创意设计类企业占比超过六成。\n\n## 入驻亮点\n位于西城的数字文创园吸引了包括知名游戏开发商在内的15家企业入驻，预计年内将创造超2000个就业岗位。\n\n## 政策扶持\n市文创办表示，将出台新版文创产业扶持政策，对入驻企业给予租金补贴和税收优惠。",
        status="pending_review", category="文化", tags="文创,产业园,招商引资",
        author_id=5, summary="一季度三大文创园区引入87家企业，数字内容企业占六成。",
    ),
    Article(
        title="夏季用电高峰到来，供电部门多措并举保供",
        content="随着连续高温天气来袭，全市电网负荷持续攀升。截至今日下午2时，最大负荷已达2850万千瓦，较去年同期增长7.3%。\n\n## 保供措施\n电力部门已启动迎峰度夏应急响应，主要通过以下措施保障供电：一是统筹调度发电机组应发尽发；二是加强跨省区电力互济；三是引导用户错峰用电。\n\n## 市民建议\n供电部门呼吁广大市民合理设置空调温度（建议26℃以上），节约用电。",
        status="pending_review", category="民生", tags="用电,高温,保供",
        author_id=6, summary="电网负荷达2850万千瓦，电力部门启动应急响应保障供电。",
    ),
    Article(
        title="跨境电商综试区扩容至中西部，红利如何释放",
        content="国务院常务会议近日决定，新设一批跨境电商综合试验区，重点覆盖中西部主要城市。至此，全国跨境电商综试区将增至185个。\n\n## 政策红利\n新设综试区将享受同等政策待遇，包括税收优惠、通关便利、外汇管理等多项支持措施。\n\n## 企业反响\n某中西部跨境电商企业负责人表示，新政将大幅降低企业出海门槛，预计年内该地区跨境电商交易额将增长40%以上。",
        status="pending_review", category="财经", tags="跨境电商,综试区,外贸",
        author_id=7, summary="新增跨境电商综试区覆盖中西部，企业享受税收通关等多重红利。",
    ),
    Article(
        title="首届全球消费电子展将在本市举办",
        content="全球消费电子协会今日宣布，首届全球消费电子展将于今秋在本市国际会展中心举办，预计将有来自50多个国家和地区的1200家企业参展。\n\n## 展会亮点\n展会设置人工智能、智能家居、可穿戴设备、新能源汽车技术等八大主题展区。多家头部科技企业已确认参展。\n\n## 经济效应\n预计展会期间将吸引专业观众15万人次，带动周边消费超过50亿元。",
        status="pending_review", category="科技", tags="消费电子,展会,科技",
        author_id=5, summary="秋季举办首届展会，50国1200家企业参展，涵盖AI智能家居等八大展区。",
    ),
    Article(
        title="高校毕业生基层就业政策再升级",
        content="教育部等多部门联合印发通知，出台新一轮高校毕业生基层就业优惠政策。\n\n## 主要政策\n1. 基层就业满3年可获学费补偿或助学贷款代偿\n2. 在基层工作满5年，考研可享受加分\n3. 基层公务员定向招录比例提高至15%\n\n## 专家解读\n教育专家认为，新政将有效引导毕业生向基层流动，优化人才分布结构。",
        status="pending_review", category="教育", tags="毕业生,基层就业,政策",
        author_id=6, summary="基层就业满3年获学费补偿，考研加分、定向招录比例提高。",
    ),
    Article(
        title="城市垃圾分类智能化管理迈入新时代",
        content="市城管委今日宣布，全市垃圾分类智能监管平台正式上线运行。该平台利用AI图像识别技术，可自动识别居民垃圾分类投放情况。\n\n## 技术亮点\n智能垃圾桶配备称重、识别、满溢预警等功能，居民扫码投放后系统自动记录分类准确率。\n\n## 推行效果\n试点社区分类准确率从65%提升至92%，垃圾减量达18%。",
        status="pending_review", category="环保", tags="垃圾分类,AI,智能化",
        author_id=7, summary="AI识别垃圾分类投放，试点社区准确率从65%提升至92%。",
    ),
    Article(
        title="新农村建设：数字技术让农产品走出去",
        content="在某县电商产业园内，村民正通过直播销售本地特色农产品。过去一年，该县农产品网络销售额突破8亿元。\n\n## 数字赋能\n该县建立了「一村一品一主播」的电商培训体系，累计培训农民主播超过3000人。\n\n## 基础设施\n全县已实现5G网络全覆盖，建成村级电商服务站120个。",
        status="pending_review", category="农业", tags="电商,直播,乡村振兴",
        author_id=5, summary="农产品网销8亿元，培训3000农民主播，5G全覆盖全县。",
    ),
    Article(
        title="轨道交通建设加速：三条线路同步推进",
        content="市轨道办今日通报，在建的地铁4号线二期、6号线、机场快线三条线路均按计划推进。\n\n## 最新进展\n4号线二期已完成80%土建工程，预计明年6月开通运营。6号线已进入盾构施工阶段。机场快线将在年底前完成车站主体结构。\n\n## 市民反响\n家住城西的市民王女士表示，地铁4号线二期开通后将大大缩短她的通勤时间，「从原来的一小时缩短到二十分钟」。",
        status="pending_review", category="交通", tags="地铁,轨道交通,建设",
        author_id=6, summary="三条地铁线正加速推进，4号线二期明年6月通车。",
    ),
    Article(
        title="城市绿化再获新提升：新增8个城市公园",
        content="市园林局宣布，今年上半年全市新增8个城市公园，新增绿地面积达120万平方米。\n\n## 公园特色\n新开放的公园各具特色，包括以湿地生态为主题的自然公园、以体育运动为主题的活力公园、以亲子游乐为主题的亲子公园等。\n\n## 市民受益\n公园全部免费向市民开放，服务半径覆盖周边30余个社区的居民。",
        status="pending_review", category="民生", tags="公园,绿化,生态环境",
        author_id=7, summary="上半年新增8个公园，新增绿地120万平方米，全部免费开放。",
    ),
    Article(
        title="区块链技术在供应链金融中的创新应用",
        content="多家银行联合科技企业推出了基于区块链技术的供应链金融服务平台，有效解决了中小企业融资难问题。\n\n## 技术优势\n区块链技术确保了交易数据的不可篡改和可追溯性，降低了金融机构的信用评估成本。\n\n## 应用效果\n试点企业融资周期从原来的15个工作日缩短至3个工作日，融资利率下降2个百分点。",
        status="pending_review", category="财经", tags="区块链,供应链金融,融资",
        author_id=5, summary="区块链平台让融资周期从15天缩至3天，利率下降2个百分点。",
    ),
]

for a in new_articles:
    db.add(a)
db.commit()
print(f"✅ 新增 {len(new_articles)} 篇待审核稿件")

# Verify
total = db.query(Article).count()
pending = db.query(Article).filter(Article.status == "pending_review").count()
published = db.query(Article).filter(Article.status == "published").count()
draft = db.query(Article).filter(Article.status == "draft").count()

print(f"现在共有 {total} 篇文章")
print(f"  草稿: {draft}")
print(f"  待审核: {pending}")
print(f"  已发布: {published}")

# Show categories
from collections import Counter
from sqlalchemy import text
rows = db.execute(text("SELECT category, status FROM articles")).fetchall()
cats = Counter(r[0] for r in rows if r[0])
pending_by_cat = Counter(r[0] for r in rows if r[1] == "pending_review" and r[0])
print(f"\n分类分布: {dict(cats)}")
print(f"待审核分类: {dict(pending_by_cat)}")

db.close()

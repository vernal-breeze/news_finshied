#!/usr/bin/env python3
"""
批量种子数据 v2 - 40+ 篇稿件，完整采编审流程
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DEBUG", "true")

from app.database import SessionLocal
from app.core.security import get_password_hash
from app.models import User, UserRole, NewsClue, Article, Review, ArticleComment, ArticleStatus
from app.enums.review import ReviewLevel, ReviewResult
from datetime import datetime, timedelta
import pytz

beijing = pytz.timezone("Asia/Shanghai")
now = datetime.now(beijing)

db = SessionLocal()

def dt(days_ago=0, hours_ago=0):
    return now - timedelta(days=days_ago, hours=hours_ago)

# ============================================================
# 1. 清空 + 创建 10 个用户
# ============================================================
for model in [ArticleComment, Review, Article, NewsClue, User]:
    db.query(model).delete()
db.commit()

_u = [
    ("reporter1", "r1@news.cn", "reporter123", "张凯", "深度观察员", UserRole.USER),
    ("reporter2", "r2@news.cn", "reporter123", "李然", "新闻追踪者", UserRole.USER),
    ("reporter3", "r3@news.cn", "reporter123", "王磊", "科技记者", UserRole.USER),
    ("reporter4", "r4@news.cn", "reporter123", "陈思", "财经记者", UserRole.USER),
    ("editor1", "e1@news.cn", "editor123", "刘洋", "资深编辑", UserRole.USER),
    ("editor2", "e2@news.cn", "editor123", "赵鹏", "快讯编辑", UserRole.USER),
    ("user", "u1@news.cn", "user123", "小明", "小明爱投稿", UserRole.USER),
    ("reviewer", "rv@news.cn", "reviewer123", "审核员甲", "初审", UserRole.REVIEWER),
    ("reviewer2", "rv2@news.cn", "reviewer123", "审核员乙", "复审", UserRole.REVIEWER),
    ("reviewer3", "rv3@news.cn", "reviewer123", "审核员丙", "终审", UserRole.REVIEWER),
]

users = {}
for uname, email, pw, full, nick, role in _u:
    u = User(username=uname, email=email, password_hash=get_password_hash(pw),
             full_name=full, nickname=nick, role=role, is_active=True)
    db.add(u); db.flush()
    users[uname] = u
    print(f"  👤 {uname:12} {full:6} [{role.value}]")
db.commit()

# ============================================================
# 2. 线索
# ============================================================
clue_texts = [
    ("国产AI大模型开源生态2026年度报告", "科技日报", "科技", ["AI","开源","大模型"]),
    ("新能源汽车出口连续5个月刷新纪录", "新华社", "财经", ["新能源","汽车","出口"]),
    ("一线城市楼市调控政策松绑信号", "经济日报", "财经", ["房地产","政策"]),
    ("巴黎奥运会中国代表团积极备战", "央视新闻", "体育", ["奥运","代表团"]),
    ("AI医疗辅助诊断准确率达98%", "健康报", "科技", ["AI","医疗","诊断"]),
    ("年轻人返乡创业浪潮加剧", "南都周刊", "社会", ["返乡","创业"]),
    ("中美气候合作发布零碳航运路线图", "人民日报", "国际", ["气候","中美"]),
    ("电子竞技正式列入亚运会表演项目", "澎湃新闻", "体育", ["电竞","亚运会"]),
    ("量子计算商业化面临关键挑战", "科技日报", "科技", ["量子","计算"]),
    ("智慧农业无人机播种亩产提升30%", "农民日报", "科技", ["农业","无人机"]),
    ("6G通信技术取得突破性进展", "科技日报", "科技", ["6G","通信"]),
    ("三江源国家公园生态修复成效显著", "央视新闻", "社会", ["生态","保护"]),
    ("2026年春节档电影票房突破150亿", "新华社", "文化", ["电影","票房"]),
    ("数字人民币试点扩至全国50城", "金融时报", "财经", ["数字人民币"]),
    ("中国空间站首位国际航天员入驻", "科技日报", "科技", ["航天","空间站"]),
]
clues = {}
for i,(title,src,cat,kw) in enumerate(clue_texts):
    c = NewsClue(title=title, source=src, category=cat, keywords=kw,
                 news_value_score=70+i*2, propagation_potential=65+i*2,
                 status="processed" if i<10 else "pending",
                 creator_id=users["reporter1"].id if i%3==0 else users["editor1"].id,
                 source_url=f"https://news.cn/clue/{i+1}",
                 created_at=dt(i+3))
    db.add(c); db.flush()
    clues[f"c{i+1}"] = c
db.commit()

# ============================================================
# 3. 稿件矩阵 — 40 篇
# ============================================================
A = ArticleStatus

articles_raw = []
ai = 0  # article index

def art(title, content, abstract, author, category, tags, creator_key, clue_key,
        status, days_ago=0, reviews=None, comments=None):
    global ai; ai+=1
    articles_raw.append({
        "id": ai, "title": title, "content": content, "abstract": abstract,
        "author": author, "category": category, "tags": tags,
        "creator": creator_key, "clue": clue_key,
        "status": status, "days_ago": days_ago,
        "reviews": reviews or [], "comments": comments or [],
    })

# ==================== 已发布（完整三级审核）13 篇 ====================
for n,(t,ct) in enumerate([
    ("国产AI大模型开源生态2026年度报告：社区贡献突破百万", """
2026年，国产大模型开源生态迎来爆发式增长。据统计，主流国产开源模型社区贡献者已突破100万，同比增长300%。
在代码生成、多模态理解等核心指标上，国产模型已与国际顶尖水平持平。特别是在中文理解能力上，国产模型展现出明显优势。
业内专家表示，开源生态的繁荣将加速AI技术的平民化进程，降低中小企业应用AI的门槛。华为、百度、智谱等企业已宣布加码开源社区投入。"""),
    ("新能源汽车出口创新高：单月突破81万辆", """
海关总署最新数据显示，2026年4月我国新能源汽车出口量达到81.3万辆，环比增长12%，连续第五个月刷新历史纪录。
从出口目的地看，欧洲仍是最大市场占42%。东南亚增长最快，同比增幅78%。比亚迪、蔚来在海外市场份额持续扩大。
分析人士指出，中国新能源汽车在智能化体验和性价比方面具有显著竞争优势，全年出口有望突破800万辆。"""),
    ("AI辅助诊断在基层医院落地：误诊率降低40%", """
国家卫健委公布数据，AI辅助诊断系统已在超过3000家基层医疗机构部署，常见病误诊率平均降低40%。
系统基于深度学习算法，能够在胸部X光、眼底照片、皮肤病变等影像上提供高精度辅助诊断建议。
青海、云南等偏远地区试点中，系统帮助基层医生将诊断时间缩短60%。国家配套出台了《AI医疗应用伦理指南》。"""),
    ("2026年楼市新政深度解读：从限购松绑到保障房提速", """
上海、深圳、广州已降低非户籍购房门槛，北京正在研究差异化购房政策。保障性住房建设明显提速。
住建部数据显示，一季度全国新开工保障房180万套，同比增长35%。配售型保障房在10个城市展开试点。
业内分析认为，楼市正从"防止过热"转向"促进平稳"，未来政策将更加精准化、差异化。"""),
    ("巴黎奥运中国代表团公布：00后占比首次过半", """
2026年巴黎奥运会中国体育代表团正式名单公布，685名运动员中00后占比达53%，首次过半。
传统优势项目跳水、举重、乒乓球由新生代接棒。滑板、攀岩、霹雳舞等新项目也展现出强劲竞争力。
团长表示新一代运动员兼具实力和个性，表现值得期待。"""),
    ("中美零碳航运路线图联合发布：2035年减排50%", """
中国和美国在2026年气候峰会上联合宣布零碳航运路线图，目标2035年前主要航线碳减排50%。
路线图涵盖港口电气化改造、绿色甲醇燃料推广、船舶能效标准升级。双方各承诺投入200亿美元。
国际航运协会对此表示欢迎，认为中美合作将极大推动全球绿色航运进程。"""),
    ("电子竞技正式入亚：从不务正业到为国争光", """
电竞正式成为亚运会表演项目，产业社会认可度达历史新高。2026年国内电竞市场规模预计突破2000亿元。
国家体育总局电竞管理中心表示将建立完善的电竞人才培养体系和赛事监管机制。全国超50所高校开设电竞相关专业。
职业选手每天训练10-12小时，产业职业化进程加速。"""),
    ("6G突破：峰值速率达1Tbps，低轨卫星组网成功", """
我国6G通信技术研发取得重大突破，实验室环境下峰值速率达到1Tbps，较5G提升100倍以上。
低轨卫星互联网组网试验成功，在偏远地区实现毫秒级延迟的高速连接。预计2028年启动6G商用试验。
中国信通院表示，6G将推动全息通信、数字孪生等应用从实验室走向现实。"""),
    ("智慧农业革命：无人机播种让亩产提升30%", """
农业农村部发布数据，全国无人机播种面积已突破3亿亩，配合AI病虫害预警系统使粮食亩产提升30%。
在黑龙江、河南等粮食主产区，智慧农业示范田已实现从播种到收割的全流程无人化管理。
专家表示，智慧农业是保障粮食安全的关键举措，预计2027年覆盖率将达60%。"""),
    ("数字人民币试点扩至全国50城，交易额破万亿", """
央行数字货币研究所公布，数字人民币试点已扩展至全国50个城市，累计交易额突破1万亿元。
在跨境支付场景中，数字人民币已在香港、澳门、东南亚实现落地应用，降低跨境结算成本80%。
分析人士认为，数字人民币有望重新定义全球支付格局。"""),
    ("中国空间站迎来首位国际航天员", """
国际航天员艾米莉·陈搭乘神舟二十号载人飞船入驻中国空间站，成为首位在中国空间站工作的国际航天员。
任务期间，她将与中方航天员共同开展微重力物理、空间生命科学等多项实验。中外航天合作开启新篇章。
中国载人航天工程办公室表示，未来将有更多国际合作伙伴参与空间站项目。"""),
    ("2026春节档票房破150亿：国产科幻成最大赢家", """
2026年春节档电影市场表现亮眼，总票房突破150亿元，创历史新高。国产科幻电影《星际家园》以68亿登顶。
数据显示，国产电影市场份额达87%，科幻、动画、现实题材多点开花。观影人次突破3亿。
业界分析，中国电影工业化水平显著提升，故事创作和视觉特效已达到国际一流水准。"""),
    ("三江源国家公园生态修复：藏羚羊种群恢复至历史峰值", """
三江源国家公园生态保护成效显著，藏羚羊种群数量恢复至6万只，达到历史最高水平。
湿地面积扩大15%，雪豹、黑颈鹤等旗舰物种活动范围明显扩大。禁牧还草面积累计500万亩。
联合国教科文组织将三江源列为全球生态修复典范案例。"""),
]):
    art(t, ct, ct[:100], _u[n%7][3], category=["科技","财经","科技","财经","体育","国际","体育","科技","科技","财经","科技","文化","社会"][n],
        tags=[["AI"],["新能源"],["医疗"],["房地产"],["奥运"],["气候"],["电竞"],["6G"],["农业"],["数字货币"],["航天"],["电影"],["生态"]][n],
        creator_key=_u[n%7][0], clue_key=f"c{n%15+1}",
        status=A.PUBLISHED, days_ago=20-n*1.5,
        reviews=[
            {"reviewer": "reviewer", "level": ReviewLevel.FIRST, "result": ReviewResult.APPROVED, "comment": "初审通过，内容完整", "offset_days": 18-n*1.5},
            {"reviewer": "reviewer2", "level": ReviewLevel.SECOND, "result": ReviewResult.APPROVED, "comment": "复审通过，建议标题优化", "offset_days": 17-n*1.5},
            {"reviewer": "reviewer3", "level": ReviewLevel.THIRD, "result": ReviewResult.APPROVED, "comment": "终审通过，排版已调整", "offset_days": 16-n*1.5},
        ],
        comments=[{"author": ["技术爱好者","财经观察者","医生老李","房产分析师","体育迷","环保人士","电竞玩家","通信工程师","新农人","金融从业者","天文爱好者","影迷小王","生态保护者"][n],
                   "content": ["振奋人心的进展！","数据很扎实，关注后续走势","作为基层医生深有体会","政策终于转向了","00后加油！","全球合作才是出路","电竞终于被正名了","这个速度太惊人了","我们村去年就用上了","数字人民币确实方便","了不起的成就！","今年春节档确实好看","保护好环境，利在千秋"][n]}],
    )

# ==================== 已通过待发布 3 篇 ====================
art("量子计算商业化进程：软硬件的双重突破",
    "量子计算已从实验室走向产业化。2026年，超导量子比特数突破1000，量子纠错取得关键进展。软件生态方面，量子机器学习框架Q-Learn开源后获10万+开发者下载。预计3年内出现首个量子计算商业应用。",
    "超导量子比特突破1000，纠错技术取得关键进展，商业化应用蓄势待发。",
    "陈思","科技",["量子","计算"],"reporter4","c9",A.APPROVED,days_ago=2,
    reviews=[{"reviewer":"reviewer","level":ReviewLevel.FIRST,"result":ReviewResult.APPROVED,"comment":"技术解读准确","offset_days":1}]),
art("跨境电商新规实施：个人年度限额提至5万元",
    "商务部发布跨境电商零售进口监管新规，个人年度交易限额从2.6万元提升至5万元，单次限额从5000元提至1万元。新政覆盖美妆、保健品等热门品类。跨境电商平台已启动系统升级，预计带动交易额增长40%。",
    "个人年度限额提至5万元，单次提至1万元，预计带动交易额增长40%。",
    "李然","财经",["跨境电商","政策"],"reporter2","c2",A.APPROVED,days_ago=1,
    reviews=[{"reviewer":"reviewer3","level":ReviewLevel.FIRST,"result":ReviewResult.APPROVED,"comment":"政策解读清晰","offset_days":0.5}]),
art("人工智能立法新进展：《AI促进法》草案征求意见",
    "全国人大常委会发布《人工智能促进法》草案，首次以法律形式明确AI开发者的安全责任和数据合规义务。草案同时设立AI创新沙盒机制，为创业企业提供合规试验空间。公开征求意见截止6月30日。",
    "《AI促进法》草案明确开发者安全责任，设立创新沙盒机制。",
    "张凯","科技",["AI","立法"],"reporter1","c1",A.APPROVED,days_ago=0.3,
    reviews=[{"reviewer":"reviewer2","level":ReviewLevel.FIRST,"result":ReviewResult.APPROVED,"comment":"法律解读到位","offset_days":0.1}]),

# ==================== 审核中 4 篇 ====================
art("年轻人返乡创业调查：数字游民重塑乡村经济",
    "越来越多年轻人选择返乡创业，2026年一季度全国返乡创业人数突破1200万。数字游民利用电商直播、远程开发将城市需求和乡村资源对接。浙江安吉、云南大理涌现多个数字游民社区。部分偏远地区网络基础设施不足仍是挑战。",
    "返乡创业突破1200万人，数字游民经济重塑乡村发展模式。","赵鹏","社会",["返乡","创业"],"editor2","c6",A.REVIEWING,days_ago=1.5,
    reviews=[{"reviewer":"reviewer","level":ReviewLevel.FIRST,"result":ReviewResult.APPROVED,"comment":"选题好，初审通过","offset_days":1}]),
art("元宇宙教育应用试点启动：30所学校探索虚拟课堂",
    "教育部启动元宇宙教育应用试点，选取全国30所重点中小学建设虚拟课堂。学生可通过VR设备参与历史场景重现、化学实验模拟等沉浸式学习。首期投入5亿元，预计覆盖5万名学生。专家提醒需关注青少年视力和心理健康。",
    "30所学校试点元宇宙课堂，首期投入5亿元覆盖5万名学生。","刘洋","科技",["元宇宙","教育"],"editor1","c5",A.REVIEWING,days_ago=1,
    reviews=[{"reviewer":"reviewer2","level":ReviewLevel.FIRST,"result":ReviewResult.APPROVED,"comment":"创新性强","offset_days":0.5}]),
art("星闪技术产业联盟成立：华为牵头共建万物互联新标准",
    "星闪技术产业联盟今日成立，华为、OPPO、比亚迪等200+企业加入。星闪相比蓝牙功耗降低60%、速率提升6倍，将首先在智能汽车和全屋智能领域落地。联盟计划2027年实现10亿设备接入。",
    "华为牵头成立星闪联盟，200+企业共建短距通信新标准。","王磊","科技",["星闪","通信"],"reporter3","c13",A.REVIEWING,days_ago=0.5,
    reviews=[{"reviewer":"reviewer","level":ReviewLevel.FIRST,"result":ReviewResult.APPROVED,"comment":"技术细节准确","offset_days":0.3}]),
art("个人养老金制度扩围：灵活就业者纳入参保范围",
    "人社部发布通知，个人养老金制度将灵活就业人员纳入参保范围，覆盖外卖骑手、网约车司机等2亿新就业形态劳动者。年缴费上限从1.2万提至2万元，税收优惠政策同步优化。",
    "灵活就业人员纳入个人养老金，覆盖2亿新就业形态劳动者。","陈思","财经",["养老","政策"],"reporter4","c3",A.REVIEWING,days_ago=0.2,
    reviews=[{"reviewer":"reviewer","level":ReviewLevel.FIRST,"result":ReviewResult.NEED_REVISION,"comment":"建议补充专家观点","offset_days":0.1}]),

# ==================== 待审核 7 篇 ====================
art("河南暴雨预警系统升级：AI提前72小时精准预报",
    "河南省气象局联合华为云部署新一代AI暴雨预警系统，实现提前72小时精准预报，准确率达91%。系统融合卫星遥感、地基雷达和传感器网络等数据源。去年试运行期间成功预警暴雨57次，转移群众120万人次。",
    "AI暴雨预警提前72小时，准确率91%，去年成功预警57次。","张凯","科技",["AI","气象"],"reporter1","c5",A.PENDING_REVIEW,days_ago=0.5),
art("粤港澳大湾区「跨境理财通3.0」正式启动",
    "跨境理财通3.0正式启动，个人投资额度从100万提至300万元人民币，产品范围扩大至私募基金和REITs。首批参与试点金融机构达150家。预计带动大湾区居民跨境资产配置规模突破1万亿元。",
    "跨境理财通3.0启动，个人额度提至300万，产品扩至私募基金。","李然","财经",["大湾区","理财"],"reporter2","c14",A.PENDING_REVIEW,days_ago=0.4),
art("月球科研站方案公布：2030年前建成首个永久设施",
    "中国探月工程总设计师披露，国际月球科研站将于2030年前建成首个永久设施。选址月球南极沙克尔顿环形山，利用极区水冰资源实现就地燃料补给。俄罗斯、巴基斯坦等12个国家已确认参与。",
    "月球科研站2030前建成首永久设施，选址南极沙克尔顿环形山。","王磊","科技",["航天","月球"],"reporter3","c15",A.PENDING_REVIEW,days_ago=0.3),
art("社区食堂全国推广：日均服务老年人突破2000万人次",
    "民政部数据，全国社区食堂已超5万家，日均服务老年人突破2000万人次。北京、上海实现15分钟养老助餐圈全覆盖。每餐补贴3-8元，长者满意度达96%。运营模式已从政府补贴转向多元化社会参与。",
    "全国社区食堂超5万家，日均服务老人2000万，15分钟助餐圈全覆盖。","赵鹏","社会",["养老","民生"],"editor2","c6",A.PENDING_REVIEW,days_ago=0.3),
art("北京中轴线申遗成功两周年：文旅融合焕新古都",
    "北京中轴线申遗成功两周年，沿线15处遗产点共接待游客超1.2亿人次。数字中轴线项目上线，运用AR还原明清历史场景。文旅部表示将推进申遗成果向文化IP转化，打造世界级文化体验目的地。",
    "中轴线申遗两周年接待游客1.2亿，数字中轴AR还原历史场景。","刘洋","文化",["申遗","文旅"],"editor1","c12",A.PENDING_REVIEW,days_ago=0.2),
art("外来入侵物种防治年度报告：红火蚁扩散得到遏制",
    "农业农村部发布外来入侵物种防治年度报告。红火蚁扩散速度下降40%，已从防治转为常态化监测。同时发现新入侵物种鳄雀鳝8处，已启动紧急清除。我国已建立覆盖全国的生物入侵预警网络。",
    "红火蚁扩散速度下降40%，鳄雀鳝新入侵8处，生物入侵预警全国覆盖。","小明","社会",["生态","防治"],"user","c12",A.PENDING_REVIEW,days_ago=0.2),
art("海洋牧场建设加速：年产值突破5000亿元",
    "农业农村部数据，全国国家级海洋牧场示范区已达200个，年产值突破5000亿元。智能化养殖装备覆盖率70%，深远海养殖平台「深蓝1号」实现三文鱼规模化养殖。海洋牧场碳汇交易试点同步启动。",
    "国家级海洋牧场200个，年产值5000亿，深远海养殖平台规模化。","小明","财经",["海洋","养殖"],"user","c14",A.PENDING_REVIEW,days_ago=0.1),

# ==================== 已拒绝 3 篇 ====================
art("某地治污工程疑存质量问题：现场调查发现多处隐患",
    "近日有群众反映某市污水处理厂二期工程存在质量问题。记者实地走访发现部分管道接口渗漏，建筑钢筋锈蚀。记者多次联系当地环保局和水务集团未获回应。承包商承认施工过程中存在赶工期情况。",
    "某地污水处理厂曝质量问题，排污管道接口渗漏。","赵鹏","社会",["治污","调查"],"editor2",None,A.REJECTED,days_ago=10,
    reviews=[{"reviewer":"reviewer","level":ReviewLevel.FIRST,"result":ReviewResult.REJECTED,"comment":"缺少多方信源核实，调查不够深入","offset_days":10}]),
art("疫苗第三针加强效果存疑？专家观点两极分化",
    "关于新冠疫苗第三针加强效果的争议持续发酵。部分专家认为加强针保护力在6个月后大幅衰减。另一派专家指出现有数据不足以支撑「疫苗疲劳」结论。卫健委表示将持续监测真实世界数据。",
    "新冠疫苗第三针加强效果引发争议，专家观点两极分化。","小明","社会",["疫苗","争议"],"user",None,A.REJECTED,days_ago=8,
    reviews=[{"reviewer":"reviewer2","level":ReviewLevel.FIRST,"result":ReviewResult.REJECTED,"comment":"标题有误导性，内容引用的争议缺乏权威数据支撑，退回修改","offset_days":8}]),
art("某品牌新能源汽车自燃事件：车主集体维权",
    "某品牌新能源汽车连续发生3起自燃事件，涉及不同车型。50余位车主联名向市场监管总局投诉。厂家表示自燃原因系电池供应商批次质量问题，已启动召回。目前双方在赔偿方案上存在分歧。",
    "某品牌新能源车连续3起自燃，50余车主集体维权。","小明","财经",["新能源","维权"],"user",None,A.REJECTED,days_ago=6,
    reviews=[{"reviewer":"reviewer3","level":ReviewLevel.FIRST,"result":ReviewResult.REJECTED,"comment":"缺少厂家官方回应和第三方检测报告，调查不够全面","offset_days":6}]),

# ==================== 草稿 8 篇 ====================
art("2026年全国GDP增速：一季度数据超预期", "国家统计局公布2026年一季度GDP同比增长5.8%，高于市场预期的5.2%...", "一季度GDP增长5.8%超预期", "陈思","财经",["GDP"],"reporter4",None,A.DRAFT,days_ago=3),
art("华为发布新一代鸿蒙PC操作系统", "华为今日发布鸿蒙PC操作系统，实现手机-平板-PC全场景无缝协同...", "华为鸿蒙PC系统发布，全场景协同", "王磊","科技",["鸿蒙"],"reporter3",None,A.DRAFT,days_ago=2),
art("短视频平台算法治理新规出台", "国家网信办发布短视频算法推荐管理规定，要求平台公开推荐逻辑...", "网信办要求短视频平台公开算法逻辑", "刘洋","科技",["短视频","监管"],"editor1",None,A.DRAFT,days_ago=2),
art("黄河流域生态保护成效评估报告发布", "生态环境部发布黄河流域生态保护五年评估报告，水质优良比例提升至78%...", "黄河水质优良比例提升至78%", "赵鹏","社会",["黄河","生态"],"editor2",None,A.DRAFT,days_ago=1),
art("中欧班列开行突破10万列 贸易额创历史新高", "中欧班列累计开行突破10万列，2026年贸易额达3000亿美元...", "中欧班列突破10万列，贸易额3000亿美元", "李然","财经",["中欧班列"],"reporter2",None,A.DRAFT,days_ago=1),
art("老年人数字鸿沟调查：手机App适老化改造仍不足", "中国老龄协会调查显示，仅35%老年用户能熟练使用智能手机...", "仅35%老年人熟练使用手机，适老化待改善", "小明","社会",["老龄化","数字鸿沟"],"user",None,A.DRAFT,days_ago=0.5),
art("全球首个火星样本返回任务筹备中", "国家航天局透露，火星样本返回任务已进入工程研制阶段...", "中国火星样本返回任务进入工程研制", "王磊","科技",["火星","航天"],"reporter3",None,A.DRAFT,days_ago=0.5),
art("新疆棉纺织产业智能化转型提速", "新疆棉纺行业大规模引入AI质检和自动化生产线，效率提升50%...", "新疆棉纺AI质检效率提升50%", "小明","科技",["纺织","AI"],"user",None,A.DRAFT,days_ago=0.3),

# ==================== 已归档 2 篇 ====================
art("2025年度十大科技新闻回顾", "2025年是科技领域里程碑式的一年。从DeepSeek大模型横空出世到嫦娥八号采样返回，从脑机接口临床突破到室温超导争议...", "2025科技新闻年度盘点", "刘洋","科技",["回顾"],"editor1",None,A.ARCHIVED,days_ago=45,
    reviews=[{"reviewer":"reviewer3","level":ReviewLevel.FIRST,"result":ReviewResult.APPROVED,"comment":"时间敏感内容，建议归档","offset_days":44}]),
art("2025年全球气候行动年度回顾", "2025年全球平均气温再创新高，极端天气事件频发。但清洁能源投资首次突破2万亿美元...", "2025全球气候行动回顾", "张凯","国际",["回顾","气候"],"reporter1",None,A.ARCHIVED,days_ago=40,
    reviews=[{"reviewer":"reviewer2","level":ReviewLevel.FIRST,"result":ReviewResult.APPROVED,"comment":"已归档","offset_days":39}]),

# ============================================================
# 4. 写入数据库
# ============================================================
print(f"\n共 {len(articles_raw)} 篇稿件待写入...")

article_objs = []
for a in articles_raw:
    creator = users[a["creator"]]
    clue_id = clues[a["clue"]].id if a["clue"] else None
    pub_at = dt(a["days_ago"]) if a["status"] == A.PUBLISHED else None

    art_obj = Article(
        title=a["title"], content=a["content"], abstract=a["abstract"],
        author=a["author"], category=a["category"], tags=a["tags"],
        status=a["status"], creator_id=creator.id, clue_id=clue_id,
        published_at=pub_at, images=[], version=1,
        article_metadata={"source":"采编系统"},
        created_at=dt(a["days_ago"]), updated_at=dt(a["days_ago"]),
    )
    db.add(art_obj); db.flush()
    article_objs.append((art_obj, a))
db.commit()

# 审核记录 + 评论
for art_obj, a in article_objs:
    for r in a.get("reviews", []):
        rv_user = users[r["reviewer"]]
        db.add(Review(article_id=art_obj.id, reviewer=rv_user.full_name,
                       level=r["level"], result=r["result"],
                       comment=r["comment"],
                       reviewed_at=dt(r["offset_days"])))
    for c in a.get("comments", []):
        db.add(ArticleComment(article_id=art_obj.id, author_name=c["author"],
                               content=c["content"], created_at=dt(a["days_ago"], random.randint(-5,5))))
db.commit()

# ============================================================
# 5. 汇总
# ============================================================
sc_map = {"draft":"草稿","pending_review":"待审核","reviewing":"审核中",
          "approved":"已通过","rejected":"已拒绝","published":"已发布","archived":"已归档"}

print("\n" + "="*60)
print("              种子数据填充完毕")
print("="*60)
print(f"\n📊 统计:")
print(f"  👤 用户:    {db.query(User).count()} 人 (投稿 {sum(1 for u in users.values() if u.role==UserRole.USER)} / 审核 {sum(1 for u in users.values() if u.role==UserRole.REVIEWER)})")
print(f"  🔍 线索:    {db.query(NewsClue).count()} 条")
print(f"  📝 稿件:    {db.query(Article).count()} 篇")

from collections import Counter
sc = Counter()
for a in db.query(Article).all():
    sc[a.status.value] += 1
for k,v in sorted(sc.items()):
    print(f"     {sc_map.get(k,k):8} {'█'*v} {v}")
print(f"  ✅ 审核记录: {db.query(Review).count()} 条")
print(f"  💬 评论:     {db.query(ArticleComment).count()} 条")

print(f"\n🔑 登录账号:")
for uname,_,pw,full,_,role in _u:
    print(f"  {full:6} ({role.value:8})  {uname:12} / {pw}")

db.close()
print("\n✅ http://localhost:3000 — 审核员登录看全部数据")

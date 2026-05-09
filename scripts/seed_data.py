#!/usr/bin/env python3
"""种子数据脚本：使用 http.client（兼容 Python 3.14 urllib3 问题）"""
import http.client
import json
import random
import time
import sys

HOST = "localhost"
PORT = 8000

def api(method, path, body=None, token=None):
    conn = http.client.HTTPConnection(HOST, PORT, timeout=15)
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body_bytes = json.dumps(body).encode() if body else None
    conn.request(method, path, body=body_bytes, headers=headers)
    r = conn.getresponse()
    data = r.read().decode()
    conn.close()
    return r.status, data

USERS = [
    ("zhangsan", "pass123456", "zhangsan@test.com", "张三"),
    ("lisi", "pass123456", "lisi@test.com", "李四"),
    ("wangwu", "pass123456", "wangwu@test.com", "王五"),
    ("zhaoliu", "pass123456", "zhaoliu@test.com", "赵六"),
    ("sunqi", "pass123456", "sunqi@test.com", "孙七"),
    ("zhouba", "pass123456", "zhouba@test.com", "周八"),
    ("wujiu", "pass123456", "wujiu@test.com", "吴九"),
    ("zhengshi", "pass123456", "zhengshi@test.com", "郑十"),
]
REGISTERED = []
CATS = ["科技", "财经", "社会", "教育", "健康", "体育", "娱乐", "国际"]

def gen_content(title, cat, author_nick):
    paragraphs = [
        f"# {title}\n\n## 行业背景\n\n当前，{cat}行业正处于快速发展期。随着技术创新和市场需求的持续增长，行业格局正在发生深刻变化。从传统模式向数字化、智能化转型已成为不可逆转的趋势。\n\n在过去的一年中，我们观察到多个重要的行业信号。政策层面的支持力度不断加大，为行业发展提供了良好的外部环境。技术创新驱动下的新产品和新服务层出不穷，极大地丰富了市场供给。消费者需求的升级也在倒逼行业参与者不断提升自身竞争力。",
        f"## 市场现状\n\n从市场数据来看，{cat}行业在过去一年保持了稳健增长。头部企业继续扩大领先优势，中小企业则通过差异化策略寻找突破口。\n\n线上渠道正在成为主流，传统线下渠道面临转型压力。数字化转型已经不是选择问题，而是生存问题。那些能够快速适应变化的企业，正在获得越来越大的市场份额。\n\n值得注意的是，消费者对产品品质和服务体验的要求越来越高。在这个信息透明的时代，口碑和品牌信誉成为企业最重要的资产。",
        f"## 技术驱动\n\n技术进步是推动{cat}行业变革的核心力量。人工智能、大数据、云计算等新一代信息技术正在深度渗透到行业的各个环节。\n\n在研发环节，AI辅助设计和仿真技术大幅缩短了产品开发周期。在生产环节，智能工厂和工业互联网提升了生产效率和产品质量。在营销环节，精准推荐和个性化服务提升了用户体验和转化率。\n\n这些技术的应用不仅降低了成本、提升了效率，更重要的是创造了全新的商业模式和价值主张，为行业带来了前所未有的发展机遇。",
        f"## 挑战与应对\n\n尽管前景广阔，{cat}行业也面临不少挑战。人才短缺是普遍存在的问题，尤其是既懂技术又懂业务的高端复合型人才更是稀缺。\n\n行业标准不完善、监管政策滞后也是需要解决的问题。在快速发展的行业中，标准往往落后于实践，这给企业带来了不确定性。\n\n面对这些挑战，业内专家建议企业应当加大研发投入，注重人才培养和引进，同时积极参与行业标准的制定和生态建设，共同推动行业健康发展。",
        f"## 未来展望\n\n展望未来，{cat}行业将继续保持快速发展态势。预计未来三到五年，行业规模将实现显著增长。\n\n新兴技术和商业模式将不断涌现，跨界融合将成为常态。与此同时，行业竞争也将更加激烈，优胜劣汰将进一步加速。\n\n对于从业者而言，这既是机遇也是挑战。只有持续学习、不断创新，才能在这场变革中立于不败之地。",
        f"## 结语\n\n{cat}行业的未来发展充满无限可能。从宏观政策到微观创新，各方面因素都在推动行业向前发展。\n\n我们期待看到更多的创新和突破，也相信在各方的共同努力下，行业将迎来更加繁荣的明天。\n\n（本文由记者{author_nick}采写，不代表平台立场）",
    ]
    selected = random.sample(paragraphs, random.randint(4, 5))
    content = "\n\n".join(selected)
    abstract = f"本文深入分析了{cat}行业的最新发展动态，从行业背景、市场现状、技术驱动、挑战应对和未来展望五个维度进行了系统解读。"
    return content, abstract


def main():
    print("=" * 50)
    print("第一步：注册用户")
    print("=" * 50)

    for username, pwd, email, nick in USERS:
        status, data = api("POST", "/api/auth/register", {
            "username": username, "email": email, "password": pwd, "nickname": nick
        })
        if status == 200:
            REGISTERED.append((username, pwd, nick))
            print(f"  ✅ {username} ({nick})")
        else:
            # 尝试登录
            login_data = f"username={username}&password={pwd}"
            conn = http.client.HTTPConnection(HOST, PORT, timeout=10)
            conn.request("POST", "/api/auth/login", body=login_data,
                         headers={"Content-Type": "application/x-www-form-urlencoded"})
            r = conn.getresponse()
            resp = r.read().decode()
            conn.close()
            if r.status == 200:
                REGISTERED.append((username, pwd, nick))
                print(f"  ⚠️  {username} 已存在，可登录")
            else:
                print(f"  ❌ {username}: {status} {data[:60]}")
        time.sleep(0.3)

    print(f"\n可用用户: {len(REGISTERED)}")

    # ===== 登录拿 token =====
    print("\n" + "=" * 50)
    print("第二步：登录")
    print("=" * 50)

    tokens = {}
    for username, pwd, nick in REGISTERED:
        conn = http.client.HTTPConnection(HOST, PORT, timeout=10)
        conn.request("POST", "/api/auth/login",
                      body=f"username={username}&password={pwd}",
                      headers={"Content-Type": "application/x-www-form-urlencoded"})
        r = conn.getresponse()
        resp = r.read().decode()
        conn.close()
        if r.status == 200:
            tokens[username] = (json.loads(resp)["access_token"], nick)
            print(f"  ✅ {username} 登录成功")
        else:
            print(f"  ❌ {username}: {r.status}")
        time.sleep(0.2)

    if not tokens:
        print("无可用 token，退出")
        sys.exit(1)

    # ===== 发布文章 =====
    print("\n" + "=" * 50)
    print("第三步：发布文章（50篇）")
    print("=" * 50)

    article_count = 0
    user_list = list(tokens.items())

    while article_count < 50:
        username, (token, nick) = random.choice(user_list)
        cat = random.choice(CATS)
        topic_idx = article_count % 8
        title = f"{cat}行业深度观察：趋势分析与未来展望（{nick}·第{article_count+1:02d}篇）"
        content, abstract = gen_content(title, cat, nick)
        word_count = len(content)

        article = {
            "title": title,
            "content": content,
            "abstract": abstract,
            "author": nick,
            "category": cat,
            "status": "published",
            "tags": [cat, "行业分析", "深度报道"],
        }
        status, data = api("POST", "/api/articles", article, token)
        if status == 200:
            article_count += 1
            print(f"  [{article_count:02d}/50] ✅ {title[:30]:<30s} {username:<8s} {cat:<4s} {word_count}字")
        else:
            print(f"  [{article_count+1:02d}/50] ❌ {status} {data[:60]}")
            time.sleep(1)
        time.sleep(0.15)

    print(f"\n{'=' * 50}")
    print(f"🎉 完成！{len(tokens)} 个用户，{article_count} 篇文章")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()

# 测试账号数据

> 生成时间: 2026-05-12 11:45:28
> 统一密码: `Test123456`
> 密码加密: bcrypt (优先) / sha256 (回退)

## 特殊账号

| 角色 | 用户名 | 密码 | 昵称 | 邮箱 |
|------|--------|------|------|------|
| 管理员 | `admin` | `Test123456` | 系统管理员 | admin@news-editor.com |
| 审核员 | `reviewer` | `Test123456` | 审核编辑-张明 | reviewer@news-editor.com |

## 普通用户（记者/编辑）

| 序号 | 用户名 | 昵称 | 角色 | 邮箱 |
|------|--------|------|------|------|
| 1 | `qiangzhong34` | 李飞 | reporter | qiangzhong34@sina.com |
| 2 | `tmeng87` | 奉玉华 | reporter | tmeng87@163.com |
| 3 | `xiuyingding39` | 李刚 | reporter | xiuyingding39@163.com |
| 4 | `li0526` | 李英 | reporter | li0526@gmail.com |
| 5 | `jieli65` | 王丹丹 | reporter | jieli65@sina.com |
| 6 | `heqiang61` | 邓林 | reporter | heqiang61@qq.com |
| 7 | `ilu27` | 黄建军 | reporter | ilu27@163.com |
| 8 | `dwen50` | 赵玉华 | reporter | dwen50@sina.com |
| 9 | `wdeng62` | 孟璐 | reporter | wdeng62@gmail.com |
| 10 | `wei2829` | 周强 | reporter | wei2829@sina.com |
| 11 | `mingqiao82` | 文明 | reporter | mingqiao82@sina.com |
| 12 | `qlai25` | 宋波 | reporter | qlai25@gmail.com |
| 13 | `xiaofang89` | 王帅 | reporter | xiaofang89@163.com |
| 14 | `gang9986` | 韩明 | reporter | gang9986@qq.com |
| 15 | `qiang4792` | 李冬梅 | reporter | qiang4792@163.com |
| 16 | `xiulan4679` | 陈玉华 | reporter | xiulan4679@qq.com |
| 17 | `zouyan58` | 徐华 | reporter | zouyan58@163.com |
| 18 | `sluo91` | 刘玉梅 | reporter | sluo91@gmail.com |
| 19 | `taoqian19` | 刘涛 | reporter | taoqian19@qq.com |
| 20 | `xuqiang18` | 孟秀荣 | reporter | xuqiang18@qq.com |

---

## 使用说明

### 登录

- 所有账号密码均为 `Test123456`
- 管理员: `admin`
- 审核员: `reviewer`
- 普通用户: 见上表，任选一个

### 重新生成数据

```bash
cd backend
python database_init/database_init.py --all
```

"""viral_collection/service.py —— 爆款收集 CRUD + AI 截图解析

收集抖音/快手/红果等平台爆款，截图存 DATA_ROOT/data/viral_images/{id}/，库只存相对路径数组(JSON)。
AI 解析复用 common/ai.chat（多图 → 视觉模型 → 结构化 JSON，防御性解析）。
"""

import json
import re
import shutil
import threading
from pathlib import Path

from common import db

IMAGE_DIR = 'viral_images'
ALLOWED_EXT = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'}


def _conn():
    return db.get_conn()


def _img_dir(iid):
    d = db.DATA_DIR / IMAGE_DIR / str(iid)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _parse_arr(v):
    if isinstance(v, list):
        return v
    if not v:
        return []
    try:
        a = json.loads(v)
        return a if isinstance(a, list) else []
    except Exception:
        return []


def _dump_arr(arr):
    return json.dumps(arr, ensure_ascii=False)


def _force_unlink(fp, tries=4):
    """删单个文件（带极短退避，最长约 1 秒）。

    Windows 上图片被界面加载过之后，系统实时扫描（Defender / 缩略图缓存）
    会短暂持有句柄，直接 unlink 会 PermissionError。这里做极短退避重试，
    仍失败就改名成 .trash 交给 cleanup_orphans 后续清理，避免出现
    「库里删了、磁盘还在」的残留。必须是「快」的——删除路径不该长时间阻塞。

    注意：已经是 .trash 的文件不再二次改名（避免 .trash.trash 无限叠加），
    只尽力 unlink，失败就留给下一轮 cleanup_orphans。
    """
    import time
    fn = str(fp)
    already = fn.endswith('.trash')
    for i in range(tries):
        try:
            fp.unlink()
            return True
        except FileNotFoundError:
            return True
        except Exception:
            time.sleep(0.1 * (i + 1))
    if not already:
        try:
            fp.rename(fp.with_suffix(fp.suffix + '.trash'))
        except Exception:
            pass
    return False


def _force_rmtree(folder, tries=3):
    """删整个截图目录：先逐个删文件（带重试），再删空目录。删不掉就留给孤儿清理。"""
    import time
    if not folder.exists():
        return True
    for p in folder.rglob('*'):
        if p.is_file():
            _force_unlink(p)
    for i in range(tries):
        try:
            shutil.rmtree(folder)
            return True
        except Exception:
            time.sleep(0.2 * (i + 1))
    return False


def cleanup_orphans():
    """顺手清理截图目录里的垃圾（best-effort，任何失败都不影响主流程）：
      1) 上次删不掉、改名成 .trash 的文件
      2) 记录已删除但目录还在的孤儿目录
      3) 空目录
    在列表接口里调用，用户下次打开页面残留就自动消失。
    """
    root = db.DATA_DIR / IMAGE_DIR
    if not root.exists():
        return
    try:
        conn = _conn()
        try:
            alive = {str(r['id']) for r in conn.execute("SELECT id FROM viral_collection").fetchall()}
        finally:
            conn.close()
        for sub in root.iterdir():
            if not sub.is_dir():
                continue
            # 先清掉上次改名留下的 .trash：只做一次快速尝试，绝不做长退避——
            # cleanup_orphans 跑在列表接口里，必须快、不能阻塞页面。删不掉就留给下一轮。
            for f in sub.glob('*.trash'):
                try:
                    f.unlink()
                except Exception:
                    pass
            if sub.name not in alive:
                _force_rmtree(sub)
                continue
            try:
                if not any(sub.iterdir()):
                    sub.rmdir()
            except Exception:
                pass
    except Exception:
        pass


# ---------- 列表 / 详情 ----------
def list_items(platform='', category='', keyword='', on_hongguo=None):
    # 清理孤儿目录 / .trash 放到后台线程：删除在某些环境（回收站路由、杀软扫描）
    # 下可能很慢甚至失败，绝不该阻塞列表接口、拖慢页面。
    try:
        threading.Thread(target=cleanup_orphans, daemon=True).start()
    except Exception:
        pass
    sql = "SELECT * FROM viral_collection WHERE 1=1"
    params = []
    if platform:
        sql += " AND platform=?"
        params.append(platform)
    if category:
        sql += " AND category=?"
        params.append(category)
    if on_hongguo is not None:
        sql += " AND on_hongguo=?"
        params.append(int(on_hongguo))
    if keyword:
        like = f'%{keyword}%'
        sql += (" AND (title LIKE ? OR username LIKE ? OR douyin_id LIKE ? OR drama_name LIKE ? "
                "OR original_novel LIKE ? OR tags LIKE ? OR note LIKE ?)")
        params.extend([like] * 7)
    sql += " ORDER BY id DESC"
    conn = _conn()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_item(iid):
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM viral_collection WHERE id=?", (iid,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


_FIELDS = [
    'platform', 'category', 'title', 'link', 'drama_name', 'aliases', 'original_novel',
    'username', 'douyin_id', 'following', 'followers', 'works_count', 'bio', 'homepage_link',
    'likes', 'favorites', 'play_count', 'comment_count', 'share_count', 'on_hongguo',
    'learn_from', 'novel_clue', 'tags', 'novel_tags', 'note',
]


def _extract(data):
    out = {}
    for k in _FIELDS:
        if k in data:
            v = data[k]
            if k == 'on_hongguo':
                out[k] = int(v or 0)
            else:
                out[k] = '' if v is None else str(v)
    return out


def _find_title_dup(title, exclude_id=None):
    """按标题精确查重（编辑时排除自身）。返回已存在的 id，没有则 None。"""
    if not title or not str(title).strip():
        return None
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT id FROM viral_collection WHERE title=? AND id!=? LIMIT 1",
            (str(title).strip(), exclude_id or 0),
        ).fetchone()
        return row['id'] if row else None
    finally:
        conn.close()


def create_item(data):
    d = _extract(data)
    if not d.get('title', '').strip():
        raise ValueError('标题不能为空')
    dup = _find_title_dup(d.get('title'), None)
    if dup:
        raise ValueError(f'标题『{d["title"]}』已存在（条目 #{dup}），请改名后再保存')
    cols = list(d.keys())
    placeholders = ','.join('?' for _ in cols)
    conn = _conn()
    try:
        cur = conn.execute(
            f"INSERT INTO viral_collection({','.join(cols)}) VALUES({placeholders})",
            [d[c] for c in cols],
        )
        conn.commit()
        return get_item(cur.lastrowid)
    finally:
        conn.close()


def update_item(iid, data):
    existing = get_item(iid)
    if not existing:
        raise ValueError('记录不存在')
    d = _extract(data)
    if not d:
        return existing
    if d.get('title', '').strip():
        dup = _find_title_dup(d.get('title'), iid)
        if dup:
            raise ValueError(f'标题『{d["title"]}』已存在（条目 #{dup}），请改名后再保存')
    set_clause = ','.join(f'{c}=?' for c in d)
    conn = _conn()
    try:
        conn.execute(
            f"UPDATE viral_collection SET {set_clause}, updated_at=datetime('now','localtime') WHERE id=?",
            [d[c] for c in d] + [iid],
        )
        conn.commit()
        return get_item(iid)
    finally:
        conn.close()


def delete_item(iid):
    conn = _conn()
    try:
        conn.execute("DELETE FROM viral_collection WHERE id=?", (iid,))
        conn.commit()
    finally:
        conn.close()
    _force_rmtree(db.DATA_DIR / IMAGE_DIR / str(iid))


# ---------- 截图 ----------
def add_screenshots(iid, files):
    item = get_item(iid)
    if not item:
        raise ValueError('记录不存在')
    folder = _img_dir(iid)
    existing = _parse_arr(item['screenshots'])
    for f in files:
        raw = f.get('content') or b''
        fname = f.get('filename') or 'screenshot.png'
        base = re.sub(r'[^\w\u4e00-\u9fa5.-]', '_', Path(fname).stem) or 'shot'
        ext = Path(fname).suffix.lower()
        if ext not in ALLOWED_EXT:
            ext = '.png'
        target = folder / f"{base}{ext}"
        n = 1
        while target.exists():
            target = folder / f"{base}_{n}{ext}"
            n += 1
        target.write_bytes(raw)
        existing.append(f"{IMAGE_DIR}/{iid}/{target.name}")
    conn = _conn()
    try:
        conn.execute(
            "UPDATE viral_collection SET screenshots=?, updated_at=datetime('now','localtime') WHERE id=?",
            (_dump_arr(existing), iid),
        )
        conn.commit()
    finally:
        conn.close()
    return get_item(iid)


def delete_screenshot(iid, filename):
    item = get_item(iid)
    if not item:
        raise ValueError('记录不存在')
    existing = _parse_arr(item['screenshots'])
    rel = f"{IMAGE_DIR}/{iid}/{filename}"
    new_list = [x for x in existing if x != rel]
    fp = db.DATA_DIR / rel
    if fp.exists():
        _force_unlink(fp)
    conn = _conn()
    try:
        conn.execute(
            "UPDATE viral_collection SET screenshots=?, updated_at=datetime('now','localtime') WHERE id=?",
            (_dump_arr(new_list), iid),
        )
        conn.commit()
    finally:
        conn.close()
    return get_item(iid)


def get_image_file(rel):
    fp = (db.DATA_DIR / rel).resolve()
    root = (db.DATA_DIR / IMAGE_DIR).resolve()
    if fp != root and root not in fp.parents:
        raise ValueError('非法路径')
    if not fp.exists():
        raise FileNotFoundError('文件不存在')
    return fp


# ---------- 小说平台搜索站点（用户可自定义） ----------
# 只保存「搜索页 URL 模板」，点击时由桌面壳用系统浏览器打开，人工查看结果；
# 不做任何自动抓取，避免触碰第三方站点的反爬与合规红线。
CONFIG_KEY = 'viral_search_sites'
DEFAULT_SITES = [
    {'name': '番茄小说', 'url': 'https://fanqienovel.com/search?query={q}'},
    {'name': '七猫小说', 'url': 'https://www.qimao.com/search/?wd={q}'},
    {'name': '起点中文网', 'url': 'https://www.qidian.com/so/{q}.html'},
    {'name': '微信读书', 'url': 'https://weread.qq.com/web/search?keyword={q}'},
    {'name': '百度搜一下', 'url': 'https://www.baidu.com/s?wd={q}'},
]


def get_search_sites():
    raw = db.get_config(CONFIG_KEY)
    if not raw:
        return list(DEFAULT_SITES)
    try:
        arr = json.loads(raw)
        return arr if isinstance(arr, list) else list(DEFAULT_SITES)
    except Exception:
        return list(DEFAULT_SITES)


def save_search_sites(sites):
    clean = []
    for s in sites or []:
        name = str(s.get('name') or '').strip()
        url = str(s.get('url') or '').strip()
        if name and url:
            clean.append({'name': name, 'url': url})
    db.set_config(CONFIG_KEY, json.dumps(clean, ensure_ascii=False), '爆款收集：小说平台搜索站点')
    return clean


# ---------- AI 解析截图 ----------
# 视频归属分类（用户指定清单，AI 优先匹配）
_CATEGORY_PRESET = ['AI动画', 'AI漫剧', 'AI漫画', '沙雕动画', '萌宠动画', '原创漫剧', '真人短剧', '图文', '其他']
# 视频标签：题材 + 元素/风格（核心预设，AI 优先匹配）
_VIDEO_TAG_PRESET = ['逆袭', '重生', '甜宠', '虐恋', '古风', '现代', '悬疑', '言情', '科幻', '武侠', '玄幻',
                     '霸总', '马甲', '打脸', '追妻火葬场', '反转', '脑洞', '沙雕', '搞笑', '催泪', 'AI配音', '二创', '混剪']
# 小说标签（参考番茄/书旗/起点/QQ阅读，核心预设，AI 优先匹配）
_NOVEL_TAG_PRESET = ['玄幻', '奇幻', '武侠', '仙侠', '都市', '历史', '科幻', '悬疑', '古代言情', '现代言情',
                     '重生', '穿越', '系统', '末世', '修仙', '种田', '宫斗', '宅斗', '权谋', '复仇', '甜宠',
                     '豪门', '娱乐圈', '电竞', '异能', '团宠', '萌宝', '先婚后爱', '破镜重圆', '病娇', '腹黑']

_PARSE_PROMPT = """你是一个专业的短视频爆款数据分析助手。下面是一组从抖音/快手/红果等平台截取的图片（可能包含视频播放页、作者主页、评论区）。请仔细识别截图中的文字与数字，提取结构化信息，并以 JSON 返回，字段如下：
{
  "platform": "平台名，如 抖音 / 快手 / 红果 / 视频号 / B站",
  "category": "视频归属分类，优先从以下清单选一个：AI动画 / AI漫剧 / AI漫画 / 沙雕动画 / 萌宠动画 / 原创漫剧 / 真人短剧 / 图文 / 其他；清单没有再自由概括",
  "title": "视频或作品标题",
  "link": "视频链接（抖音短链如 https://v.douyin.com/xxxxx，或分享链接，或页面地址栏里的URL；没有则空字符串）",
  "dramaName": "剧名（若与标题不同或可从标题/话题推断）",
  "username": "作者 / 账号名",
  "douyinId": "抖音号 / 作者主页 ID（主页截图里『抖音号：』后面的数字或字母组合）",
  "following": "作者关注数（保留原样，如 233；没有则空字符串）",
  "followers": "作者粉丝数（保留原样，如 2.1w、3456；没有则空字符串）",
  "worksCount": "作者作品数（保留原样，如 24、156；没有则空字符串）",
  "bio": "作者主页简介 / 签名（一段文字；没有则空字符串）",
  "homepageLink": "作者主页链接（若截图里能看到主页URL；没有则空字符串）",
  "likes": "点赞数（保留原样，如 1.2w、3456）",
  "favorites": "收藏数（保留原样）",
  "playCount": "播放量（若页面可见，如 12.5w、1.2亿；否则空字符串）",
  "tags": ["视频内容标签，优先从以下题材/元素选：逆袭、重生、甜宠、虐恋、古风、现代、悬疑、言情、科幻、武侠、玄幻、霸总、马甲、打脸、追妻火葬场、反转、脑洞、沙雕、搞笑、催泪、AI配音、二创、混剪；可补充其他贴切标签"],
  "novelTags": ["疑似/相关小说标签，优先从以下选：玄幻、奇幻、武侠、仙侠、都市、历史、科幻、悬疑、古代言情、现代言情、重生、穿越、系统、末世、修仙、种田、宫斗、宅斗、权谋、复仇、甜宠、豪门、娱乐圈、电竞、异能、团宠、萌宝、先婚后爱、破镜重圆、病娇、腹黑；可补充其他贴切标签"],
  "onHongguo": false,
  "novelKeywords": ["从主页简介 / 置顶评论 / 评论区 / 视频标题提取的疑似原作小说名、主角名或关键词；没有则为空数组"],
  "learnFrom": "可借鉴的亮点（一句话，如开头钩子、节奏、画风、配音、评论区互动点）",
  "novelClue": "与小说 / 剧本改编相关的线索（一句话，如『简介提到改编自《xxx》』、『评论区求原著』）"
}
只返回 JSON，不要任何解释或多余文字。若某字段无法从图片获得，填空字符串、空数组或 false。说明：抖音网页版对未登录环境常加载不全，『关注/粉丝/作品数/简介』可能看不到，看清哪个填哪个；是否已上架红果(onHongguo)仅凭截图通常无法判断，默认 false。"""


def _pick_vision_model_id():
    """未指定模型时，优先挑一条 supports_vision=1 且启用中的模型；没有则返回 None（走全局 active）。"""
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT id FROM model_config WHERE is_active=1 AND supports_vision=1 ORDER BY id LIMIT 1"
        ).fetchone()
        return row['id'] if row else None
    finally:
        conn.close()


def parse_screenshots(files, model_config_id=None, rule_id=None):
    if not files:
        raise ValueError('请先提供截图')
    from common import ai
    import traceback
    rule = _resolve_parse_rule(rule_id)
    # 规则自带模型优先；未指定且规则没绑模型，才 fallback 到默认视觉模型
    if not model_config_id and rule.get('model_config_id'):
        model_config_id = rule['model_config_id']
    if not model_config_id:
        model_config_id = _pick_vision_model_id()
    try:
        text = ai.chat(rule['content'], images=files, model_config_id=model_config_id)
    except Exception as e:
        # 把原始异常打印到 stderr，方便通过后端日志定位真实原因（API key/余额/模型名/网络等）
        print('[viral_parse_error]', str(e))
        traceback.print_exc()
        raise RuntimeError(f'AI 解析失败：{e}')
    return _defensive_json(text)


def _resolve_parse_rule(rule_id=None):
    """识别规则四级回退：指定规则(DB) → 菜单=爆款收集的启用规则(DB) → 参考规则文件 → 内置兜底。

    返回 dict {'content': ..., 'model_config_id': ...}，规则自带模型优先于全局默认视觉模型。
    规则内容随 ai_rule 管理（DB / AI调用规则/*.md），避免 prompt 硬编码在前端/功能代码里。
    """
    from ai_rule import service as ai_rule_service
    # 1) 显式指定 rule_id
    if rule_id:
        try:
            r = ai_rule_service.get_ai_rule(rule_id)
            if r and r.get('content'):
                return _rule_payload(r)
        except Exception as e:
            print(f'[viral_parse] 读取指定规则({rule_id})失败，回退:', e)
    # 2) 菜单=爆款收集 的启用规则（DB，用户复制/自建的）
    try:
        for r in ai_rule_service.list_ai_rules(menu='爆款收集', enabled=1) or []:
            if r.get('content'):
                return _rule_payload(r)
    except Exception as e:
        print('[viral_parse] 读取DB规则失败，回退参考规则:', e)
    # 3) 参考规则文件（DATA_ROOT/AI调用规则/爆款收集/截图识别填表规则.md）
    try:
        for ref in ai_rule_service.list_reference_rules() or []:
            if ref.get('menu') == '爆款收集' and ref.get('content'):
                return _rule_payload(ref)
    except Exception as e:
        print('[viral_parse] 读取参考规则失败，回退内置prompt:', e)
    # 4) 内置兜底（保持旧行为）
    return {'content': _PARSE_PROMPT, 'model_config_id': None}


def _rule_payload(r):
    return {'content': r.get('content'), 'model_config_id': r.get('model_config_id')}


def _defensive_json(text):
    if not text:
        raise ValueError('AI 未返回内容')
    s = text.strip()
    s = re.sub(r'^```(?:json)?\s*', '', s)
    s = re.sub(r'\s*```$', '', s)
    start = s.find('{')
    end = s.rfind('}')
    if start == -1 or end == -1 or end < start:
        raise ValueError('AI 未返回可解析的 JSON')
    s = s[start:end + 1]
    try:
        return json.loads(s)
    except Exception as e:
        raise ValueError(f'JSON 解析失败：{e}')

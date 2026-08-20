"""novel_split/splitter.py —— 把一本小说按章节标记切成标准化 .md（纯 py，无引擎/无配置依赖）

支持的拆分单位（仅这些，数字/天/日等不作为拆分单位）：
    章 / 回 / 卷 / 集 / 节

拆分哲学（用户 2026-07-13 拍板）：
    1) 一般只有「一种主格式」。先统计各格式在【行首】的命中数，选最多者
       为主格式；只按主格式切分。
    2) 正文中偶尔写到的「回 / 集 / 卷」等属于正常行文，不当成分隔符，
       因此混合格式【不会各自成章】，只在主格式处切。
    3) 「番外 / 后记 / if线 / 小剧场 / 附录 / 完结感言 / 完本感言」若在行首
       单独出现，独立成一篇 extra 章（输出 第N章.md，正文前标「> 所属：番外」），
       【绝不并入上一章】，也不会误把上一章标成 extra。

输出：projects/<项目名>/00-拆分/第N章.md
"""

import re
import zipfile
import io

CN_NUM = r'[0-9零一二三四五六七八九十百千万亿]+'


def _unit_pat(unit):
    """行首锚定的拆分单位正则。
    允许前面带一个可选的「第M卷/集」容器前缀（如「第1卷 第3章」），
    避免把带卷前缀的章标题漏切；普通「第3章」也照常命中。"""
    prefix = rf'第\s*{CN_NUM}\s*[卷集]\s*'
    return rf'^\s*(?:{prefix})?第\s*{CN_NUM}\s*{unit}'


# 行首锚定的各格式拆分正则（只认真正在行首的章节标记，正文中提及的不算）
CHAPTER_PATTERNS = {
    "章": _unit_pat("章"),
    "回": _unit_pat("回"),
    "节": _unit_pat("节"),
    "卷": rf'^\s*第\s*{CN_NUM}\s*卷',
    "集": rf'^\s*第\s*{CN_NUM}\s*集',
}

# 番外等：行首（允许装饰符号）单独出现 → 独立成 extra 章
# 关键点：必须是「标题式」行（关键词后跟 空格/：/·/—/数字/汉字数字 或行尾），
# 且整行不长（<=40 字），避免把正文中「番外具体内容……」这类散文句误判成章节。
EXTRA_KEYWORDS = ["番外", "后记", "if线", "小剧场", "附录", "完结感言", "完本感言"]
EXTRA_PAT = re.compile(
    r'^\s*[\[\]【】◆●■☆★·\-—~～]*\s*(?:' + "|".join(EXTRA_KEYWORDS) + r')'
    r'(?=[\s：:·—\-~～0-9零一二三四五六七八九十百千万亿两]|$)',
    re.MULTILINE | re.IGNORECASE,
)


# 编译所有章节正则（用于噪音候选排除，行首匹配）
_ALL_CHAPTER_PAT = re.compile(
    '|'.join(f'(?:{p})' for p in CHAPTER_PATTERNS.values()),
    re.MULTILINE,
)


def _is_heading_line(text, start):
    """番外等关键词所在行是否为「标题式」（不长，像章节名而非散文句）。"""
    nl = text.find('\n', start)
    line = text[start:nl] if nl != -1 else text[start:]
    return len(line.strip()) <= 40


def _title_line_and_end(text: str, match_start: int, match_end: int):
    """返回（完整标题行, 行尾位置+1），正文从 line_end 开始。
    
    匹配旧 00-split_novel.py 的 _title_and_end()。
    注意：match_start 可能指向 \n（^\s* 消费），所以从 match_end 找行尾。"""
    # 行首：match_start 左侧最近的 \n
    line_start = text.rfind('\n', 0, match_start)
    line_start = line_start + 1 if line_start != -1 else 0
    # 行尾：从 match_end 往后找 \n
    line_end = text.find('\n', match_end)
    if line_end == -1:
        line_end = len(text)
    title = text[line_start:line_end].strip()
    return title, line_end + 1  # content 从下一行开始


def _cn_count(text):
    return len(re.findall(r'[一-鿿]', text))


def split_text(text):
    """解析整本文本 → 章节结构字典。

    返回：
      format      : 主拆分格式（章/回/卷/集/节），无则 None
      count       : 正文章节数（不含番外）
      preface     : 第一标记前的内容（前言/简介）
      chapters    : [{"idx","title","chars","type","content"}, ...]
                    type = body 正文 / extra 番外
    """
    # 1. 收集番外标记（无论主格式如何，番外始终独立成章；只认标题式行）
    extra_markers = [
        (m.start(), m.end(), m.group(), "extra")
        for m in re.finditer(EXTRA_PAT, text)
        if _is_heading_line(text, m.start())
    ]

    # 2. 统计各格式【行首】命中数，选主格式
    counts = {}
    for name, pat in CHAPTER_PATTERNS.items():
        ms = re.findall(pat, text, re.MULTILINE)
        if ms:
            counts[name] = len(ms)

    if not counts:
        if extra_markers:
            return _build(text, None, extra_markers)
        return {"format": None, "count": 0, "preface": text.strip(), "chapters": []}

    # 主格式 = 行首命中最多者（一般只有一种格式）
    primary = max(counts, key=counts.get)

    # 3. 收集主格式标记（只切主格式，其他单位在正文中视作正常书写）
    primary_markers = [
        (m.start(), m.end(), m.group(), "body")
        for m in re.finditer(CHAPTER_PATTERNS[primary], text, re.MULTILINE)
    ]
    # 去重：番外若与主格式标记同位置（极少见），保留主格式
    seen = {s for s, *_ in primary_markers}
    extras = [m for m in extra_markers if m[0] not in seen]
    markers = sorted(primary_markers + extras, key=lambda x: x[0])

    if not markers:
        return {"format": primary, "count": 0, "preface": text.strip(), "chapters": []}

    return _build(text, primary, markers)


def _build(text, primary, markers):
    """按 markers（已排序的 (start,end,raw,type) 元组）切出章节。
    
    content 从 regex match end 开始（与旧 split_text 一致），
    title 用完整标题行（匹配旧 00-split_novel.py）。"""
    preface = text[:markers[0][0]].strip()
    chapters = []
    idx = 0
    for i, (start, end, raw, mtype) in enumerate(markers):
        next_start = markers[i + 1][0] if i + 1 < len(markers) else len(text)
        content = text[end:next_start].strip()
        # 获取完整标题行（"第124章 起点"）
        full_title, _ = _title_line_and_end(text, start, end)
        idx += 1
        chapters.append({
            "idx": idx,
            "title": full_title,
            "chars": _cn_count(content),   # content 不含标题行文字
            "type": "extra" if mtype == "extra" else "body",
            "content": content,
        })

    body_count = sum(1 for c in chapters if c["type"] == "body")
    return {
        "format": primary,
        "count": body_count,
        "preface": preface,
        "chapters": chapters,
    }


# ── 诊断 ──────────────────────────────────────────────
CN_DIGITS = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
             "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
             "百": 100, "千": 1000, "万": 10000, "亿": 100000000}


def _parse_cn_number(s: str) -> int | None:
    """把中文数字转 int，如「十三」→13、「一百零五」→105。失败返回 None。"""
    s = s.strip()
    # 纯阿拉伯数字
    if s.isdigit():
        return int(s)
    # 中文数字
    total = 0
    cur = 0
    for ch in s:
        d = CN_DIGITS.get(ch)
        if d is None:
            return None
        if d >= 10:
            if cur == 0:
                cur = 1
            total += cur * d
            cur = 0
        else:
            cur += d
    return total + cur


def _extract_chapter_num(title: str) -> int | None:
    """从「第3章」「第十三章」「第125章」等提取数字。"""
    m = re.search(r'第\s*([0-9零一二三四五六七八九十百千万亿]+)\s*[章回集节卷]', title)
    if not m:
        return None
    return _parse_cn_number(m.group(1))


def diagnose(text: str, cfg: dict | None = None) -> dict:
    """对已切分的文本执行诊断分析。

    cfg 可选键：max_chars(默认8000), 
    异常分两层：
      hard = 必须处理（格式不支持、gap 缺失）
      soft = 仅提示（巨型章）

    返回结构化诊断字典，不含 content（不暴露全文）。
    """
    if cfg is None:
        cfg = {}
    min_chars = cfg.get("min_chars", 300)
    max_chars = cfg.get("max_chars", 8000)
    noise_max_len = cfg.get("noise_max_len", 20)

    result = split_text(text)

    hard = []
    soft = []
    details = []
    char_list = []
    body_nums_seen = set()
    body_by_num = {}

    for ch in result["chapters"]:
        # 字数直接用 split_text 统计的原始字数（含标题续行，不计特殊处理）
        ccount = ch["chars"]

        ch_info = {
            "idx": ch["idx"],
            "title": ch["title"],
            "type": ch["type"],
            "chars": ccount,
            "warnings": [],
        }

        # ── 字数检查（仅 body；迷你章暂不判断，巨型章保留） ──
        if ch["type"] == "body":
            char_list.append(ccount)
            if ccount > max_chars:
                ch_info["warnings"].append(f"巨型章：{ccount} 字（阈值 {max_chars}）")
                soft.append({"chapter": ch["idx"], "type": "giant_chapter",
                             "detail": f"章「{ch['title']}」正文 {ccount} 字，超过阈值 {max_chars}"})

            # 记录序号用于 gap 检测（不判重复）
            num = _extract_chapter_num(ch["title"])
            if num is not None:
                body_nums_seen.add(num)
                body_by_num[num] = ch

        details.append(ch_info)

    # ── Gap 缺失（序号跨跳 >1） ──
    sorted_nums = sorted(body_by_num.keys())
    for i in range(len(sorted_nums) - 1):
        a, b = sorted_nums[i], sorted_nums[i + 1]
        if b - a > 1:
            ca = body_by_num[a]
            cb = body_by_num[b]
            gap_count = b - a - 1
            hard.append({"chapter": cb["idx"], "type": "chapter_gap",
                         "detail": f"从「{ca['title']}」到「{cb['title']}」缺失 {gap_count} 章"})

    # ── 格式不支持 ──
    if result["format"] is None and result["chapters"]:
        hard.insert(0, {"chapter": 0, "type": "format_not_supported",
                        "detail": "未检测到「章/回/卷/集/节」章节标记，无法拆分"})

    # ── 首尾采样 ──
    body_chs = [c for c in result["chapters"] if c["type"] == "body"]
    preview = {}
    if body_chs:
        preview["first_title"] = body_chs[0]["title"]
        preview["first_500"] = body_chs[0]["content"][:500].strip()
        last = body_chs[-1]
        preview["last_title"] = last["title"]
        preview["last_500"] = last["content"][-500:].strip() if len(last["content"]) >= 500 else last["content"].strip()
    if result["preface"]:
        preview["preface_500"] = result["preface"][:500].strip()

    # ── 字数统计 ──
    char_stats = {}
    if char_list:
        char_stats = {"min": min(char_list), "max": max(char_list),
                      "avg": round(sum(char_list) / len(char_list), 1)}

    return {
        "format": result["format"],
        "total_chapters": len(result["chapters"]),
        "body_count": result["count"],
        "extra_count": sum(1 for c in result["chapters"] if c["type"] == "extra"),
        "preface_present": bool(result["preface"]),
        "preview": preview,
        "char_stats": char_stats,
        "issues": {"hard": hard, "soft": soft},
        "detailed": details,
    }


def decode_file(raw: bytes, filename: str) -> str:
    """把上传的字节解码成文本。支持 .txt（utf-8/gbk）和 .epub。"""
    lower = (filename or "").lower()
    if lower.endswith(".epub"):
        return _extract_epub(raw)
    # txt / 其他文本：先试 utf-8，再试 gbk
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", "ignore")


def _extract_epub(raw: bytes) -> str:
    """用 ebooklib + BeautifulSoup 提取 EPUB 正文文本，匹配旧 text_extractors 行为。"""
    try:
        from ebooklib import epub
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError("处理 .epub 需安装：pip install ebooklib beautifulsoup4")

    import io
    book = epub.read_epub(io.BytesIO(raw))
    texts = []
    for item in book.get_items():
        try:
            body_html = item.get_body_content()
        except Exception:
            continue
        if not body_html:
            continue
        soup = BeautifulSoup(body_html, "html.parser")
        text = soup.get_text("\n", strip=False)
        texts.append(text)
    return "\n".join(texts)

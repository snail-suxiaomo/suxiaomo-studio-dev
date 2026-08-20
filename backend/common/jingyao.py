"""common/jingyao.py —— 08-精要 下游共享读取器（逐章累积模式，2026-07-19 恢复）。

- 08-精要/精要{idx:03d}.md          截至第 idx 章的累积快照
- 08-精要/08-小说精要报告.md        最新完整报告

下游（09-剧本 / 10-资产）调 get_context(proj, idx) 取得「截至本章的累积报告」，
用于维持跨集连贯（伏笔跨章回收、人物/关系延续）。
"""

from common import db


def get_context(proj, idx):
    """下游（09-剧本 / 10-资产）读取 08-精要 的累积上下文。

    返回拼接字符串（优先截至本章的快照，回退最新完整报告，再回退空串）：
      <精要{idx:03d}.md 全文> 或 <08-小说精要报告.md 全文>
    若均不存在则返回空串，调用方注入 {context_精要} 即可。
    """
    snap = proj / "08-精要" / f"精要{idx:03d}.md"
    if snap.exists():
        return snap.read_text(encoding="utf-8").strip()
    rep = proj / "08-精要" / "08-小说精要报告.md"
    if rep.exists():
        return rep.read_text(encoding="utf-8").strip()
    return ""

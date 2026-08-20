"""ai_rule/service.py —— AI 调用规则（双世界：参考只读 + 自建可用）

数据模型（表 ai_rules，建表见 bundled/schema/ai_rules.sql）：
  ai_rules 表**只存「自建规则」**（用户实际使用的）。
  id, menu(所属菜单/功能模块), function_key(具体功能), role(规则角色),
  name, content(正文/系统提示), model_config_id(引用模型配置, NULL=跟随启用),
  thinking(standard/deep), strength(0~1, NULL=跟随模型配置),
  enabled(1=启用), is_builtin(1=源自参考规则), ref_path(来源参考文件路径),
  sort_order, created_at, updated_at

默认参考规则（只读，不进表）：
  <DATA_ROOT>/AI调用规则/<menu>/<规则名>.md
  格式：YAML frontmatter（menu/function_key/role/name/thinking/strength/enabled/is_builtin/model_config_id）
        + 正文（--- 之后）作为 content。
  系统只读取并展示；不可改、不可删（要调整只能改文件本身）。

工作流：
  - 参考规则：list_reference_rules() 直接扫文件夹展示（只读）。
  - 自建规则：从参考「复制使用规则」(copy_reference_to_db) 或「新建」(create_ai_rule) 产生，
    进 ai_rules 表，可改/删/单条重置。
  - 单条重置 reset_rule(rid)：若 ref_path 非空，从来源文件重新读入覆盖本条。
  - 删了自建规则后，源文件仍在，可再去参考区「复制使用」重新加载。
"""

import re
import shutil
from datetime import datetime
from pathlib import Path

from common import db
from ai_rule import reviewer


RULES_DIR_NAME = 'AI调用规则'
BUNDLED_RULES_DIR = Path(__file__).resolve().parents[1] / 'bundled' / RULES_DIR_NAME


def _conn():
    return db.get_conn()


def _rules_dir():
    return db.DATA_ROOT / RULES_DIR_NAME


def _now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _ensure_ref_path_column(conn):
    """幂等：若 ai_rules 表缺 ref_path 列则补上（兼容旧库）。"""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(ai_rules)")]
    if 'ref_path' not in cols:
        conn.execute("ALTER TABLE ai_rules ADD COLUMN ref_path TEXT")
        conn.commit()


def _insert_db_from_rule(rule: dict, ref_path: str):
    """把一条解析后的规则作为「自建规则」插入 DB（source='db', ref_path 固定）。"""
    conn = _conn()
    try:
        now = _now()
        max_order = conn.execute(
            'SELECT COALESCE(MAX(sort_order), 0) FROM ai_rules').fetchone()[0]
        cur = conn.execute(
            'INSERT INTO ai_rules(menu, function_key, role, name, content, model_config_id, '
            'thinking, strength, result_count, enabled, is_builtin, source, ref_path, sort_order, created_at, updated_at) '
            'VALUES(?,?,?,?,?,?,?,?,?,?,0,\'db\',?,?,?,?)',
            (rule['menu'], rule['function_key'], rule['role'], rule['name'], rule['content'],
             rule['model_config_id'], rule['thinking'], rule['strength'], rule.get('result_count'),
             rule['enabled'],
             ref_path, max_order + 10, now, now))
        conn.commit()
        return get_ai_rule(cur.lastrowid)
    finally:
        conn.close()


def _migrate_legacy_rows():
    """旧版兼容迁移：把残留的 source='file' 镜像行收敛为「每个参考文件仅一条自建规则」。

    旧逻辑会在编辑内置规则时把 source 从 'file' 翻成 'db'，并在重置时重导文件，
    导致同一 (menu,function_key,role) 下出现 file 行与 db 行并存的重复。
    新模型：参考只从文件读，库里只留自建；故按文件身份去重——每个文件保留一条 db 行并填 ref_path，
    多余的 file 行（及重复 db 行）删除。
    """
    conn = _conn()
    try:
        _copy_bundled_if_missing()
        rules_dir = _rules_dir()
        if not rules_dir.exists():
            return
        for md in _iter_rule_files(rules_dir):
            try:
                text = md.read_text(encoding='utf-8')
            except Exception as e:
                print(f'[ai_rule] 迁移读取失败 {md}: {e}', flush=True)
                continue
            meta, body = parse_frontmatter(text)
            rule = _coerce(meta, body, fallback_name=md.stem)
            ref_path = md.relative_to(rules_dir).as_posix()
            rows = conn.execute(
                "SELECT id, source FROM ai_rules WHERE menu=? AND function_key=? AND role=?",
                (rule['menu'], rule['function_key'], rule['role'])).fetchall()
            db_rows = [r for r in rows if r['source'] == 'db']
            if db_rows:
                keep = db_rows[0]['id']
            elif rows:
                keep = rows[0]['id']  # 仅有 file 行：把它转成 db
            else:
                _insert_db_from_rule(rule, ref_path)
                continue
            conn.execute(
                "UPDATE ai_rules SET ref_path=?, is_builtin=0, source='db' WHERE id=?",
                (ref_path, keep))
            conn.execute(
                "DELETE FROM ai_rules WHERE menu=? AND function_key=? AND role=? AND id!=?",
                (rule['menu'], rule['function_key'], rule['role'], keep))
        conn.commit()
    finally:
        conn.close()


_ready = False


def _migrate_thinking_strength():
    """一次性迁移：strength 由 REAL 改为 TEXT（follow/low/medium/high/ultra），
    thinking 默认值 standard→follow，并做值映射。

    幂等：仅当 strength 列类型为 REAL（旧结构）时执行。已为新结构则跳过。
    表重建法：rename → 建新表（含 source/ref_path 全列）→ 搬数据并转换值 → drop 旧表。
    """
    conn = _conn()
    try:
        cols = {r[1]: r[2] for r in conn.execute('PRAGMA table_info(ai_rules)').fetchall()}
        if cols.get('strength') != 'REAL':
            return  # 已是新结构
        # 极旧库可能缺 source 列，先补
        if 'source' not in cols:
            conn.execute("ALTER TABLE ai_rules ADD COLUMN source TEXT NOT NULL DEFAULT 'db'")
        conn.execute('DROP INDEX IF EXISTS idx_ai_rules_scope_fn')
        conn.execute('DROP INDEX IF EXISTS idx_ai_rules_enabled')
        conn.execute('ALTER TABLE ai_rules RENAME TO ai_rules_old')
        conn.execute(
            'CREATE TABLE ai_rules ('
            'id INTEGER PRIMARY KEY AUTOINCREMENT,'
            'menu TEXT NOT NULL DEFAULT \'通用\','
            'function_key TEXT NOT NULL DEFAULT \'\','
            'role TEXT NOT NULL DEFAULT \'system\','
            'name TEXT NOT NULL,'
            'content TEXT NOT NULL DEFAULT \'\','
            'model_config_id INTEGER,'
            'thinking TEXT NOT NULL DEFAULT \'follow\','
            'strength TEXT,'
            'enabled INTEGER NOT NULL DEFAULT 1,'
            'is_builtin INTEGER NOT NULL DEFAULT 0,'
            'source TEXT NOT NULL DEFAULT \'db\','
            'ref_path TEXT,'
            'sort_order INTEGER NOT NULL DEFAULT 0,'
            'result_count TEXT,'
            'created_at TEXT NOT NULL DEFAULT (datetime(\'now\',\'localtime\')),'
            'updated_at TEXT NOT NULL DEFAULT (datetime(\'now\',\'localtime\')))')
        conn.execute(
            'INSERT INTO ai_rules(id, menu, function_key, role, name, content, model_config_id, '
            'thinking, strength, result_count, enabled, is_builtin, source, sort_order, created_at, updated_at, ref_path) '
            'SELECT id, menu, function_key, role, name, content, model_config_id, '
            "CASE WHEN thinking='deep' THEN 'enabled' WHEN thinking='disabled' THEN 'disabled' ELSE 'follow' END, "
            "CASE WHEN strength IN ('follow','low','medium','high','ultra') THEN strength "
            'WHEN strength IS NULL THEN NULL '
            "WHEN strength < 0.3 THEN 'low' WHEN strength < 0.6 THEN 'medium' "
            "WHEN strength < 0.85 THEN 'high' ELSE 'ultra' END, "
            "CASE WHEN role='generate' THEN 'single' ELSE NULL END, "
            'enabled, is_builtin, source, sort_order, created_at, updated_at, ref_path '
            'FROM ai_rules_old')
        conn.execute('CREATE INDEX idx_ai_rules_scope_fn ON ai_rules(menu, function_key)')
        conn.execute('CREATE INDEX idx_ai_rules_enabled ON ai_rules(enabled)')
        conn.execute('DROP TABLE ai_rules_old')
        conn.commit()
        print('[ai_rule] 已迁移 thinking/strength 语义（REAL→TEXT）', flush=True)
    finally:
        conn.close()


def _migrate_result_count():
    """幂等：补 result_count 列（single/multi），并把明确能推断的行补上值。

    - 缺列则 ALTER 补上（旧库）。
    - role='generate' 的行补 'single'（生成=单条）；其余保持 NULL，
      由前端按 role 兜底（organize 等默认 multi）。
    """
    conn = _conn()
    try:
        cols = [r[1] for r in conn.execute('PRAGMA table_info(ai_rules)')]
        if 'result_count' not in cols:
            conn.execute("ALTER TABLE ai_rules ADD COLUMN result_count TEXT")
        conn.execute(
            "UPDATE ai_rules SET result_count='single' "
            "WHERE role='generate' AND (result_count IS NULL OR result_count='')")
        conn.commit()
    finally:
        conn.close()


def ensure_ready():
    """幂等初始化：确保 ref_path 列存在、旧 file 镜像行已迁移为自建规则、
    thinking/strength 语义已升级为新结构。

    不再做「首启自动把文件灌进 DB」——参考规则改由 list_reference_rules 直接读文件。
    """
    global _ready
    if _ready:
        return
    try:
        conn = _conn()
        try:
            _ensure_ref_path_column(conn)
        finally:
            conn.close()
        _migrate_legacy_rows()
        _migrate_thinking_strength()
        _migrate_result_count()
    except Exception as e:
        print(f'[ai_rule] ensure_ready 异常: {e}', flush=True)
    finally:
        _ready = True


# ---------------------------------------------------------------------------
# 文件解析（最小 frontmatter 解析，不依赖 PyYAML）
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str):
    """解析 `--- ... ---` 之间的 key: value，返回 (meta: dict, body: str)。

    若无 frontmatter，返回 ({}, 全文去空白)。
    """
    m = re.match(r'^\s*---\s*\n(.*?)\n---\s*\n?(.*)$', text, re.DOTALL)
    if not m:
        return {}, text.strip()
    meta_text, body = m.group(1), m.group(2)
    meta = {}
    for line in meta_text.splitlines():
        line = line.rstrip()
        if not line.strip() or line.strip().startswith('#'):
            continue
        if ':' not in line:
            continue
        k, _, v = line.partition(':')
        k = k.strip()
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
            v = v[1:-1]
        if k:
            meta[k] = v
    return meta, body.strip()


def _coerce(meta: dict, body: str, fallback_name: str = ''):
    """把 frontmatter + body 组装成 ai_rules 行字典（含类型转换）。"""
    thinking = _think(meta.get('thinking') or 'follow')

    sr = (meta.get('strength') or '').strip()
    strength = _str(sr) if sr else None  # 空 → 跟随(follow)

    er = (meta.get('enabled') or 'true').strip().lower()
    enabled = 1 if er in ('1', 'true', 'yes', 'y', '启用') else 0

    ibr = (meta.get('is_builtin') or 'true').strip().lower()
    is_builtin = 1 if ibr in ('1', 'true', 'yes', 'y') else 0

    mc = None
    mcr = (meta.get('model_config_id') or '').strip()
    if mcr:
        try:
            mc = int(mcr)
        except ValueError:
            mc = None

    name = (meta.get('name') or '').strip() or fallback_name
    content = body or (meta.get('content') or '')

    rc = (meta.get('result_count') or '').strip().lower()
    result_count = rc if rc in ('single', 'multi') else None

    return {
        'menu': (meta.get('menu') or meta.get('scope') or '通用').strip(),
        'function_key': (meta.get('function_key') or '通用').strip(),
        'role': (meta.get('role') or 'system').strip(),
        'name': name,
        'content': content,
        'model_config_id': mc,
        'thinking': thinking,
        'strength': strength,
        'result_count': result_count,
        'enabled': enabled,
        'is_builtin': is_builtin,
        'source': 'file',
    }


def _iter_rule_files(rules_dir: Path):
    if not rules_dir.exists():
        return
    for p in sorted(rules_dir.rglob('*.md')):
        if p.is_file():
            yield p


def _copy_bundled_if_missing():
    """若数据根下 AI调用规则/ 不存在，从随包 bundled 源复制（仅缺失时）。"""
    dst = _rules_dir()
    if dst.exists():
        return
    if not BUNDLED_RULES_DIR.exists():
        return
    try:
        shutil.copytree(BUNDLED_RULES_DIR, dst)
    except Exception as e:  # 复制失败不应阻断启动
        print(f'[ai_rule] 复制内置规则源失败: {e}', flush=True)


def _scan_folder_into_db():
    """[已废弃] 旧版首启自动灌库逻辑，已不再使用（参考规则改由文件直接读）。保留空函数以免误调用。"""
    return


# ---------------------------------------------------------------------------
# 种子（首启 / 缺失时）
# ---------------------------------------------------------------------------

def ensure_ai_rules_seeded():
    """[已废弃] 旧版首启自动灌库；保留为空函数以免外部误调用报错。"""
    ensure_ready()


# ---------------------------------------------------------------------------
# 查询 / CRUD
# ---------------------------------------------------------------------------

def list_ai_rules(menu=None, function_key=None, role=None, enabled=None):
    ensure_ready()
    conn = _conn()
    try:
        sql = 'SELECT * FROM ai_rules WHERE 1=1'
        params = []
        if menu:
            sql += ' AND menu=?'; params.append(menu)
        if function_key:
            sql += ' AND function_key=?'; params.append(function_key)
        if role:
            sql += ' AND role=?'; params.append(role)
        if enabled is not None:
            sql += ' AND enabled=?'; params.append(enabled)
        sql += ' ORDER BY menu, function_key, sort_order, id'
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_ai_rule(rid):
    conn = _conn()
    try:
        row = conn.execute('SELECT * FROM ai_rules WHERE id=?', (rid,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_ai_rule(data):
    from ai_rule.validator import validate_payload
    validate_payload(data)
    conn = _conn()
    try:
        name = (data.get('name') or '').strip()
        exist = conn.execute('SELECT id FROM ai_rules WHERE name=?', (name,)).fetchone()
        if exist:
            raise ValueError('规则名称已存在：' + name)
        now = _now()
        max_order = conn.execute(
            'SELECT COALESCE(MAX(sort_order), 0) FROM ai_rules').fetchone()[0]
        cur = conn.execute(
            'INSERT INTO ai_rules(menu, function_key, role, name, content, model_config_id, '
            'thinking, strength, enabled, is_builtin, source, sort_order, created_at, updated_at) '
            'VALUES(?,?,?,?,?,?,?,?,?,0,\'db\',?,?,?)',
            (data.get('menu', '通用'), data.get('function_key', '通用'), data.get('role', 'system'),
             (data.get('name') or '').strip(), data.get('content', ''),
             _mc(data.get('model_config_id')), _think(data.get('thinking')),
             _str(data.get('strength')), _en(data.get('enabled')),
             max_order + 10, now, now))
        conn.commit()
        return get_ai_rule(cur.lastrowid)
    finally:
        conn.close()


def update_ai_rule(rid, data):
    from ai_rule.validator import validate_update
    existing = get_ai_rule(rid)
    if not existing:
        raise ValueError('规则不存在')
    validate_update(data)
    name = (data.get('name') or existing['name']).strip()
    conn = _conn()
    try:
        dup = conn.execute('SELECT id FROM ai_rules WHERE name=? AND id!=?', (name, rid)).fetchone()
        if dup:
            raise ValueError('规则名称已存在：' + name)
        now = _now()
        # 编辑后视为用户工作副本（source='db'），即便原是内置项；is_builtin 保持（仍不可删）
        conn.execute(
            'UPDATE ai_rules SET menu=?, function_key=?, role=?, name=?, content=?, '
            'model_config_id=?, thinking=?, strength=?, enabled=?, is_builtin=?, source=\'db\', '
            'updated_at=? WHERE id=?',
            ((data.get('menu') or existing['menu']).strip(),
             (data.get('function_key') or existing['function_key']).strip(),
             (data.get('role') or existing['role']).strip(),
             (data.get('name') or existing['name']).strip(),
             data.get('content', existing['content']),
             _mc(data.get('model_config_id', existing['model_config_id'])),
             _think(data.get('thinking', existing['thinking'])),
             _str(data.get('strength', existing['strength'])),
             _en(data.get('enabled', existing['enabled'])),
             existing['is_builtin'],
             now, rid))
        conn.commit()
        return get_ai_rule(rid)
    finally:
        conn.close()


def delete_ai_rule(rid):
    existing = get_ai_rule(rid)
    if not existing:
        raise ValueError('规则不存在')
    ok, reason = reviewer.can_delete(existing)
    if not ok:
        raise ValueError(reason)
    conn = _conn()
    try:
        conn.execute('DELETE FROM ai_rules WHERE id=?', (rid,))
        conn.commit()
        return True
    finally:
        conn.close()


def list_reference_rules():
    """读取 workspace/AI调用规则/ 下的所有 .md 作为「默认参考规则」（只读展示）。

    每条返回：ref_path(相对路径) + 解析出的字段 + copied(是否已有同名自建规则)。
    不写库、不修改文件。
    """
    ensure_ready()
    rules_dir = _rules_dir()
    if not rules_dir.exists():
        return []
    conn = _conn()
    try:
        existing = {(r['ref_path']) for r in conn.execute(
            "SELECT ref_path FROM ai_rules WHERE ref_path IS NOT NULL").fetchall()}
    finally:
        conn.close()
    out = []
    for md in _iter_rule_files(rules_dir):
        try:
            text = md.read_text(encoding='utf-8')
        except Exception as e:
            print(f'[ai_rule] 读取参考规则失败 {md}: {e}', flush=True)
            continue
        meta, body = parse_frontmatter(text)
        rule = _coerce(meta, body, fallback_name=md.stem)
        ref_path = md.relative_to(rules_dir).as_posix()
        out.append({
            'ref_path': ref_path,
            'menu': rule['menu'],
            'function_key': rule['function_key'],
            'role': rule['role'],
            'name': rule['name'],
            'content': rule['content'],
            'model_config_id': rule['model_config_id'],
            'thinking': rule['thinking'],
            'strength': rule['strength'],
            'result_count': rule.get('result_count'),
            'enabled': rule['enabled'],
            'copied': ref_path in existing,
        })
    return out


def copy_reference_to_db(ref_path: str):
    """把一条参考规则（按 ref_path）复制为「自建规则」进 DB。已复制则直接返回已有项。"""
    ensure_ready()
    rules_dir = _rules_dir()
    md = rules_dir / ref_path
    if not md.exists() or not md.is_file():
        raise ValueError('参考规则文件不存在：' + ref_path)
    conn = _conn()
    try:
        exist = conn.execute(
            "SELECT id FROM ai_rules WHERE ref_path=?", (ref_path,)).fetchone()
        if exist:
            return get_ai_rule(exist['id'])
    finally:
        conn.close()
    try:
        text = md.read_text(encoding='utf-8')
    except Exception as e:
        raise ValueError('读取参考规则失败：' + str(e))
    meta, body = parse_frontmatter(text)
    rule = _coerce(meta, body, fallback_name=md.stem)
    return _insert_db_from_rule(rule, ref_path)


def reset_rule(rid):
    """单条重置：若 ref_path 非空，从来源文件重新读入覆盖本条；否则报错。"""
    existing = get_ai_rule(rid)
    if not existing:
        raise ValueError('规则不存在')
    ref_path = existing.get('ref_path')
    if not ref_path:
        raise ValueError('该规则为纯新建，无来源文件，无法重置')
    rules_dir = _rules_dir()
    md = rules_dir / ref_path
    if not md.exists() or not md.is_file():
        raise ValueError('来源文件不存在：' + ref_path)
    try:
        text = md.read_text(encoding='utf-8')
    except Exception as e:
        raise ValueError('读取来源文件失败：' + str(e))
    meta, body = parse_frontmatter(text)
    rule = _coerce(meta, body, fallback_name=md.stem)
    conn = _conn()
    try:
        now = _now()
        conn.execute(
            'UPDATE ai_rules SET menu=?, function_key=?, role=?, name=?, content=?, '
            'model_config_id=?, thinking=?, strength=?, enabled=?, is_builtin=?, ref_path=?, '
            'updated_at=? WHERE id=?',
            (rule['menu'], rule['function_key'], rule['role'], rule['name'], rule['content'],
             rule['model_config_id'], rule['thinking'], rule['strength'], rule['enabled'],
             existing['is_builtin'], ref_path, now, rid))
        conn.commit()
        return get_ai_rule(rid)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 类型辅助
# ---------------------------------------------------------------------------

def _mc(v):
    if v is None or v == '':
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def _think(v):
    """思考模式：新语义 follow/fast/expert（跟随所选模型 modes 的 key，原样保留）。

    兼容旧值：deep→follow、standard→follow、enabled→expert、disabled→fast。
    """
    t = (v or 'follow')
    if isinstance(t, str):
        t = t.strip().lower()
    mapping = {
        'deep': 'follow',       # 旧值兼容：deep 不再使用，回落跟随
        'standard': 'follow',   # 旧值兼容
        'enabled': 'expert',    # 旧值兼容：强制开启思考 → 专家模式
        'disabled': 'fast',     # 旧值兼容：强制关闭思考 → 快速模式
        'follow': 'follow',
    }
    if t in mapping:
        return mapping[t]
    # 新值（fast/expert 或模型自定义 modes key）原样保留
    return t


def _str(v):
    """思考强度：follow/low/medium/high 原样；数字 0~1 按档位映射；空/非法 → None(跟随)。"""
    if v is None or v == '':
        return None
    s = str(v).strip().lower()
    if s in ('follow', 'low', 'medium', 'high'):
        return s
    if s == 'ultra':
        # 旧值兼容：超高档已废弃，回落为高
        return 'high'
    try:
        f = float(s)
    except (ValueError, TypeError):
        return None
    if f < 0.3:
        return 'low'
    if f < 0.6:
        return 'medium'
    if f < 0.85:
        return 'high'
    return 'high'


def _en(v):
    if v is None:
        return 1
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, int):
        return 1 if v else 0
    s = str(v).strip().lower()
    return 1 if s in ('1', 'true', 'yes', 'y', '启用') else 0


def set_active_rule(menu, function_key, role, rid=None, ref_path=None):
    """激活指定 scope+role 下的一条规则，并禁用同 scope+role 的其他规则。

    - 若传 rid：必须是已存在自建规则，且 menu/function_key/role 匹配。
    - 若传 ref_path：先把参考规则复制为自建规则（幂等），再激活。
    返回被激活的规则字典。
    """
    ensure_ready()
    if rid:
        rule = get_ai_rule(rid)
        if not rule:
            raise ValueError('规则不存在')
        if (rule['menu'] != menu or rule['function_key'] != function_key
                or rule['role'] != role):
            raise ValueError('规则与指定范围不匹配')
    elif ref_path:
        rule = copy_reference_to_db(ref_path)
        rid = rule['id']
    else:
        raise ValueError('rid 或 ref_path 必须提供一个')

    conn = _conn()
    try:
        conn.execute(
            'UPDATE ai_rules SET enabled=0 WHERE menu=? AND function_key=? AND role=? AND id!=?',
            (menu, function_key, role, rid))
        conn.execute(
            'UPDATE ai_rules SET enabled=1 WHERE id=?',
            (rid,))
        conn.commit()
        return get_ai_rule(rid)
    finally:
        conn.close()


def resolve_rule_content(menu, function_key, role, fallback_content=None):
    """读取「AI 调用规则」中某条指令的正文，四级回退：

    1) DB 中启用(enabled=1)的自建规则（按 menu+function_key+role 匹配）；
    2) 参考规则文件（<DATA_ROOT>/AI调用规则/<menu>/...md，按 frontmatter 匹配）；
    3) 调用方提供的 fallback_content；
    4) 空串。

    用途：管线（00-06）不再直查 novel_prompt_config，改用本函数取指令正文；
    当 DB 无对应自建规则时，直接以参考文件作为默认值，无需改首启播种逻辑。
    """
    ensure_ready()
    # 1) DB 启用规则（自建规则优先级最高）
    try:
        for r in (list_ai_rules(menu=menu, function_key=function_key, role=role, enabled=1) or []):
            if r.get('content'):
                return r['content']
    except Exception as e:
        print(f'[ai_rule] resolve_rule_content DB 查询失败: {e}', flush=True)
    # 2) 参考规则文件（作为默认指令源）
    try:
        for ref in (list_reference_rules() or []):
            if (ref.get('menu') == menu and ref.get('function_key') == function_key
                    and ref.get('role') == role and ref.get('content')):
                return ref['content']
    except Exception as e:
        print(f'[ai_rule] resolve_rule_content 参考文件查询失败: {e}', flush=True)
    # 3) fallback（调用方内置兜底）
    return fallback_content or ""

"""
荟城减重 WSP 报告生成系统 - 报告生成模块
负责生成 PDF 报告和 LLM 分析用 MD 文件
"""
import json
from datetime import datetime


def calc_bmi(weight_kg, height_cm):
    """计算 BMI 及分级"""
    if not weight_kg or not height_cm:
        return None, None
    bmi = round(weight_kg / ((height_cm / 100) ** 2), 1)
    if bmi < 18.5:
        level = '体重过轻'
    elif bmi < 24:
        level = '正常'
    elif bmi < 28:
        level = '超重'
    elif bmi < 32:
        level = '肥胖Ⅰ级'
    elif bmi < 36:
        level = '肥胖Ⅱ级'
    else:
        level = '肥胖Ⅲ级'
    return bmi, level


def calc_bp(sbp, dbp):
    """血压分级"""
    if not sbp and not dbp:
        return None
    sbp = sbp or 0
    dbp = dbp or 0
    if sbp >= 180 or dbp >= 110:
        return '高血压3级'
    elif sbp >= 160 or dbp >= 100:
        return '高血压2级'
    elif sbp >= 140 or dbp >= 90:
        return '高血压1级'
    elif sbp >= 130 or dbp >= 80:
        return '正常高值'
    elif sbp >= 120 and dbp < 80:
        return '正常高值'
    else:
        return '正常'


def calc_waist(waist_cm, sex):
    """腰围评估"""
    if not waist_cm:
        return None
    if sex == '男':
        if waist_cm >= 90:
            return '超标（≥90cm）'
        elif waist_cm >= 85:
            return '临界'
        else:
            return '正常'
    else:
        if waist_cm >= 85:
            return '超标（≥85cm）'
        elif waist_cm >= 80:
            return '临界'
        else:
            return '正常'


def calc_whr(waist_cm, hip_cm, sex):
    """腰臀比评估"""
    if not waist_cm or not hip_cm:
        return None, None
    whr = round(waist_cm / hip_cm, 2)
    if sex == '男':
        if whr >= 1.0:
            level = '中心性肥胖'
        elif whr >= 0.9:
            level = '偏高'
        else:
            level = '正常'
    else:
        if whr >= 0.9:
            level = '中心性肥胖'
        elif whr >= 0.85:
            level = '偏高'
        else:
            level = '正常'
    return whr, level


def calc_hr(hr):
    """心率评估"""
    if not hr:
        return None
    if hr < 60:
        return '心率偏慢'
    elif hr > 100:
        return '心率偏快'
    else:
        return '正常'


def compute_derived(record):
    """计算所有派生值"""
    derived = {}
    derived['bmi'], derived['bmi_level'] = calc_bmi(
        record.get('weight_kg'), record.get('height_cm'))
    derived['bp_level'] = calc_bp(record.get('sbp'), record.get('dbp'))
    derived['waist_level'] = calc_waist(
        record.get('waist_cm'), record.get('sex'))
    derived['whr'], derived['whr_level'] = calc_whr(
        record.get('waist_cm'), record.get('hip_cm'), record.get('sex'))
    derived['hr_level'] = calc_hr(record.get('heart_rate'))

    # 服务包判断
    path = record.get('suitable_path', '')
    derived['package_type'] = '完整包' if '全程' in (path or '') else '轻度包'

    # 阻断判断
    red_flags = record.get('red_positive', [])
    if red_flags and len(red_flags) > 0:
        derived['gate_blocked'] = True
        derived['gate_reason'] = f"红旗项：{'、'.join(red_flags)}"
    else:
        derived['gate_blocked'] = False
        derived['gate_reason'] = None

    return derived


# ========== 通用 CSS ==========
REPORT_CSS = """
@page {
    size: A4 portrait;
    margin: 2cm 1.5cm;
    @bottom-center {
        content: "第 " counter(page) " 页 / 共 " counter(pages) " 页";
        font-size: 10px;
        color: #7F8C9B;
    }
}
@page :first { margin: 0; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
    color: #2C3E50;
    font-size: 13px;
    line-height: 1.7;
}
.cover {
    background: linear-gradient(160deg, #0A2A3C, #146C86);
    color: #fff;
    padding: 100px 40px;
    text-align: center;
    height: 297mm;
    page-break-after: always;
}
.cover-logo { font-size: 36px; font-weight: 700; letter-spacing: 3px; margin-bottom: 8px; }
.cover-sub { font-size: 16px; opacity: 0.7; margin-bottom: 40px; }
.cover-title { font-size: 24px; font-weight: 600; margin-bottom: 12px; }
.cover-info { font-size: 14px; opacity: 0.6; line-height: 2.2; }
.section { margin-bottom: 24px; page-break-inside: avoid; }
.section-title {
    font-size: 16px; font-weight: 700; color: #146C86;
    border-bottom: 2px solid #146C86; padding-bottom: 8px;
    margin-bottom: 12px;
}
table.data-table { width: 100%; border-collapse: collapse; margin-bottom: 12px; }
table.data-table th, table.data-table td {
    padding: 8px 12px; border: 1px solid #E4E8ED; text-align: left; font-size: 12px;
}
table.data-table th { background: #F5F7FA; font-weight: 600; color: #7F8C9B; }
.tag {
    display: inline-block; padding: 3px 8px; border-radius: 4px;
    font-size: 11px; margin: 2px; font-weight: 500;
}
.tag-blue { background: rgba(20,108,134,0.1); color: #146C86; }
.tag-orange { background: rgba(232,131,58,0.1); color: #E8833A; }
.tag-red { background: rgba(201,75,75,0.1); color: #C94B4B; }
.tag-green { background: rgba(66,163,106,0.1); color: #42A36A; }
.tag-yellow { background: rgba(242,184,75,0.15); color: #C08B00; }
.calc-box {
    background: #F0F7FA; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px;
}
.calc-row { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #D6E4ED; }
.calc-row:last-child { border-bottom: none; }
.calc-label { color: #5A6C7D; }
.calc-value { font-weight: 600; }
.warn { color: #F2B84B; }
.danger { color: #C94B4B; }
.good { color: #42A36A; }
.risk-bar-wrap { margin-bottom: 8px; }
.risk-bar-label { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 2px; }
.risk-bar-bg { height: 8px; background: #E4E8ED; border-radius: 4px; overflow: hidden; }
.risk-bar-fill { height: 100%; border-radius: 4px; }
.toc-item { padding: 4px 0; font-size: 13px; color: #146C86; }
.alert-box {
    background: rgba(201,75,75,0.08); border-left: 4px solid #C94B4B;
    padding: 12px 16px; border-radius: 4px; margin: 12px 0;
}
.alert-box-green {
    background: rgba(66,163,106,0.08); border-left: 4px solid #42A36A;
    padding: 12px 16px; border-radius: 4px; margin: 12px 0;
}
"""


def generate_report_html(record, derived, template_content=None):
    """生成报告 HTML 内容"""
    name = record.get('name', '未知')
    sex = record.get('sex', '')
    age = record.get('age', '')
    record_id = record.get('record_id', '')
    record_date = str(record.get('record_date', ''))
    path = record.get('suitable_path', '全程版')
    pkg = derived.get('package_type', '完整包')

    bmi = derived.get('bmi')
    bmi_level = derived.get('bmi_level', '—')
    bp_level = derived.get('bp_level', '—')
    waist_level = derived.get('waist_level', '—')
    whr = derived.get('whr')
    whr_level = derived.get('whr_level', '—')
    hr_level = derived.get('hr_level', '—')

    goals = record.get('selected_goals', [])
    conditions = record.get('conditions', [])
    medications = record.get('medications', [])
    allergies = record.get('allergies', [])
    red_flags = record.get('red_positive', [])
    body_feelings = record.get('body_feelings', [])
    tcm_tendency = record.get('tcm_tendency', [])
    obstacles = record.get('main_obstacles', [])
    cautions = record.get('external_cautions', [])
    risk_scores = record.get('risk_scores', {})

    target_w = record.get('target_weight_kg')
    target_waist = record.get('target_waist_cm')
    weight = record.get('weight_kg')
    waist = record.get('waist_cm')

    def tags(items, css='tag-blue'):
        if not items:
            return '<span class="tag tag-green">无</span>'
        return ''.join(f'<span class="tag {css}">{t}</span>' for t in items)

    def risk_color(score):
        if score >= 4:
            return '#C94B4B'
        elif score >= 3:
            return '#E8833A'
        elif score >= 2:
            return '#F2B84B'
        else:
            return '#42A36A'

    risk_bars = ''
    for dim, score in risk_scores.items():
        pct = int(score / 5 * 100) if score else 0
        risk_bars += f"""
        <div class="risk-bar-wrap">
            <div class="risk-bar-label"><span>{dim}</span><span style="font-weight:600;color:{risk_color(score)}">{score}/5</span></div>
            <div class="risk-bar-bg"><div class="risk-bar-fill" style="width:{pct}%;background:{risk_color(score)}"></div></div>
        </div>"""

    gate_box = ''
    if record.get('report_permission') != '可以生成' or derived.get('gate_blocked'):
        gate_box = f'<div class="alert-box"><strong>⚠️ 闸门阻断</strong><br>{derived.get("gate_reason", "报告闸门未通过")}</div>'
    else:
        gate_box = '<div class="alert-box-green"><strong>✅ 闸门通过</strong><br>未发现红旗项，可以正常生成报告。</div>'

    female_section = ''
    if sex == '女' and record.get('female_status'):
        female_section = f'<tr><th>女性情况</th><td>{record["female_status"]}</td></tr>'

    weight_diff = f'-{(float(weight) - float(target_w)):.1f} kg' if weight and target_w else '—'
    waist_diff = f'-{(float(waist) - float(target_waist)):.1f} cm' if waist and target_waist else '—'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><style>{REPORT_CSS}</style></head>
<body>

<!-- 封面 -->
<div class="cover">
    <div class="cover-logo">荟城中医减重</div>
    <div class="cover-sub">体重管理报告</div>
    <div class="cover-title">{name} · 减重评估报告</div>
    <div class="cover-info">
        报告编号：{record_id}<br>
        评估日期：{record_date}<br>
        服务包：{path}（{pkg}）
    </div>
</div>

<!-- 目录 -->
<div class="section">
    <div class="section-title">目录</div>
    <div class="toc-item">一、基本信息</div>
    <div class="toc-item">二、体格评估</div>
    <div class="toc-item">三、健康风险筛查</div>
    <div class="toc-item">四、饮食与生活方式</div>
    <div class="toc-item">五、中医体质辨证</div>
    <div class="toc-item">六、减重目标</div>
    <div class="toc-item">七、风险评分</div>
    <div class="toc-item">八、闸门判断</div>
</div>

<!-- 一、基本信息 -->
<div class="section">
    <div class="section-title">一、基本信息</div>
    <table class="data-table">
        <tr><th style="width:15%">姓名</th><td style="width:35%">{name}</td><th style="width:15%">性别</th><td style="width:35%">{sex}</td></tr>
        <tr><th>年龄</th><td>{age}岁</td><th>职业</th><td>{record.get('occupation_status', '—')}</td></tr>
        <tr><th>身高</th><td>{record.get('height_cm', '—')} cm</td><th>体重</th><td>{record.get('weight_kg', '—')} kg</td></tr>
        <tr><th>腰围</th><td>{record.get('waist_cm', '—')} cm</td><th>臀围</th><td>{record.get('hip_cm', '—')} cm</td></tr>
        {female_section}
    </table>
</div>

<!-- 二、体格评估 -->
<div class="section">
    <div class="section-title">二、体格评估</div>
    <div class="calc-box">
        <div class="calc-row"><span class="calc-label">BMI</span><span class="calc-value {'danger' if bmi and bmi>=28 else 'warn' if bmi and bmi>=24 else 'good'}">{bmi or '—'} · {bmi_level}</span></div>
        <div class="calc-row"><span class="calc-label">血压</span><span class="calc-value {'danger' if '高血压' in (bp_level or '') else 'warn' if bp_level=='正常高值' else 'good'}">{record.get('sbp','—')}/{record.get('dbp','—')} mmHg · {bp_level}</span></div>
        <div class="calc-row"><span class="calc-label">腰围</span><span class="calc-value {'danger' if '超标' in (waist_level or '') else 'warn' if waist_level=='临界' else 'good'}">{record.get('waist_cm','—')}cm · {waist_level}</span></div>
        <div class="calc-row"><span class="calc-label">腰臀比</span><span class="calc-value {'danger' if '肥胖' in (whr_level or '') else 'warn' if whr_level=='偏高' else 'good'}">{whr or '—'} · {whr_level}</span></div>
        <div class="calc-row"><span class="calc-label">静息心率</span><span class="calc-value {'good' if hr_level=='正常' else 'warn'}">{record.get('heart_rate','—')} 次/分 · {hr_level}</span></div>
        <div class="calc-row"><span class="calc-label">体脂率</span><span class="calc-value">{record.get('body_fat_percent', '—')}%</span></div>
        <div class="calc-row"><span class="calc-label">内脏脂肪等级</span><span class="calc-value">{record.get('visceral_fat_level', '—')}</span></div>
    </div>
</div>

<!-- 三、健康风险筛查 -->
<div class="section">
    <div class="section-title">三、健康风险筛查</div>
    <p style="margin:6px 0">已知疾病：{tags(conditions, 'tag-orange') if conditions else '<span class="tag tag-green">无</span>'}</p>
    <p style="margin:6px 0">长期用药：{tags(medications, 'tag-blue') if medications else '<span class="tag tag-green">无</span>'}</p>
    <p style="margin:6px 0">过敏史：{tags(allergies, 'tag-yellow') if allergies else '<span class="tag tag-green">无</span>'}</p>
    <p style="margin:6px 0">红旗项：{tags(red_flags, 'tag-red') if red_flags else '<span class="tag tag-green">无</span>'}</p>
    {'<p style="margin:6px 0">用药备注：' + str(record.get('med_detail','—')) + '</p>' if record.get('med_detail') else ''}
</div>

<!-- 四、饮食与生活方式 -->
<div class="section">
    <div class="section-title">四、饮食与生活方式</div>
    <table class="data-table">
        <tr><th>外食频率</th><td>{record.get('eating_out_frequency', '—')}</td></tr>
        <tr><th>夜宵/零食/甜饮</th><td>{record.get('night_snack_sweet_drink', '—')}</td></tr>
        <tr><th>主食油腻程度</th><td>{record.get('staple_oily_food', '—')}</td></tr>
        <tr><th>运动频率</th><td>{record.get('exercise_frequency', '—')}</td></tr>
        <tr><th>睡眠状况</th><td>{record.get('sleep_status', '—')}</td></tr>
        <tr><th>排便情况</th><td>{record.get('bowel_status', '—')}</td></tr>
        <tr><th>压力/情绪性进食</th><td>{record.get('stress_eating', '—')}</td></tr>
        <tr><th>饮水情况</th><td>{record.get('water_intake', '—')}</td></tr>
    </table>
    <p style="margin:8px 0">发胖原因：{tags(record.get('selected_gain_reasons',[]), 'tag-orange')}</p>
</div>

<!-- 五、中医体质辨证 -->
<div class="section">
    <div class="section-title">五、中医体质辨证</div>
    <p style="margin:6px 0">体质倾向：{tags(tcm_tendency, 'tag-orange') if tcm_tendency else '<span class="tag tag-green">待定</span>'}</p>
    <p style="margin:6px 0">自觉症状：{tags(body_feelings, 'tag-yellow') if body_feelings else '<span class="tag tag-green">无</span>'}</p>
    <p style="margin:6px 0">减重阻力：{tags(obstacles, 'tag-blue') if obstacles else '<span class="tag tag-green">无</span>'}</p>
    <p style="margin:6px 0">舌象：{record.get('tongue_photo_taken', '—')}</p>
    <p style="margin:6px 0">医生备注：{record.get('report_focus_note', '—')}</p>
    <p style="margin:6px 0">外治禁忌：{tags(cautions, 'tag-red') if cautions and cautions != ['无禁忌'] else '<span class="tag tag-green">无特殊禁忌</span>'}</p>
</div>

<!-- 六、减重目标 -->
<div class="section">
    <div class="section-title">六、减重目标</div>
    <table class="data-table">
        <tr><th>目标体重</th><td>{weight or '—'} → {target_w or '—'} kg（{weight_diff}）</td></tr>
        <tr><th>目标腰围</th><td>{waist or '—'} → {target_waist or '—'} cm（{waist_diff}）</td></tr>
        <tr><th>既往减重经历</th><td>{record.get('past_weight_loss', '—')}</td></tr>
    </table>
    <p style="margin:8px 0">本次希望改善：{tags(goals, 'tag-blue') if goals else '—'}</p>
</div>

<!-- 七、风险评分 -->
<div class="section">
    <div class="section-title">七、风险评分</div>
    {risk_bars if risk_bars else '<p>暂无评分数据</p>'}
</div>

<!-- 八、闸门判断 -->
<div class="section">
    <div class="section-title">八、闸门判断</div>
    {gate_box}
    <p style="margin:8px 0">适合路径：{path}</p>
    <p style="margin:8px 0">报告闸门：{record.get('report_permission', '—')}</p>
</div>

</body>
</html>"""
    return html


def generate_md(record, derived):
    """生成 LLM 分析用 MD 文件"""
    name = record.get('name', '未知')
    path = '全程版' if '全程' in (record.get('suitable_path') or '') else '轻享版'

    def list_str(items):
        return '、'.join(items) if items else '无'

    def risk_table(scores):
        if not scores:
            return '暂无评分'
        rows = ''
        for dim, score in scores.items():
            rows += f"| {dim} | {score}/5 |\n"
        return rows

    female_line = ''
    if record.get('sex') == '女':
        female_line = f"- 女性特殊情况：{record.get('female_status', '—')}\n"

    # 预计算差值
    w_diff = '—'
    if record.get('weight_kg') and record.get('target_weight_kg'):
        try:
            w_diff = f"{float(record['weight_kg']) - float(record['target_weight_kg']):.1f}"
        except (ValueError, TypeError):
            w_diff = '—'

    waist_diff_val = '—'
    if record.get('waist_cm') and record.get('target_waist_cm'):
        try:
            waist_diff_val = f"{float(record['waist_cm']) - float(record['target_waist_cm']):.1f}"
        except (ValueError, TypeError):
            waist_diff_val = '—'

    med_detail_str = f"，{record.get('med_detail')}" if record.get('med_detail') else ''

    md = f"""# {name} · 减重报告生成任务

## 任务说明

你是一名中医减重门诊医生。请根据以下结构化数据，生成一份完整的减重体重管理报告。
报告需包含：封面、目录、体格评估、代谢与心血管风险、中医体质辨证、生活方式画像、30天行动方案、预期效果等章节。

---

## 一、基本信息

| 字段 | 值 |
|------|-----|
| 姓名 | {name} |
| 性别 | {record.get('sex', '—')} |
| 年龄 | {record.get('age', '—')}岁 |
| 报告编号 | {record.get('record_id', '—')} |
| 评估日期 | {record.get('record_date', '—')} |
| 服务包 | {path} |
| 职业 | {record.get('occupation_status', '—')} |

## 二、体格测量

| 指标 | 测量值 | 评估 |
|------|--------|------|
| 身高 | {record.get('height_cm', '—')} cm | — |
| 体重 | {record.get('weight_kg', '—')} kg | {derived.get('bmi_level', '—')} |
| BMI | {derived.get('bmi', '—')} | {derived.get('bmi_level', '—')} |
| 腰围 | {record.get('waist_cm', '—')} cm | {derived.get('waist_level', '—')} |
| 臀围 | {record.get('hip_cm', '—')} cm | — |
| 腰臀比 | {derived.get('whr', '—')} | {derived.get('whr_level', '—')} |
| 血压 | {record.get('sbp', '—')}/{record.get('dbp', '—')} mmHg | {derived.get('bp_level', '—')} |
| 静息心率 | {record.get('heart_rate', '—')} 次/分 | {derived.get('hr_level', '—')} |
| 体脂率 | {record.get('body_fat_percent', '—')}% | — |
| 内脏脂肪等级 | {record.get('visceral_fat_level', '—')} | — |

## 三、减重目标

- 本次希望改善：{list_str(record.get('selected_goals', []))}
- 目标体重：{record.get('weight_kg', '—')} → {record.get('target_weight_kg', '—')} kg（-{w_diff}kg）
- 目标腰围：{record.get('waist_cm', '—')} → {record.get('target_waist_cm', '—')} cm（-{waist_diff_val}cm）
- 既往减重经历：{record.get('past_weight_loss', '—')}

## 四、健康风险筛查

- 已知疾病/异常：{list_str(record.get('conditions', []))}
- 长期用药：{list_str(record.get('medications', []))}{med_detail_str}
- 过敏史：{list_str(record.get('allergies', []))}
- ⚠️ 红旗项：{list_str(record.get('red_positive', []))}
{female_line}
## 五、饮食与生活方式

- 外食频率：{record.get('eating_out_frequency', '—')}
- 夜宵/零食/甜饮：{record.get('night_snack_sweet_drink', '—')}
- 主食油腻：{record.get('staple_oily_food', '—')}
- 运动频率：{record.get('exercise_frequency', '—')}
- 睡眠：{record.get('sleep_status', '—')}
- 排便：{record.get('bowel_status', '—')}
- 压力进食：{record.get('stress_eating', '—')}
- 饮水：{record.get('water_intake', '—')}
- 发胖原因：{list_str(record.get('selected_gain_reasons', []))}

## 六、中医初筛

- 自觉症状：{list_str(record.get('body_feelings', []))}
- 体质倾向：{list_str(record.get('tcm_tendency', []))}
- 主要减重阻力：{list_str(record.get('main_obstacles', []))}
- 舌象：{record.get('tongue_photo_taken', '—')}
- 适合路径：{record.get('suitable_path', '—')}
- 报告闸门：{record.get('report_permission', '—')}
- 医生备注：{record.get('report_focus_note', '—')}

## 七、外治禁忌

- {list_str(record.get('external_cautions', [])) if record.get('external_cautions') else '无特殊禁忌'}

## 八、风险评分

| 维度 | 评分 |
|------|------|
{risk_table(record.get('risk_scores', {}))}

---

## 生成要求

1. 用 V17 报告模板结构生成完整报告（封面→目录→体格评估→代谢心血管风险→中医辨证→生活方式→30天方案→预期效果）
2. 中医部分必须包含：辨证分型、病机分析、证候描述、调理方向
3. 30天方案包含：日历表（第1-4周）、饮食建议、运动建议、外治建议、中药调理建议
4. 语言专业但易懂，面向用户
5. **禁止编造** 未在数据中出现的诊断/数值
6. 风险提示明确，建议就医的放在显眼位置
7. 报告使用 V17 标准颜色体系（主色#146C86、强调橙#E8833A、绿#42A36A、红#C94B4B、黄#F2B84B）

请开始生成报告。
"""
    return md


def generate_pdf_from_html(html_content):
    """从 HTML 内容生成 PDF 字节流"""
    from weasyprint import HTML
    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes

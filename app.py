"""
荟城减重 WSP 报告生成系统 - Flask 后端 API
"""
import os
import json
import io
import logging
from datetime import datetime, date
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS

from db import get_conn, serialize_row
from report_generator import (
    compute_derived, generate_report_html, generate_md, generate_pdf_from_html,
    gate_check_level1, gate_check_level2, gate_check_level3, check_missing_optional
)

# 配置日志系统
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# 创建logger
logger = logging.getLogger('wsp_app')
logger.setLevel(logging.DEBUG)

# 文件处理器 - 按日期分割,每个文件最大10MB,保留30个备份
file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, 'app.log'),
    maxBytes=10*1024*1024,  # 10MB
    backupCount=30,
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)

# 控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# 日志格式
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)


# ========== 仪表盘 ==========
@app.route('/api/dashboard')
def dashboard():
    """仪表盘统计数据"""
    conn = get_conn()
    try:
        cur = conn.cursor()
        today = date.today().isoformat()
        cur.execute("SELECT COUNT(*) AS c FROM reports WHERE DATE(record_date)=%s", (today,))
        today_count = cur.fetchone()['c']

        cur.execute("SELECT COUNT(*) AS c FROM reports WHERE status='pending'")
        pending = cur.fetchone()['c']

        cur.execute("SELECT COUNT(*) AS c FROM reports WHERE status='completed'")
        completed = cur.fetchone()['c']

        cur.execute("SELECT COUNT(*) AS c FROM reports WHERE status='blocked'")
        blocked = cur.fetchone()['c']

        # 最近记录
        cur.execute("""
            SELECT record_id, name, record_date, suitable_path, status, sex
            FROM reports ORDER BY created_at DESC LIMIT 5
        """)
        recent = []
        for r in cur.fetchall():
            recent.append({
                'record_id': r['record_id'],
                'name': r['name'],
                'record_date': str(r['record_date']),
                'suitable_path': r['suitable_path'],
                'status': r['status'],
                'sex': r['sex']
            })

        # 本周趋势 - 生成完整的7天数据
        cur.execute("""
            SELECT DATE(record_date) AS d, COUNT(*) AS c
            FROM reports
            WHERE record_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
            GROUP BY DATE(record_date)
            ORDER BY d
        """)
        trend_data = {str(r['d']): r['c'] for r in cur.fetchall()}
        
        # 生成最近7天的完整数据(包括没有数据的日期)
        from datetime import datetime, timedelta
        today = date.today()
        trend = []
        for i in range(6, -1, -1):  # 从6天前到今天
            d = today - timedelta(days=i)
            date_str = d.isoformat()
            trend.append({
                'date': date_str,
                'count': trend_data.get(date_str, 0)
            })

        return jsonify({
            'today_count': today_count,
            'pending': pending,
            'completed': completed,
            'blocked': blocked,
            'recent': recent,
            'trend': trend
        })
    finally:
        conn.close()


# ========== 报告列表 ==========
@app.route('/api/reports')
def list_reports():
    """获取报告列表"""
    keyword = request.args.get('keyword', '').strip()
    status = request.args.get('status', '').strip()
    include_test = request.args.get('include_test', 'false').lower() == 'true'  # 是否包含测试数据

    sql = """
        SELECT id, record_id, record_date, name, sex, age,
               suitable_path, status, gate_reason, created_at, updated_at
        FROM reports WHERE 1=1
    """
    params = []
    
    # 默认排除测试数据
    if not include_test:
        sql += " AND name NOT LIKE %s AND name NOT LIKE %s AND name NOT LIKE %s AND name NOT LIKE %s"
        params.extend(['%测试%', '%边界测试%', '%字符串数值测试%', '%红旗项测试%'])
    
    if keyword:
        sql += " AND (name LIKE %s OR record_id LIKE %s)"
        params.extend([f'%{keyword}%', f'%{keyword}%'])
    if status and status != '全部':
        sql += " AND status=%s"
        params.append(status)
    sql += " ORDER BY created_at DESC"

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        result = []
        for r in rows:
            result.append({
                'id': r['id'],
                'record_id': r['record_id'],
                'record_date': str(r['record_date']),
                'name': r['name'],
                'sex': r['sex'],
                'age': r['age'],
                'suitable_path': r['suitable_path'],
                'status': r['status'],
                'gate_reason': r['gate_reason'],
                'created_at': r['created_at'].strftime('%Y-%m-%d %H:%M') if r['created_at'] else None,
                'updated_at': r['updated_at'].strftime('%Y-%m-%d %H:%M') if r['updated_at'] else None,
            })
        return jsonify(result)
    finally:
        conn.close()


# ========== 报告详情 ==========
@app.route('/api/reports/<record_id>')
def get_report(record_id):
    """获取报告详情"""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM reports WHERE record_id=%s", (record_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'error': '报告不存在'}), 404

        report = serialize_row(row)
        # 计算派生值
        derived = compute_derived(report)
        report['derived'] = derived
        return jsonify(report)
    finally:
        conn.close()


# ========== 创建/更新报告 ==========
@app.route('/api/reports', methods=['POST'])
def create_report():
    """创建新报告（信息采集提交）"""
    logger.info(f"开始创建报告")
    data = request.json
    if not data:
        return jsonify({'error': '无数据'}), 400

    # 校验必填
    required = ['name', 'sex', 'age', 'height_cm', 'weight_kg']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'缺少必填字段: {", ".join(missing)}'}), 400

    # 数值范围验证
    height_cm = data.get('height_cm')
    weight_kg = data.get('weight_kg')
    waist_cm = data.get('waist_cm')
    hip_cm = data.get('hip_cm')
    sbp = data.get('sbp')
    dbp = data.get('dbp')
    heart_rate = data.get('heart_rate')
    body_fat_percent = data.get('body_fat_percent')
    visceral_fat_level = data.get('visceral_fat_level')
    target_weight_kg = data.get('target_weight_kg')
    target_waist_cm = data.get('target_waist_cm')

    # 转换为数值类型(如果存在)
    try:
        if height_cm is not None:
            height_cm = float(height_cm)
            data['height_cm'] = height_cm
        if weight_kg is not None:
            weight_kg = float(weight_kg)
            data['weight_kg'] = weight_kg
        if waist_cm is not None:
            waist_cm = float(waist_cm)
            data['waist_cm'] = waist_cm
        if hip_cm is not None:
            hip_cm = float(hip_cm)
            data['hip_cm'] = hip_cm
        if sbp is not None:
            sbp = int(sbp)
            data['sbp'] = sbp
        if dbp is not None:
            dbp = int(dbp)
            data['dbp'] = dbp
        if heart_rate is not None:
            heart_rate = int(heart_rate)
            data['heart_rate'] = heart_rate
        if body_fat_percent is not None:
            body_fat_percent = float(body_fat_percent)
            data['body_fat_percent'] = body_fat_percent
        if visceral_fat_level is not None:
            visceral_fat_level = int(visceral_fat_level)
            data['visceral_fat_level'] = visceral_fat_level
        if target_weight_kg is not None:
            target_weight_kg = float(target_weight_kg)
            data['target_weight_kg'] = target_weight_kg
        if target_waist_cm is not None:
            target_waist_cm = float(target_waist_cm)
            data['target_waist_cm'] = target_waist_cm
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'数据格式错误: {str(e)}'}), 400

    if height_cm and not (100 <= height_cm <= 250):
        return jsonify({'error': '身高应在100-250cm之间'}), 400

    if weight_kg and not (30 <= weight_kg <= 300):
        return jsonify({'error': '体重应在30-300kg之间'}), 400

    if waist_cm and hip_cm and waist_cm >= hip_cm:
        return jsonify({'error': '腰围应小于臀围'}), 400

    if sbp and not (60 <= sbp <= 250):
        return jsonify({'error': '收缩压应在60-250mmHg之间'}), 400

    if dbp and not (40 <= dbp <= 150):
        return jsonify({'error': '舒张压应在40-150mmHg之间'}), 400

    if heart_rate and not (40 <= heart_rate <= 200):
        return jsonify({'error': '心率应在40-200次/分之间'}), 400

    if body_fat_percent and not (5 <= body_fat_percent <= 60):
        return jsonify({'error': '体脂率应在5-60%之间'}), 400

    if visceral_fat_level and not (1 <= visceral_fat_level <= 59):
        return jsonify({'error': '内脏脂肪等级应在1-59之间'}), 400

    if target_weight_kg and weight_kg and target_weight_kg >= weight_kg:
        return jsonify({'error': '目标体重应小于当前体重'}), 400

    if target_waist_cm and waist_cm and target_waist_cm >= waist_cm:
        return jsonify({'error': '目标腰围应小于当前腰围'}), 400

    # 生成 record_id
    record_id = data.get('record_id')
    if not record_id:
        today = datetime.now().strftime('%Y%m%d')
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) AS c FROM reports WHERE record_id LIKE %s", (f'HC-{today}-%',))
            count = cur.fetchone()['c']
            record_id = f"HC-{today}-{count + 1:03d}"
        finally:
            conn.close()
    data['record_id'] = record_id
    data['record_date'] = data.get('record_date', date.today().isoformat())

    # 计算派生值
    derived = compute_derived(data)
    logger.debug(f"计算派生值完成")

    # 执行三级闸门检查
    level1_pass, level1_msg = gate_check_level1(data)
    level2_pass, level2_msg = gate_check_level2(data, derived)
    level3_pass, level3_msg = gate_check_level3(data, derived)
    logger.debug(f"闸门检查: L1={level1_pass}, L2={level2_pass}, L3={level3_pass}")

    # 综合判断
    if not level1_pass:
        data['status'] = 'blocked'
        data['gate_reason'] = level1_msg
        gate_status = 'block'
    elif not level3_pass:
        data['status'] = 'blocked'
        data['gate_reason'] = level3_msg
        gate_status = 'block'
    elif not level2_pass:
        data['status'] = 'pending'  # 警告但不阻断
        data['gate_reason'] = level2_msg
        gate_status = 'warn'
    else:
        # 检查缺失非必填字段
        missing_optional = check_missing_optional(data)
        if missing_optional:
            data['status'] = 'pending'
            data['gate_reason'] = f"闸门警告 · 缺失非必填项：{'、'.join(missing_optional)}"
            gate_status = 'warn'
        else:
            data['status'] = 'pending'
            gate_status = 'pass'

    # 生成报告 HTML 和 MD 内容
    try:
        html_content = generate_report_html(data, derived)
        md_content = generate_md(data, derived)
        logger.info(f"报告内容生成成功")
    except Exception as e:
        logger.error(f"报告内容生成失败: {str(e)}", exc_info=True)
        raise

    # 写入数据库
    conn = get_conn()
    try:
        cur = conn.cursor()
        sql = """
            INSERT INTO reports (
                record_id, record_date, name, sex, age, occupation_status,
                height_cm, weight_kg, waist_cm, hip_cm, sbp, dbp, heart_rate,
                body_fat_percent, visceral_fat_level, target_weight_kg, target_waist_cm,
                past_weight_loss, eating_out_frequency, night_snack_sweet_drink, staple_oily_food,
                exercise_frequency, sleep_status, bowel_status, stress_eating, water_intake,
                suitable_path, report_permission, report_focus_note, female_status,
                tongue_photo_taken, med_detail,
                bmi, whr, bmi_level, bp_level, waist_level, whr_level, hr_level,
                selected_goals, selected_gain_reasons, conditions, medications, allergies,
                red_positive, body_feelings, tcm_tendency, main_obstacles, external_cautions,
                risk_scores, status, gate_reason, content, md_content, template_version
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
        """
        params = (
            record_id, data['record_date'], data['name'], data['sex'], data['age'],
            data.get('occupation_status'),
            data.get('height_cm'), data.get('weight_kg'), data.get('waist_cm'), data.get('hip_cm'),
            data.get('sbp'), data.get('dbp'), data.get('heart_rate'),
            data.get('body_fat_percent'), data.get('visceral_fat_level'),
            data.get('target_weight_kg'), data.get('target_waist_cm'),
            data.get('past_weight_loss'), data.get('eating_out_frequency'),
            data.get('night_snack_sweet_drink'), data.get('staple_oily_food'),
            data.get('exercise_frequency'), data.get('sleep_status'),
            data.get('bowel_status'), data.get('stress_eating'), data.get('water_intake'),
            data.get('suitable_path', '全程版'), '可以生成' if gate_status == 'pass' else ('阻断' if gate_status == 'block' else '警告'),
            data.get('report_focus_note'), data.get('female_status'),
            data.get('tongue_photo_taken'), data.get('med_detail'),
            derived.get('bmi'), derived.get('whr'), derived.get('bmi_level'),
            derived.get('bp_level'), derived.get('waist_level'),
            derived.get('whr_level'), derived.get('hr_level'),
            json.dumps(data.get('selected_goals', []), ensure_ascii=False),
            json.dumps(data.get('selected_gain_reasons', []), ensure_ascii=False),
            json.dumps(data.get('conditions', []), ensure_ascii=False),
            json.dumps(data.get('medications', []), ensure_ascii=False),
            json.dumps(data.get('allergies', []), ensure_ascii=False),
            json.dumps(data.get('red_positive', []), ensure_ascii=False),
            json.dumps(data.get('body_feelings', []), ensure_ascii=False),
            json.dumps(data.get('tcm_tendency', []), ensure_ascii=False),
            json.dumps(data.get('main_obstacles', []), ensure_ascii=False),
            json.dumps(data.get('external_cautions', []), ensure_ascii=False),
            json.dumps(data.get('risk_scores', {}), ensure_ascii=False),
            data['status'], data.get('gate_reason'),
            html_content, md_content, 'V17'
        )
        cur.execute(sql, params)

        # 写入闸门日志（使用前面计算的gate_status）
        if gate_status == 'block':
            gate_detail = data.get('gate_reason', '闸门阻断')
        elif gate_status == 'warn':
            gate_detail = data.get('gate_reason', '闸门警告')
        else:
            gate_detail = '闸门通过 · 可以生成'

        cur.execute("""
            INSERT INTO gate_logs (record_id, name, gate_status, gate_detail)
            VALUES (%s, %s, %s, %s)
        """, (record_id, data['name'], gate_status, gate_detail))

        return jsonify({
            'success': True,
            'record_id': record_id,
            'status': data['status'],
            'gate_reason': data.get('gate_reason'),
            'message': '报告已保存' + ('，闸门已阻断' if data['status'] == 'blocked' else '')
        })
    except Exception as e:
        logger.error(f"创建报告异常: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# ========== 重新生成报告内容 ==========
@app.route('/api/reports/<record_id>/generate', methods=['POST'])
def regenerate_report(record_id):
    """重新生成报告内容并更新状态"""
    logger.info(f"开始生成报告: {record_id}")
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM reports WHERE record_id=%s", (record_id,))
        row = cur.fetchone()
        if not row:
            logger.error(f"报告不存在: {record_id}")
            return jsonify({'error': '报告不存在'}), 404

        logger.debug(f"获取报告数据成功")
        report = serialize_row(row)
        derived = compute_derived(report)
        logger.debug(f"计算派生值成功")

        # 执行三级闸门检查
        level1_pass, level1_msg = gate_check_level1(report)
        level2_pass, level2_msg = gate_check_level2(report, derived)
        level3_pass, level3_msg = gate_check_level3(report, derived)
        logger.debug(f"闸门检查: L1={level1_pass}, L2={level2_pass}, L3={level3_pass}")

        # 生成报告内容
        try:
            html_content = generate_report_html(report, derived)
            md_content = generate_md(report, derived)
            logger.info(f"报告内容生成成功")
        except Exception as e:
            logger.error(f"报告内容生成失败: {str(e)}", exc_info=True)
            raise

        # 综合判断状态
        if not level1_pass:
            new_status = 'blocked'
            gate_reason = level1_msg
            gate_status = 'block'
        elif not level3_pass:
            new_status = 'blocked'
            gate_reason = level3_msg
            gate_status = 'block'
        elif not level2_pass:
            new_status = 'completed'  # 警告但不阻断
            gate_reason = level2_msg
            gate_status = 'warn'
        else:
            # 检查缺失非必填字段
            missing_optional = check_missing_optional(report)
            if missing_optional:
                new_status = 'completed'
                gate_reason = f"闸门警告 · 缺失非必填项：{'、'.join(missing_optional)}"
                gate_status = 'warn'
            else:
                new_status = 'completed'
                gate_reason = None
                gate_status = 'pass'
        cur.execute("""
            UPDATE reports SET content=%s, md_content=%s, status=%s, gate_reason=%s,
            bmi=%s, whr=%s, bmi_level=%s, bp_level=%s, waist_level=%s, whr_level=%s, hr_level=%s
            WHERE record_id=%s
        """, (html_content, md_content, new_status, gate_reason,
              derived.get('bmi'), derived.get('whr'), derived.get('bmi_level'),
              derived.get('bp_level'), derived.get('waist_level'),
              derived.get('whr_level'), derived.get('hr_level'), record_id))

        # 写入闸门日志
        if gate_status == 'block':
            gate_detail = gate_reason or '闸门阻断'
        elif gate_status == 'warn':
            gate_detail = gate_reason or '闸门警告'
        else:
            gate_detail = '闸门通过 · 报告重新生成'

        cur.execute("""
            INSERT INTO gate_logs (record_id, name, gate_status, gate_detail)
            VALUES (%s, %s, %s, %s)
        """, (record_id, report.get('name'), gate_status, gate_detail))

        return jsonify({
            'success': True,
            'status': new_status,
            'gate_status': gate_status,
            'message': '报告已生成' + ('，闸门已阻断' if new_status == 'blocked' else '')
        })
    except Exception as e:
        logger.error(f"报告生成异常: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# ========== 下载 PDF ==========
@app.route('/api/reports/<record_id>/pdf')
def download_pdf(record_id):
    """生成并下载 PDF 报告"""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM reports WHERE record_id=%s", (record_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'error': '报告不存在'}), 404

        report = serialize_row(row)

        # 如果有已生成的 content 直接用，否则重新生成
        if report.get('content'):
            html_content = report['content']
        else:
            derived = compute_derived(report)
            html_content = generate_report_html(report, derived)

        # 生成 PDF
        pdf_bytes = generate_pdf_from_html(html_content)

        filename = f"{record_id}_{report['name']}_报告.pdf"
        from urllib.parse import quote
        encoded_filename = quote(filename)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# ========== 下载 MD ==========
@app.route('/api/reports/<record_id>/md')
def download_md(record_id):
    """生成并下载 MD 报告"""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM reports WHERE record_id=%s", (record_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'error': '报告不存在'}), 404

        report = serialize_row(row)

        # 如果有已生成的 md_content 直接用，否则重新生成
        if report.get('md_content'):
            md_content = report['md_content']
        else:
            derived = compute_derived(report)
            md_content = generate_md(report, derived)

        filename = f"{record_id}_{report['name']}_给LLM生成报告.md"
        from urllib.parse import quote
        encoded_filename = quote(filename)
        return Response(
            md_content,
            mimetype='text/markdown; charset=utf-8',
            headers={'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_filename}"}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# ========== 闸门日志 ==========
@app.route('/api/gate-logs')
def gate_logs():
    """获取闸门日志"""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM gate_logs ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
        result = []
        for r in rows:
            result.append({
                'id': r['id'],
                'record_id': r['record_id'],
                'name': r['name'],
                'gate_status': r['gate_status'],
                'gate_detail': r['gate_detail'],
                'created_at': r['created_at'].strftime('%Y-%m-%d %H:%M') if r['created_at'] else None,
            })
        return jsonify(result)
    finally:
        conn.close()


# ========== 按报告ID查询闸门日志 ==========
@app.route('/api/reports/<record_id>/gate-logs')
def report_gate_logs(record_id):
    """获取指定报告的闸门日志历史"""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM gate_logs WHERE record_id=%s ORDER BY created_at DESC
        """, (record_id,))
        rows = cur.fetchall()
        result = []
        for r in rows:
            result.append({
                'id': r['id'],
                'record_id': r['record_id'],
                'name': r['name'],
                'gate_status': r['gate_status'],
                'gate_detail': r['gate_detail'],
                'created_at': r['created_at'].strftime('%Y-%m-%d %H:%M:%S') if r['created_at'] else None,
            })
        return jsonify(result)
    finally:
        conn.close()
@app.route('/api/templates')
def list_templates():
    """获取模板列表"""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, version, name, description, status,
                   created_at, updated_at,
                   LEFT(content, 200) AS content_preview
            FROM templates ORDER BY status='active' DESC, created_at DESC
        """)
        rows = cur.fetchall()
        result = []
        for r in rows:
            result.append({
                'id': r['id'],
                'version': r['version'],
                'name': r['name'],
                'description': r['description'],
                'status': r['status'],
                'created_at': r['created_at'].strftime('%Y-%m-%d') if r['created_at'] else None,
                'updated_at': r['updated_at'].strftime('%Y-%m-%d') if r['updated_at'] else None,
                'content_preview': r['content_preview'],
            })
        return jsonify(result)
    finally:
        conn.close()


@app.route('/api/templates/<int:tid>')
def get_template(tid):
    """获取模板详情"""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM templates WHERE id=%s", (tid,))
        row = cur.fetchone()
        if not row:
            return jsonify({'error': '模板不存在'}), 404
        return jsonify(serialize_row(row))
    finally:
        conn.close()


@app.route('/api/templates', methods=['POST'])
def create_template():
    """创建新模板"""
    data = request.json
    if not data or not data.get('version') or not data.get('name') or not data.get('content'):
        return jsonify({'error': '缺少必填字段: version, name, content'}), 400

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO templates (version, name, description, content, color_scheme, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            data['version'], data['name'], data.get('description', ''),
            data['content'],
            json.dumps(data.get('color_scheme', {}), ensure_ascii=False),
            data.get('status', 'archived')
        ))
        return jsonify({'success': True, 'id': cur.lastrowid, 'message': '模板创建成功'})
    except Exception as e:
        if 'Duplicate' in str(e):
            return jsonify({'error': '模板版本号已存在'}), 400
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/templates/<int:tid>', methods=['PUT'])
def update_template(tid):
    """更新模板"""
    data = request.json
    if not data:
        return jsonify({'error': '无数据'}), 400

    conn = get_conn()
    try:
        cur = conn.cursor()
        fields = []
        params = []
        for field in ['version', 'name', 'description', 'content', 'status']:
            if field in data:
                fields.append(f"{field}=%s")
                params.append(data[field])
        if 'color_scheme' in data:
            fields.append("color_scheme=%s")
            params.append(json.dumps(data['color_scheme'], ensure_ascii=False))
        if not fields:
            return jsonify({'error': '无更新字段'}), 400

        params.append(tid)
        cur.execute(f"UPDATE templates SET {', '.join(fields)} WHERE id=%s", params)
        return jsonify({'success': True, 'message': '模板更新成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/templates/<int:tid>/activate', methods=['POST'])
def activate_template(tid):
    """激活模板（设为使用中，其他设为归档）"""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE templates SET status='archived' WHERE status='active'")
        cur.execute("UPDATE templates SET status='active' WHERE id=%s", (tid,))
        return jsonify({'success': True, 'message': '模板已激活'})
    finally:
        conn.close()


@app.route('/api/templates/<int:tid>', methods=['DELETE'])
def delete_template(tid):
    """删除模板"""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT status FROM templates WHERE id=%s", (tid,))
        row = cur.fetchone()
        if not row:
            return jsonify({'error': '模板不存在'}), 404
        if row['status'] == 'active':
            return jsonify({'error': '不能删除使用中的模板'}), 400
        cur.execute("DELETE FROM templates WHERE id=%s", (tid,))
        return jsonify({'success': True, 'message': '模板已删除'})
    finally:
        conn.close()


# ========== 日志管理 ==========
@app.route('/api/logs')
def get_logs():
    """获取日志列表，支持过滤"""
    try:
        # 获取查询参数
        level = request.args.get('level', '').upper()  # DEBUG, INFO, WARNING, ERROR
        start_date = request.args.get('start_date', '')  # YYYY-MM-DD
        end_date = request.args.get('end_date', '')  # YYYY-MM-DD
        limit = int(request.args.get('limit', 100))  # 默认100条
        
        log_file = os.path.join(LOG_DIR, 'app.log')
        logs = []
        
        if not os.path.exists(log_file):
            return jsonify([])
        
        # 读取日志文件
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 解析日志
        for line in reversed(lines):  # 从最新的开始
            line = line.strip()
            if not line:
                continue
            
            # 解析日志格式: 2026-06-18 12:11:45 [INFO] message
            try:
                # 提取时间戳和级别
                parts = line.split(' [', 1)
                if len(parts) < 2:
                    continue
                
                timestamp_str = parts[0]
                rest = parts[1]
                
                bracket_end = rest.find(']')
                if bracket_end == -1:
                    continue
                
                log_level = rest[:bracket_end]
                message = rest[bracket_end+2:]  # 跳过 '] '
                
                # 级别过滤
                if level and log_level != level:
                    continue
                
                # 日期过滤
                if start_date or end_date:
                    log_date = timestamp_str.split(' ')[0]
                    if start_date and log_date < start_date:
                        continue
                    if end_date and log_date > end_date:
                        continue
                
                logs.append({
                    'timestamp': timestamp_str,
                    'level': log_level,
                    'message': message
                })
                
                # 限制返回数量
                if len(logs) >= limit:
                    break
                    
            except Exception:
                continue
        
        # 反转回正序（从旧到新）
        logs.reverse()
        
        return jsonify(logs)
        
    except Exception as e:
        logger.error(f"获取日志失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/logs/levels')
def get_log_levels():
    """获取日志级别统计"""
    try:
        log_file = os.path.join(LOG_DIR, 'app.log')
        stats = {'DEBUG': 0, 'INFO': 0, 'WARNING': 0, 'ERROR': 0}
        
        if not os.path.exists(log_file):
            return jsonify(stats)
        
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if '[DEBUG]' in line:
                    stats['DEBUG'] += 1
                elif '[INFO]' in line:
                    stats['INFO'] += 1
                elif '[WARNING]' in line:
                    stats['WARNING'] += 1
                elif '[ERROR]' in line:
                    stats['ERROR'] += 1
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"获取日志统计失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/logs/clear', methods=['POST'])
def clear_logs():
    """清空日志文件"""
    try:
        log_file = os.path.join(LOG_DIR, 'app.log')
        if os.path.exists(log_file):
            open(log_file, 'w').close()
            logger.info("日志已清空")
        return jsonify({'success': True, 'message': '日志已清空'})
    except Exception as e:
        logger.error(f"清空日志失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ========== 静态文件 ==========
@app.route('/')
def index():
    return app.send_static_file('index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

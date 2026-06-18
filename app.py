"""
荟城减重 WSP 报告生成系统 - Flask 后端 API
"""
import os
import json
import io
from datetime import datetime, date
from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS

from db import get_conn, serialize_row
from report_generator import (
    compute_derived, generate_report_html, generate_md, generate_pdf_from_html
)

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

        # 本周趋势
        cur.execute("""
            SELECT DATE(record_date) AS d, COUNT(*) AS c
            FROM reports
            WHERE record_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            GROUP BY DATE(record_date)
            ORDER BY d
        """)
        trend = [{'date': str(r['d']), 'count': r['c']} for r in cur.fetchall()]

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

    sql = """
        SELECT id, record_id, record_date, name, sex, age,
               suitable_path, status, gate_reason, created_at, updated_at
        FROM reports WHERE 1=1
    """
    params = []
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
    data = request.json
    if not data:
        return jsonify({'error': '无数据'}), 400

    # 校验必填
    required = ['name', 'sex', 'age', 'height_cm', 'weight_kg']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'缺少必填字段: {", ".join(missing)}'}), 400

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

    # 闸门判断
    red_flags = data.get('red_positive', [])
    if red_flags and len(red_flags) > 0:
        data['report_permission'] = '阻断'
        data['status'] = 'blocked'
        data['gate_reason'] = f"红旗项：{'、'.join(red_flags)}"
    else:
        data['report_permission'] = '可以生成'
        data['status'] = 'pending'
        data['gate_reason'] = None

    # 生成报告 HTML 和 MD 内容
    html_content = generate_report_html(data, derived)
    md_content = generate_md(data, derived)

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
            data.get('suitable_path', '全程版'), data['report_permission'],
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

        # 写入闸门日志
        if data['status'] == 'blocked':
            gate_status = 'block'
            gate_detail = data.get('gate_reason', '闸门阻断')
        else:
            # 检测缺失非必填字段，产生 warn
            missing_optional = []
            optional_fields = {
                'body_fat_percent': '体脂率', 'visceral_fat_level': '内脏脂肪等级',
                'sbp': '收缩压', 'dbp': '舒张压', 'heart_rate': '静息心率',
                'hip_cm': '臀围', 'target_weight_kg': '目标体重',
                'waist_cm': '腰围'
            }
            for field, label in optional_fields.items():
                if not data.get(field):
                    missing_optional.append(label)
            if missing_optional:
                gate_status = 'warn'
                gate_detail = f"闸门警告 · 缺失非必填项：{'、'.join(missing_optional)}"
            else:
                gate_status = 'pass'
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
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# ========== 重新生成报告内容 ==========
@app.route('/api/reports/<record_id>/generate', methods=['POST'])
def regenerate_report(record_id):
    """重新生成报告内容并更新状态"""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM reports WHERE record_id=%s", (record_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'error': '报告不存在'}), 404

        report = serialize_row(row)
        derived = compute_derived(report)

        html_content = generate_report_html(report, derived)
        md_content = generate_md(report, derived)

        # 更新报告内容和状态
        new_status = 'blocked' if derived.get('gate_blocked') else 'completed'
        cur.execute("""
            UPDATE reports SET content=%s, md_content=%s, status=%s, gate_reason=%s,
            bmi=%s, whr=%s, bmi_level=%s, bp_level=%s, waist_level=%s, whr_level=%s, hr_level=%s
            WHERE record_id=%s
        """, (html_content, md_content, new_status, derived.get('gate_reason'),
              derived.get('bmi'), derived.get('whr'), derived.get('bmi_level'),
              derived.get('bp_level'), derived.get('waist_level'),
              derived.get('whr_level'), derived.get('hr_level'), record_id))

        # 写入闸门日志（重新生成时也记录）
        if derived.get('gate_blocked'):
            gate_status = 'block'
            gate_detail = derived.get('gate_reason', '闸门阻断')
        else:
            # 检测缺失非必填字段，产生 warn
            missing_optional = []
            optional_fields = {
                'body_fat_percent': '体脂率', 'visceral_fat_level': '内脏脂肪等级',
                'sbp': '收缩压', 'dbp': '舒张压', 'heart_rate': '静息心率',
                'hip_cm': '臀围', 'target_weight_kg': '目标体重'
            }
            for field, label in optional_fields.items():
                if not report.get(field):
                    missing_optional.append(label)
            if missing_optional:
                gate_status = 'warn'
                gate_detail = f"闸门警告 · 缺失非必填项：{'、'.join(missing_optional)}（报告已生成）"
            else:
                gate_status = 'pass'
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


# ========== 静态文件 ==========
@app.route('/')
def index():
    return app.send_static_file('index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

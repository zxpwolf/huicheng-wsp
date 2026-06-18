-- 荟城减重 WSP 报告生成系统 数据库结构
CREATE DATABASE IF NOT EXISTS huicheng_wsp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE huicheng_wsp;

-- ========== 报告表 ==========
CREATE TABLE IF NOT EXISTS reports (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    record_id       VARCHAR(50)  NOT NULL UNIQUE COMMENT '报告编号',
    record_date     DATE         NOT NULL COMMENT '评估日期',
    name            VARCHAR(50)  NOT NULL COMMENT '姓名',
    sex             VARCHAR(10)  NOT NULL COMMENT '性别',
    age             INT          NOT NULL COMMENT '年龄',
    occupation_status VARCHAR(100) DEFAULT NULL COMMENT '职业/活动状态',

    -- 体格测量
    height_cm       DECIMAL(5,1) DEFAULT NULL,
    weight_kg       DECIMAL(5,1) DEFAULT NULL,
    waist_cm        DECIMAL(5,1) DEFAULT NULL,
    hip_cm          DECIMAL(5,1) DEFAULT NULL,
    sbp             INT          DEFAULT NULL COMMENT '收缩压',
    dbp             INT          DEFAULT NULL COMMENT '舒张压',
    heart_rate      INT          DEFAULT NULL COMMENT '静息心率',
    body_fat_percent DECIMAL(5,1) DEFAULT NULL,
    visceral_fat_level VARCHAR(10) DEFAULT NULL,

    -- 目标
    target_weight_kg DECIMAL(5,1) DEFAULT NULL,
    target_waist_cm  DECIMAL(5,1) DEFAULT NULL,
    past_weight_loss VARCHAR(100) DEFAULT NULL,

    -- 生活方式
    eating_out_frequency  VARCHAR(100) DEFAULT NULL,
    night_snack_sweet_drink VARCHAR(100) DEFAULT NULL,
    staple_oily_food      VARCHAR(100) DEFAULT NULL,
    exercise_frequency    VARCHAR(100) DEFAULT NULL,
    sleep_status          VARCHAR(100) DEFAULT NULL,
    bowel_status          VARCHAR(100) DEFAULT NULL,
    stress_eating         VARCHAR(100) DEFAULT NULL,
    water_intake          VARCHAR(100) DEFAULT NULL,

    -- 路径与闸门
    suitable_path       VARCHAR(50)  DEFAULT NULL,
    report_permission   VARCHAR(50)  DEFAULT '可以生成' COMMENT '闸门判断',
    report_focus_note   TEXT         DEFAULT NULL COMMENT '医生备注',
    female_status       VARCHAR(100) DEFAULT NULL,
    tongue_photo_taken  VARCHAR(20)  DEFAULT NULL,
    med_detail          VARCHAR(200) DEFAULT NULL,

    -- 派生计算值
    bmi         DECIMAL(4,1) DEFAULT NULL,
    whr         DECIMAL(3,2) DEFAULT NULL,
    bmi_level   VARCHAR(50)  DEFAULT NULL,
    bp_level    VARCHAR(50)  DEFAULT NULL,
    waist_level VARCHAR(50)  DEFAULT NULL,
    whr_level   VARCHAR(50)  DEFAULT NULL,
    hr_level    VARCHAR(50)  DEFAULT NULL,

    -- 多选字段 (JSON)
    selected_goals        JSON DEFAULT NULL,
    selected_gain_reasons JSON DEFAULT NULL,
    conditions            JSON DEFAULT NULL,
    medications           JSON DEFAULT NULL,
    allergies             JSON DEFAULT NULL,
    red_positive          JSON DEFAULT NULL,
    body_feelings         JSON DEFAULT NULL,
    tcm_tendency          JSON DEFAULT NULL,
    main_obstacles        JSON DEFAULT NULL,
    external_cautions     JSON DEFAULT NULL,
    risk_scores           JSON DEFAULT NULL,

    -- 状态与内容
    status       VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'pending=待生成, completed=已完成, blocked=已阻断',
    gate_reason  VARCHAR(200) DEFAULT NULL COMMENT '闸门阻断原因',
    content      LONGTEXT     DEFAULT NULL COMMENT '报告HTML内容',
    md_content   LONGTEXT     DEFAULT NULL COMMENT 'MD内容',
    template_version VARCHAR(20) DEFAULT 'V17',

    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_status (status),
    INDEX idx_name (name),
    INDEX idx_record_date (record_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========== 模板表 ==========
CREATE TABLE IF NOT EXISTS templates (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    version     VARCHAR(20)  NOT NULL UNIQUE COMMENT '模板版本号',
    name        VARCHAR(100) NOT NULL COMMENT '模板名称',
    description TEXT         DEFAULT NULL,
    content     LONGTEXT     NOT NULL COMMENT 'HTML模板内容',
    color_scheme JSON        DEFAULT NULL COMMENT '颜色配置',
    status      VARCHAR(20)  NOT NULL DEFAULT 'archived' COMMENT 'active=使用中, archived=归档',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========== 闸门日志表 ==========
CREATE TABLE IF NOT EXISTS gate_logs (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    record_id   VARCHAR(50)  NOT NULL,
    name        VARCHAR(50)  DEFAULT NULL,
    gate_status VARCHAR(20)  NOT NULL COMMENT 'pass=通过, block=阻断, warn=警告',
    gate_detail TEXT         DEFAULT NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_record_id (record_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========== 初始模板数据 (V17) ==========
INSERT INTO templates (version, name, description, content, color_scheme, status) VALUES
('V17', 'V17 标准模板', '当前使用的标准报告模板', '<div class="report">{{content}}</div>',
 JSON_OBJECT('primary','#146C86','accent_orange','#E8833A','accent_green','#42A36A','accent_red','#C94B4B','accent_yellow','#F2B84B'),
 'active'),
('V16', 'V16 标准模板', '已归档的旧版模板', '<div class="report-v16">{{content}}</div>',
 JSON_OBJECT('primary','#146C86','accent_orange','#E8833A','accent_green','#42A36A','accent_red','#C94B4B','accent_yellow','#F2B84B'),
 'archived'),
('V15', 'V15 简版模板', '精简版报告模板', '<div class="report-v15">{{content}}</div>',
 JSON_OBJECT('primary','#146C86','accent_orange','#E8833A','accent_green','#42A36A','accent_red','#C94B4B','accent_yellow','#F2B84B'),
 'archived')
ON DUPLICATE KEY UPDATE version=version;

-- ========== 示例报告数据 ==========
INSERT INTO reports (
    record_id, record_date, name, sex, age, occupation_status,
    height_cm, weight_kg, waist_cm, hip_cm, sbp, dbp, heart_rate,
    body_fat_percent, visceral_fat_level, target_weight_kg, target_waist_cm,
    past_weight_loss, eating_out_frequency, night_snack_sweet_drink, staple_oily_food,
    exercise_frequency, sleep_status, bowel_status, stress_eating, water_intake,
    suitable_path, report_permission, report_focus_note, tongue_photo_taken,
    bmi, whr, bmi_level, bp_level, waist_level, whr_level, hr_level,
    selected_goals, conditions, medications, allergies, red_positive,
    body_feelings, tcm_tendency, main_obstacles, external_cautions, risk_scores,
    status, gate_reason
) VALUES
(
    'HC-20260615-001', '2026-06-15', '张三', '男', 42, '久坐办公',
    175.0, 88.5, 98.0, 104.0, 138, 86, 78,
    32.1, '10', 78.0, 88.0,
    '成功过但反弹', '每周3-5次', '每周3次以上', '两者都偏多',
    '很少运动', '经常熬夜', '2-3天一次', '明显', '偏少',
    '全程版', '可以生成', '腰腹型肥胖，先控夜宵作息', '已拍',
    28.9, 0.94, '肥胖Ⅰ级', '正常高值', '超标（≥90cm）', '偏高', '正常',
    JSON_ARRAY('减重','减腰围','改善代谢','改善排便'),
    JSON_ARRAY('高血压前期','脂肪肝'),
    JSON_ARRAY('降压药'),
    JSON_ARRAY('无'),
    JSON_ARRAY(),
    JSON_ARRAY('怕冷','疲劳','口苦粘腻','睡眠差'),
    JSON_ARRAY('痰湿质','肝郁质'),
    JSON_ARRAY('热量摄入','久坐不动','反复反弹','腹型肥胖'),
    JSON_ARRAY('无禁忌'),
    JSON_OBJECT('代谢风险',4,'心血管风险',3,'执行难度',3,'反弹风险',4),
    'completed', NULL
),
(
    'HC-20260615-002', '2026-06-15', '李四', '男', 35, '轻度活动',
    170.0, 82.0, 92.0, 98.0, 125, 82, 72,
    28.0, '9', 72.0, 85.0,
    '尝试过没效果', '每周1-2次', '每周1-2次', '主食偏多',
    '每周1-2次', '偶尔熬夜', '1-2天一次', '偶尔', '一般',
    '轻享版', '可以生成', '轻度超重，加强运动', '未拍',
    28.4, 0.94, '肥胖Ⅰ级', '正常高值', '超标（≥90cm）', '偏高', '正常',
    JSON_ARRAY('减重','降体脂'),
    JSON_ARRAY(),
    JSON_ARRAY(),
    JSON_ARRAY('无'),
    JSON_ARRAY(),
    JSON_ARRAY('疲劳'),
    JSON_ARRAY('痰湿质'),
    JSON_ARRAY('久坐不动'),
    JSON_ARRAY('无禁忌'),
    JSON_OBJECT('代谢风险',2,'心血管风险',2,'执行难度',2,'反弹风险',2),
    'pending', NULL
),
(
    'HC-20260614-003', '2026-06-14', '王五', '男', 50, '久坐办公',
    172.0, 95.0, 105.0, 108.0, 155, 98, 88,
    35.0, '14', 80.0, 95.0,
    '从未减过', '几乎每天外食', '几乎每天', '两者都偏多',
    '很少运动', '严重失眠', '3天以上一次', '非常明显', '很少喝水',
    '全程版', '阻断', '高血压2级+红旗项，建议就医', '未拍',
    32.1, 0.97, '肥胖Ⅱ级', '高血压2级', '超标（≥90cm）', '偏高', '正常',
    JSON_ARRAY('减重','减腰围','改善代谢'),
    JSON_ARRAY('高血压','心血管疾病'),
    JSON_ARRAY('降压药'),
    JSON_ARRAY('无'),
    JSON_ARRAY('胸痛胸闷','血压严重异常'),
    JSON_ARRAY('怕冷','疲劳','水肿','睡眠差','急躁易怒'),
    JSON_ARRAY('痰湿质','阳虚质','血瘀质'),
    JSON_ARRAY('热量摄入','久坐不动','腹型肥胖','代谢偏低'),
    JSON_ARRAY('血压禁忌'),
    JSON_OBJECT('代谢风险',5,'心血管风险',5,'执行难度',4,'反弹风险',4),
    'blocked', '红旗项：胸痛胸闷、血压严重异常；血压155/98mmHg属高血压2级'
),
(
    'HC-20260613-004', '2026-06-13', '赵六', '女', 38, '轻度活动',
    162.0, 68.0, 82.0, 96.0, 118, 75, 70,
    30.0, '7', 58.0, 75.0,
    '成功过但反弹', '每周1-2次', '基本不吃', '主食偏多',
    '每周3-5次', '偶尔熬夜', '每天1-2次', '不明显', '充足（≥2000ml）',
    '轻享版', '可以生成', '产后发胖，腰围偏高', '已拍',
    25.9, 0.85, '超重', '正常', '临界', '偏高', '正常',
    JSON_ARRAY('减腰围','改善代谢','排便/水肿'),
    JSON_ARRAY(),
    JSON_ARRAY(),
    JSON_ARRAY('无'),
    JSON_ARRAY(),
    JSON_ARRAY('怕冷','水肿'),
    JSON_ARRAY('阳虚质'),
    JSON_ARRAY('反复反弹','腹型肥胖'),
    JSON_ARRAY('无禁忌'),
    JSON_OBJECT('代谢风险',2,'心血管风险',1,'执行难度',2,'反弹风险',3),
    'completed', NULL
),
(
    'HC-20260612-005', '2026-06-12', '钱七', '女', 45, '退休居家',
    160.0, 72.0, 88.0, 100.0, 128, 82, 76,
    33.5, '8', 60.0, 80.0,
    '尝试过没效果', '每周3-5次', '每周3次以上', '油腻偏多',
    '很少运动', '经常熬夜', '2-3天一次', '明显', '偏少',
    '全程版', '可以生成', '体脂率偏高，需控制饮食', '已拍',
    28.1, 0.88, '肥胖Ⅰ级', '正常高值', '超标（≥85cm）', '偏高', '正常',
    JSON_ARRAY('减重','减腰围','降体脂','改善代谢'),
    JSON_ARRAY('血脂异常'),
    JSON_ARRAY('降脂药'),
    JSON_ARRAY('无'),
    JSON_ARRAY(),
    JSON_ARRAY('疲劳','口苦粘腻','痰多苔厚'),
    JSON_ARRAY('痰湿质','湿热质'),
    JSON_ARRAY('热量摄入','久坐不动','腹型肥胖'),
    JSON_ARRAY('无禁忌'),
    JSON_OBJECT('代谢风险',3,'心血管风险',2,'执行难度',3,'反弹风险',3),
    'completed', NULL
);

-- ========== 闸门日志初始数据 ==========
INSERT INTO gate_logs (record_id, name, gate_status, gate_detail) VALUES
('HC-20260615-001', '张三', 'pass', '闸门通过 · 可以生成'),
('HC-20260615-002', '李四', 'pass', '闸门通过 · 可以生成'),
('HC-20260614-003', '王五', 'block', '闸门阻断 · 红旗项：胸痛胸闷、血压严重异常'),
('HC-20260613-004', '赵六', 'pass', '闸门通过 · 可以生成'),
('HC-20260612-005', '钱七', 'warn', '闸门警告 · 缺失必填项：体脂率已补填');

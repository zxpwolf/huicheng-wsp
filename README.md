# 荟城减重 WSP 报告生成系统

## 项目结构

```
huicheng-wsp/
├── app.py                # Flask 后端主应用（API 服务）
├── db.py                 # MySQL 数据库连接模块
├── report_generator.py   # 报告生成模块（PDF + MD）
├── schema.sql            # 数据库建表脚本（含初始数据）
├── index.html            # 前端页面（HTML5 移动端适配）
└── README.md             # 本文件
```

## 技术栈

- **后端**: Python 3 + Flask + PyMySQL
- **数据库**: MySQL 8.0
- **PDF生成**: WeasyPrint
- **前端**: 原生 HTML5 + CSS + JavaScript（无框架依赖）

## 本地部署步骤

### 1. 安装 MySQL 并初始化数据库

```bash
mysql -u root -p < schema.sql
```

> 如需修改数据库连接配置，编辑 `db.py` 中的 `DB_CONFIG`。

### 2. 安装 Python 依赖

```bash
pip install flask flask-cors pymysql weasyprint
```

### 3. 启动后端服务

```bash
python app.py
```

服务启动在 `http://localhost:5000`，前端页面和 API 均通过此端口访问。

### 4. 访问系统

浏览器打开 `http://localhost:5000` 即可使用。

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/dashboard | 仪表盘统计 |
| GET | /api/reports | 报告列表（支持搜索/筛选） |
| GET | /api/reports/\<id\> | 报告详情 |
| POST | /api/reports | 创建报告（信息采集提交） |
| POST | /api/reports/\<id\>/generate | 重新生成报告内容 |
| GET | /api/reports/\<id\>/pdf | 下载 PDF |
| GET | /api/reports/\<id\>/md | 下载 MD |
| GET | /api/gate-logs | 闸门日志列表 |
| GET | /api/reports/\<id\>/gate-logs | 按报告查询闸门日志 |
| GET | /api/templates | 模板列表 |
| POST | /api/templates | 创建模板 |
| PUT | /api/templates/\<id\> | 更新模板 |
| POST | /api/templates/\<id\>/activate | 激活模板 |
| DELETE | /api/templates/\<id\> | 删除模板 |

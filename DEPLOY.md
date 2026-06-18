# 荟城减重 WSP 系统 - Docker 生产环境部署指南

## 📋 目录结构

```
huicheng-wsp/
├── Dockerfile              # Docker镜像构建文件
├── docker-compose.yml      # Docker Compose配置
├── .env.example            # 环境变量示例
├── .dockerignore           # Docker忽略文件
├── nginx.conf              # Nginx配置文件
├── schema.sql              # 数据库初始化脚本
├── requirements.txt        # Python依赖
├── app.py                  # Flask应用入口
├── logs/                   # 日志目录（自动创建）
└── data/                   # 数据目录（自动创建）
    ├── mysql-backup/       # MySQL备份
    └── uploads/            # 上传文件
```

## 🚀 快速开始

### 1. 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 2GB 可用内存
- 至少 10GB 可用磁盘空间

### 2. 环境准备

```bash
# 克隆代码
git clone https://github.com/zxpwolf/huicheng-wsp.git
cd huicheng-wsp

# 复制环境变量文件
cp .env.example .env

# 编辑 .env 文件，修改密码和密钥
vim .env
```

**重要**: 在生产环境中，请务必修改 `.env` 文件中的以下配置:
- `MYSQL_ROOT_PASSWORD` - MySQL root密码
- `MYSQL_PASSWORD` - 应用数据库密码
- `SECRET_KEY` - Flask密钥（使用随机字符串）

生成随机密钥的方法:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3. 启动服务

#### 方式一：基础部署（MySQL + Flask）

```bash
# 构建并启动服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

访问: http://localhost:5000

#### 方式二：完整部署（含Nginx反向代理）

```bash
# 使用production profile启动（包含Nginx）
docker-compose --profile production up -d

# 查看服务状态
docker-compose ps
```

访问: http://localhost (通过Nginx)

### 4. 验证部署

```bash
# 检查容器状态
docker-compose ps

# 所有容器应该显示 "Up" 状态

# 测试API
curl http://localhost:5000/api/dashboard

# 查看应用日志
docker-compose logs web

# 查看数据库日志
docker-compose logs mysql
```

## 🔧 常用操作

### 查看日志

```bash
# 实时查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f web
docker-compose logs -f mysql
docker-compose logs -f nginx

# 查看最近100行日志
docker-compose logs --tail=100 web
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启单个服务
docker-compose restart web
docker-compose restart mysql
```

### 停止服务

```bash
# 停止所有服务
docker-compose stop

# 停止并删除容器
docker-compose down

# 停止并删除容器、网络、卷（谨慎使用！会删除数据库数据）
docker-compose down -v
```

### 更新应用

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build

# 清理未使用的镜像
docker image prune -f
```

### 数据库备份

```bash
# 手动备份数据库
docker-compose exec mysql mysqldump -u root -p${MYSQL_ROOT_PASSWORD} huicheng_wsp > backup_$(date +%Y%m%d_%H%M%S).sql

# 备份文件保存在当前目录
ls -lh backup_*.sql
```

### 数据库恢复

```bash
# 从备份恢复
docker-compose exec -T mysql mysql -u root -p${MYSQL_ROOT_PASSWORD} huicheng_wsp < backup_20260618_120000.sql
```

### 进入容器

```bash
# 进入Web容器
docker-compose exec web bash

# 进入MySQL容器
docker-compose exec mysql bash

# 进入MySQL命令行
docker-compose exec mysql mysql -u wsp_user -p huicheng_wsp
```

## 🔐 安全配置

### 1. HTTPS配置

如需启用HTTPS，需要:

1. 获取SSL证书（Let's Encrypt或其他CA）
2. 将证书文件放到 `ssl/` 目录:
   ```
   ssl/
   ├── fullchain.pem
   └── privkey.pem
   ```
3. 取消 `nginx.conf` 中HTTPS配置的注释
4. 重启服务:
   ```bash
   docker-compose --profile production up -d
   ```

### 2. 防火墙配置

```bash
# 只开放必要端口
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 3306/tcp   # 禁止外部访问MySQL
sudo ufw enable
```

### 3. 定期更新

```bash
# 更新Docker镜像
docker-compose pull
docker-compose up -d

# 更新系统包
sudo apt update && sudo apt upgrade
```

## 📊 监控和维护

### 健康检查

```bash
# 检查服务健康状态
curl http://localhost:5000/api/dashboard
curl http://localhost/health  # 如果使用Nginx

# 查看容器资源使用
docker stats
```

### 日志轮转

日志已通过Python logging模块配置自动轮转:
- 单文件最大: 10MB
- 保留备份: 30个
- 位置: `logs/app.log`

### 数据库优化

```sql
-- 进入MySQL
docker-compose exec mysql mysql -u root -p

-- 优化表
USE huicheng_wsp;
OPTIMIZE TABLE reports;
OPTIMIZE TABLE gate_logs;

-- 查看慢查询
SHOW VARIABLES LIKE 'slow_query_log';
```

## 🐛 故障排查

### 容器无法启动

```bash
# 查看详细日志
docker-compose logs

# 检查端口占用
sudo lsof -i :5000
sudo lsof -i :3306
sudo lsof -i :80

# 检查磁盘空间
df -h
```

### 数据库连接失败

```bash
# 检查MySQL是否运行
docker-compose ps mysql

# 查看MySQL日志
docker-compose logs mysql

# 测试数据库连接
docker-compose exec web python -c "
from db import get_conn
conn = get_conn()
print('Database connected!')
conn.close()
"
```

### 应用错误

```bash
# 查看应用日志
docker-compose logs web

# 进入容器调试
docker-compose exec web bash
python app.py  # 手动启动查看错误
```

### 日志文件过大

```bash
# 清空日志
docker-compose exec web truncate -s 0 /app/logs/app.log

# 或者使用API清空
curl -X POST http://localhost:5000/api/logs/clear
```

## 📈 性能优化

### 1. MySQL优化

在 `docker-compose.yml` 中调整:
```yaml
command:
  - --innodb-buffer-pool-size=512M  # 根据内存调整
  - --max-connections=500
  - --query-cache-size=64M
```

### 2. Gunicorn替代Flask开发服务器

修改 `Dockerfile`:
```dockerfile
RUN pip install gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

### 3. Redis缓存（可选）

添加Redis服务到 `docker-compose.yml`:
```yaml
redis:
  image: redis:alpine
  container_name: huicheng-wsp-redis
  ports:
    - "6379:6379"
```

## 🔄 CI/CD集成

### GitHub Actions示例

创建 `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Deploy to server
        uses: appleboy/scp-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          source: "."
          target: "/opt/huicheng-wsp"
      
      - name: Restart services
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/huicheng-wsp
            docker-compose pull
            docker-compose up -d --build
            docker system prune -f
```

## 📞 技术支持

如遇到问题，请:
1. 查看日志: `docker-compose logs`
2. 检查容器状态: `docker-compose ps`
3. 查阅本文档的故障排查章节
4. 提交Issue到GitHub仓库

## 📝 版本历史

- v1.0 (2026-06-18): 初始Docker部署配置
  - MySQL 8.0
  - Python 3.14
  - Flask 3.0
  - Nginx Alpine

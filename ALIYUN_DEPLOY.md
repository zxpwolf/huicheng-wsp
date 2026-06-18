# 阿里云服务器部署指南

## 📋 服务器信息

- **外网地址**: 47.104.220.141:2023
- **内网地址**: 172.17.0.30:2023
- **部署用户**: deployer
- **部署目录**: /home/deployer/huicheng-wsp/

## 🚀 快速部署

### 方式一: 使用自动化脚本(推荐)

```bash
# 在本地执行
./deploy-to-aliyun.sh
```

脚本会自动:
1. ✅ 上传代码到服务器
2. ✅ 创建配置文件
3. ✅ 构建Docker镜像
4. ✅ 启动所有服务
5. ✅ 执行健康检查

### 方式二: 手动部署

#### 1. SSH登录服务器

```bash
ssh -p 2023 deployer@47.104.220.141
```

密码: `Jjk@ynxt2026`

#### 2. 克隆代码

```bash
cd /home/deployer
git clone https://github.com/zxpwolf/huicheng-wsp.git
cd huicheng-wsp
```

#### 3. 配置环境变量

```bash
# 复制配置文件
cp .env.example .env

# 编辑配置文件
vim .env
```

**重要**: 修改以下配置:
```bash
MYSQL_ROOT_PASSWORD=你的强密码
MYSQL_PASSWORD=你的强密码
SECRET_KEY=运行 python3 -c "import secrets; print(secrets.token_hex(32))" 生成
```

#### 4. 创建必要目录

```bash
mkdir -p logs data/mysql-backup data/uploads ssl
```

#### 5. 启动服务

```bash
# 基础部署(MySQL + Flask)
docker-compose up -d

# 或完整部署(含Nginx)
docker-compose --profile production up -d
```

#### 6. 等待并验证

```bash
# 等待30秒让服务启动
sleep 30

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 测试访问
curl http://localhost:5000/api/dashboard
```

## 🔐 安全配置

### 1. 修改默认密码

立即修改 `.env` 文件中的密码:

```bash
vim /home/deployer/huicheng-wsp/.env
```

修改后重启服务:

```bash
docker-compose down
docker-compose up -d
```

### 2. 配置防火墙

```bash
# 只开放必要端口
sudo ufw allow 2023/tcp   # SSH
sudo ufw allow 80/tcp     # HTTP
sudo ufw allow 443/tcp    # HTTPS (如果使用)
sudo ufw deny 3306/tcp    # 禁止外部访问MySQL
sudo ufw enable
```

### 3. 配置HTTPS(可选但推荐)

参考 [DEPLOY.md](DEPLOY.md) 中的HTTPS配置章节。

## 📊 访问系统

部署完成后,通过浏览器访问:

```
http://47.104.220.141:5000
```

如果使用Nginx部署:

```
http://47.104.220.141
```

## 🔧 常用运维命令

### 查看服务状态

```bash
cd /home/deployer/huicheng-wsp
docker-compose ps
```

### 查看日志

```bash
# 实时查看所有服务日志
docker-compose logs -f

# 查看特定服务
docker-compose logs -f web
docker-compose logs -f mysql
```

### 重启服务

```bash
docker-compose restart
```

### 停止服务

```bash
docker-compose down
```

### 更新应用

```bash
cd /home/deployer/huicheng-wsp
git pull
docker-compose up -d --build
```

### 数据库备份

```bash
cd /home/deployer/huicheng-wsp
docker-compose exec mysql mysqldump -u root -p${MYSQL_ROOT_PASSWORD} huicheng_wsp > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 进入容器调试

```bash
# 进入Web容器
docker-compose exec web bash

# 进入MySQL
docker-compose exec mysql mysql -u wsp_user -p huicheng_wsp
```

## 🐛 故障排查

### 服务无法启动

```bash
# 查看详细日志
docker-compose logs

# 检查端口占用
sudo lsof -i :5000
sudo lsof -i :3306

# 检查磁盘空间
df -h
```

### 数据库连接失败

```bash
# 检查MySQL是否运行
docker-compose ps mysql

# 查看MySQL日志
docker-compose logs mysql

# 测试连接
docker-compose exec web python -c "
from db import get_conn
conn = get_conn()
print('Connected!')
conn.close()
"
```

### 应用错误

```bash
# 查看应用日志
docker-compose logs web

# 进入容器调试
docker-compose exec web bash
python app.py
```

## 📈 监控和维护

### 资源监控

```bash
# 查看容器资源使用
docker stats

# 查看服务器资源
htop
df -h
free -h
```

### 日志管理

日志自动保存在 `/home/deployer/huicheng-wsp/logs/app.log`

查看最近日志:

```bash
tail -f /home/deployer/huicheng-wsp/logs/app.log
```

清空日志:

```bash
curl -X POST http://localhost:5000/api/logs/clear
```

## 🔄 自动更新脚本

创建定时更新脚本 `/home/deployer/update.sh`:

```bash
#!/bin/bash
cd /home/deployer/huicheng-wsp
git pull
docker-compose up -d --build
docker system prune -f
echo "更新完成: $(date)"
```

添加到crontab每天凌晨2点自动更新:

```bash
crontab -e
# 添加: 0 2 * * * /home/deployer/update.sh >> /home/deployer/update.log 2>&1
```

## 📞 技术支持

如遇到问题:
1. 查看日志: `docker-compose logs`
2. 检查服务状态: `docker-compose ps`
3. 查阅 [DEPLOY.md](DEPLOY.md) 文档
4. 提交Issue到GitHub仓库

## ⚠️ 注意事项

1. **定期备份**: 建议每天备份数据库
2. **监控日志**: 定期检查日志文件大小
3. **安全更新**: 及时更新系统和Docker镜像
4. **密码管理**: 使用强密码,定期更换
5. **HTTPS**: 生产环境强烈建议配置HTTPS

---

**部署完成时间**: 2026-06-18  
**文档版本**: v1.0

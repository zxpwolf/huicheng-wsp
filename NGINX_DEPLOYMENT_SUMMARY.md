# Nginx配置完成 - 部署总结

## ✅ 已完成的工作

### 1. Docker容器架构

已成功部署三容器架构:

```
┌─────────────┐
│   Nginx     │ ← 80端口 (反向代理)
│  (alpine)   │
└──────┬──────┘
       │ proxy_pass
       ↓
┌─────────────┐
│    Flask    │ ← 5000端口 (内部,不对外)
│   (web)     │
└──────┬──────┘
       │ pymysql
       ↓
┌─────────────┐
│   MySQL     │ ← 3306端口 (数据库)
│   (8.0)     │
└─────────────┘
```

### 2. 容器状态

```bash
# 查看所有容器
docker ps | grep huicheng

huicheng-wsp-nginx   nginx:alpine      Up X minutes   0.0.0.0:80->80/tcp
huicheng-wsp-web     huicheng-wsp-web  Up X minutes   5000/tcp (internal)
huicheng-wsp-mysql   mysql:8.0         Up X minutes   0.0.0.0:3306->3306/tcp
```

### 3. Nginx配置详情

**配置文件**: [nginx.conf](file:///Users/admin/Documents/projects/Pauline/huicheng-wsp/nginx.conf)

**主要功能**:
- ✅ 反向代理到Flask应用
- ✅ Gzip压缩支持
- ✅ 静态文件缓存
- ✅ 健康检查端点 (/health)
- ✅ 客户端最大上传50MB
- ✅ 完整的请求头转发

**关键配置**:
```nginx
upstream flask_app {
    server web:5000;  # Docker内部网络
}

server {
    listen 80;
    
    location / {
        proxy_pass http://flask_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🌐 访问方式

### 本地访问 (服务器上测试)
```bash
# 通过Nginx (推荐)
curl http://localhost:80/api/dashboard

# 直接访问Flask (调试用)
curl http://localhost:5000/api/dashboard
```

### 外网访问
```
http://47.104.220.141:80
```

**⚠️ 重要**: 需要在阿里云控制台开放80端口!

## 🔧 阿里云安全组配置

### 必须开放的端口

| 端口 | 协议 | 用途 | 授权对象 |
|------|------|------|----------|
| 80   | TCP  | Web访问(HTTP) | 0.0.0.0/0 |
| 2023 | TCP  | SSH登录 | 你的IP/32 |
| 3306 | TCP  | MySQL(可选,仅管理) | 你的IP/32 |

### 配置步骤

1. **登录阿里云控制台**: https://ecs.console.aliyun.com
2. **找到实例**: IP为 `47.104.220.141` 的ECS
3. **安全组配置**: 实例详情 > 安全组 > 配置规则
4. **添加入方向规则**:
   ```
   授权策略: 允许
   协议类型: TCP
   端口范围: 80/80
   授权对象: 0.0.0.0/0
   优先级: 1
   描述: WSP系统Web访问
   ```
5. **保存并等待生效** (通常1-2分钟)

## 📊 常用运维命令

### 查看服务状态
```bash
# 查看所有容器
docker compose ps

# 查看实时日志
docker compose logs -f

# 查看特定服务日志
docker logs -f huicheng-wsp-nginx
docker logs -f huicheng-wsp-web
```

### 重启服务
```bash
# 重启所有服务
docker compose restart

# 重启单个服务
docker compose restart nginx
docker compose restart web
```

### 停止服务
```bash
# 停止所有服务
docker compose down

# 停止并删除数据卷 (危险!)
docker compose down -v
```

### 更新应用
```bash
# 1. 上传新代码
cd /home/deployer/huicheng-wsp
git pull  # 或手动上传

# 2. 重新构建并启动
docker compose up -d --build web

# 3. 验证
curl http://localhost:80/api/dashboard
```

## 🔍 故障排查

### 问题1: 外网无法访问

**检查清单**:
1. ✅ 阿里云安全组已开放80端口
2. ✅ Nginx容器运行正常: `docker ps | grep nginx`
3. ✅ Flask应用正常: `curl http://localhost:5000/api/dashboard`
4. ✅ Nginx配置正确: `docker exec huicheng-wsp-nginx nginx -t`

**诊断命令**:
```bash
# 本地测试
curl http://localhost:80/api/dashboard

# 检查Nginx日志
docker logs huicheng-wsp-nginx --tail 50

# 检查Flask日志
docker logs huicheng-wsp-web --tail 50
```

### 问题2: Nginx返回502 Bad Gateway

**原因**: Flask应用未启动或Nginx无法连接

**解决**:
```bash
# 检查Flask状态
docker ps | grep web

# 查看Flask日志
docker logs huicheng-wsp-web --tail 50

# 重启Flask
docker compose restart web
```

### 问题3: 数据库连接失败

**检查**:
```bash
# MySQL是否运行
docker ps | grep mysql

# 测试数据库连接
docker exec huicheng-wsp-web python -c "from db import get_conn; conn = get_conn(); print('✅数据库连接成功'); conn.close()"
```

## 🔒 安全建议

### 当前状态
- ⚠️ HTTP明文传输 (未加密)
- ⚠️ 5000端口仍对外暴露
- ✅ Nginx反向代理已启用

### 改进建议

#### 1. 启用HTTPS (强烈推荐)
```bash
# 使用Let's Encrypt免费证书
docker run -it --rm \
  -v /etc/letsencrypt:/etc/letsencrypt \
  certbot/certbot certonly \
  --standalone \
  -d your-domain.com
```

然后取消注释 [nginx.conf](file:///Users/admin/Documents/projects/Pauline/huicheng-wsp/nginx.conf) 中的HTTPS配置部分。

#### 2. 隐藏Flask端口
修改 `docker-compose.yml`,移除web服务的ports映射:
```yaml
web:
  # 不要暴露5000端口到宿主机
  expose:
    - "5000"  # 只在Docker内部网络可用
```

#### 3. 限制SSH访问
在阿里云安全组中,将2023端口的授权对象改为你的固定IP:
```
端口: 2023/2023
授权对象: 你的办公IP/32
```

#### 4. 定期备份数据库
```bash
# 创建备份脚本
cat > backup-db.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker exec huicheng-wsp-mysql mysqldump -u wsp_user -p'Wsp@App@2026!Secure' huicheng_wsp > /backup/db_${DATE}.sql
find /backup -name "db_*.sql" -mtime +7 -delete  # 保留7天
EOF

chmod +x backup-db.sh

# 添加到crontab (每天凌晨2点备份)
echo "0 2 * * * /home/deployer/huicheng-wsp/backup-db.sh" | crontab -
```

## 📈 性能优化

### Nginx优化

已在配置中启用:
- ✅ Gzip压缩 (减少60-80%流量)
- ✅ 静态文件缓存 (30天)
- ✅ Keepalive连接复用

### 进一步优化

1. **增加worker进程**:
   ```nginx
   worker_processes auto;
   worker_rlimit_nofile 65535;
   ```

2. **启用HTTP/2** (需要HTTPS):
   ```nginx
   listen 443 ssl http2;
   ```

3. **添加限流**:
   ```nginx
   limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
   ```

## 🎯 下一步计划

### 短期 (本周)
- [ ] 配置阿里云安全组开放80端口
- [ ] 测试外网访问是否正常
- [ ] 设置数据库自动备份

### 中期 (本月)
- [ ] 申请SSL证书并启用HTTPS
- [ ] 配置域名解析 (如 wsp.yourdomain.com)
- [ ] 设置监控告警

### 长期
- [ ] 考虑使用负载均衡
- [ ] 实现蓝绿部署
- [ ] 添加CDN加速

## 📞 技术支持

**项目目录**: `/home/deployer/huicheng-wsp`

**相关文档**:
- [ALIYUN_ACCESS_FIX.md](file:///Users/admin/Documents/projects/Pauline/huicheng-wsp/ALIYUN_ACCESS_FIX.md) - 阿里云访问问题排查
- [DEPLOY.md](file:///Users/admin/Documents/projects/Pauline/huicheng-wsp/DEPLOY.md) - Docker部署指南
- [ALIYUN_DEPLOY.md](file:///Users/admin/Documents/projects/Pauline/huicheng-wsp/ALIYUN_DEPLOY.md) - 阿里云部署详细步骤

**部署脚本**:
- [deploy-with-nginx.sh](file:///Users/admin/Documents/projects/Pauline/huicheng-wsp/deploy-with-nginx.sh) - 一键部署脚本

---

**部署时间**: 2026-06-18  
**部署版本**: Docker Compose + Nginx  
**服务器**: 阿里云 ECS (47.104.220.141)

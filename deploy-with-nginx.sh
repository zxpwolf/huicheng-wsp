#!/bin/bash
set -e

echo "========================================="
echo "  荟城WSP系统 - Nginx部署脚本"
echo "========================================="
echo ""

cd /home/deployer/huicheng-wsp

# 1. 确保requirements.txt包含cryptography
echo "步骤1/6: 检查依赖..."
if ! grep -q "cryptography" requirements.txt; then
    echo "cryptography>=42.0.0" >> requirements.txt
    echo "✅ 已添加cryptography到requirements.txt"
else
    echo "✅ cryptography已在requirements.txt中"
fi

# 2. 停止并清理旧容器
echo ""
echo "步骤2/6: 清理旧容器..."
docker compose down
docker rm -f huicheng-wsp-web huicheng-wsp-mysql huicheng-wsp-nginx 2>/dev/null || true
echo "✅ 旧容器已清理"

# 3. 创建必要的目录
echo ""
echo "步骤3/6: 创建目录结构..."
mkdir -p logs/nginx
echo "✅ 目录已创建"

# 4. 重新构建镜像
echo ""
echo "步骤4/6: 重新构建Docker镜像(这可能需要几分钟)..."
docker build --no-cache -t huicheng-wsp-web . 
echo "✅ 镜像构建完成"

# 5. 启动所有服务
echo ""
echo "步骤5/6: 启动服务(MySQL + Flask + Nginx)..."
docker compose up -d
echo "✅ 服务已启动"

# 6. 等待并验证
echo ""
echo "步骤6/6: 等待服务启动并验证..."
sleep 20

# 检查容器状态
echo ""
echo "=== 容器状态 ==="
docker compose ps

# 测试Flask应用
echo ""
echo "=== 测试Flask应用 ==="
if curl -s http://localhost:5000/api/dashboard > /dev/null 2>&1; then
    echo "✅ Flask应用运行正常 (端口5000)"
else
    echo "❌ Flask应用启动失败,查看日志:"
    docker logs huicheng-wsp-web --tail 20
fi

# 测试Nginx
echo ""
echo "=== 测试Nginx反向代理 ==="
NGINX_STATUS=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:80/ 2>/dev/null || echo "000")
if [ "$NGINX_STATUS" != "000" ]; then
    echo "✅ Nginx运行正常 (端口80) - HTTP状态: $NGINX_STATUS"
else
    echo "❌ Nginx启动失败,查看日志:"
    docker logs huicheng-wsp-nginx --tail 20
fi

# 最终总结
echo ""
echo "========================================="
echo "  部署完成!"
echo "========================================="
echo ""
echo "访问方式:"
echo "  1. 本地访问: http://localhost:80"
echo "  2. 外网访问: http://47.104.220.141:80"
echo ""
echo "重要提示:"
echo "  ⚠️  需要在阿里云控制台开放80端口(安全组配置)"
echo "  📖 详细说明请查看: ALIYUN_ACCESS_FIX.md"
echo ""
echo "常用命令:"
echo "  查看日志:   docker compose logs -f"
echo "  重启服务:   docker compose restart"
echo "  停止服务:   docker compose down"
echo ""
